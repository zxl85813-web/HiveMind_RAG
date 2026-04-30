# -*- coding: utf-8 -*-
"""Step-by-step pipeline walkthrough — prints every stage side-by-side."""
import asyncio, json, sys, io, textwrap
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import async_session_factory
from app.services.quote import QuoteIntelligenceService, TokenVault


DIV  = "=" * 70
DIV2 = "-" * 70
N_DEMO = 3  # show only 3 records for readability


def section(title: str) -> None:
    print(f"\n{DIV}")
    print(f"  {title}")
    print(DIV)


def show_record(label: str, rec: dict, idx: int) -> None:
    print(f"\n  [{label} #{idx+1}]")
    for k, v in rec.items():
        if k == "id":
            continue  # skip UUID noise
        print(f"    {k:<22} = {v}")


async def main() -> int:
    svc = QuoteIntelligenceService()

    # ================================================================
    # STAGE 0 — 从数据库取原始数据
    # ================================================================
    section("STAGE 0 — 从 PostgreSQL quotes 表取原始数据 (RAW)")

    async with async_session_factory() as db:
        raw_quotes = await svc.fetch(db, tenant_id="default", limit=50)

    raw_records = svc.to_dicts(raw_quotes)

    print(f"\n  共取到 {len(raw_records)} 条报价记录（展示前 {N_DEMO} 条）")
    print(f"  表字段：id / tenant_id / customer_name / customer_phone /")
    print(f"          customer_email / customer_company / product_name /")
    print(f"          quantity / unit_price_cents / amount_cents /")
    print(f"          currency / region / status / created_at")
    print(DIV2)
    for i, rec in enumerate(raw_records[:N_DEMO]):
        show_record("原始", rec, i)

    print(f"\n  >>> PII 字段一览（前 {N_DEMO} 条）:")
    print(f"  {'序号':<4} {'customer_name':<18} {'customer_phone':<22} {'customer_email':<28} {'customer_company'}")
    for i, rec in enumerate(raw_records[:N_DEMO]):
        print(f"  {i+1:<4} {rec['customer_name']:<18} {rec['customer_phone']:<22} {rec['customer_email']:<28} {rec.get('customer_company','')}")

    # ================================================================
    # STAGE 1 — MASK：用 TokenVault 替换 PII
    # ================================================================
    section("STAGE 1 — MASK：TokenVault 将 PII 替换为不透明 token")

    masked_all, vault = svc.mask_records(raw_records)

    print(f"""
  TokenVault 工作原理
  {DIV2}
  · 每个唯一 PII 值只生成一个 token（去重 + 稳定映射）
  · token 格式：[KIND_NNN]
      CUST    = customer_name
      PHONE   = customer_phone
      EMAIL   = customer_email
      COMPANY = customer_company
  · 同一个 "Alice Chen" 不论出现多少次，始终映射到同一个 [CUST_001]
  · vault 内部保存双向字典：token <-> 原始值
  · 本次 vault 生成了 {len(vault)} 个唯一 PII token（来自 {len(raw_records)} 条记录）
""")

    print(f"  Token 映射表（前 15 条）：")
    print(f"  {'Token':<18} {'原始值'}")
    print(f"  {'-'*18} {'-'*30}")
    for tok, val in list(vault.mapping().items())[:15]:
        print(f"  {tok:<18} {val}")

    print(f"\n  Masked 记录对比（前 {N_DEMO} 条）：")
    print(DIV2)
    for i in range(N_DEMO):
        raw = raw_records[i]
        msk = masked_all[i]
        print(f"\n  ── 第 {i+1} 条 ──────────────────────────────")
        pii_fields = ["customer_name", "customer_phone", "customer_email", "customer_company"]
        for f in pii_fields:
            rv = raw.get(f) or "(空)"
            mv = msk.get(f) or "(空)"
            arrow = "→" if rv != mv else "  "
            print(f"    {f:<22} {rv:<28} {arrow}  {mv}")
        non_pii = [k for k in msk if k not in pii_fields and k != "id"]
        print(f"    ── 非 PII 字段（原样保留）──")
        for f in non_pii:
            print(f"    {f:<22} {msk[f]}")

    # ================================================================
    # STAGE 2 — TOP-N 算法排序
    # ================================================================
    section("STAGE 2 — TOP-N 算法排序")

    top5 = svc.top_n(masked_all, 5, ranking="amount_weighted_recency")

    print(f"""
  排序策略：amount_weighted_recency（默认）
  {DIV2}
  公式：score = amount_cents × e^(-age_days / 30)
    · amount_cents  = 金额（分），越大越好
    · age_days      = 距今天数，越新越高分
    · 半衰期 30 天：30 天前的订单得分 ≈ 当前金额的 36.8%
    · 效果：高价值 & 新鲜的报价排名靠前
""")
    print(f"  TOP-5 排名（masked，发给 LLM 的就是这份数据）：")
    print(f"  {'#':<3} {'customer_name':<14} {'product_name':<32} {'amount_cents':>14} {'status':<10} {'created_at'}")
    print(f"  {'-'*3} {'-'*14} {'-'*32} {'-'*14} {'-'*10} {'-'*26}")
    for i, rec in enumerate(top5):
        print(f"  {i+1:<3} {rec['customer_name']:<14} {rec['product_name']:<32} {rec['amount_cents']:>14,} {rec['status']:<10} {rec['created_at']}")

    # ================================================================
    # STAGE 3 — 发给 LLM 的 Prompt
    # ================================================================
    section("STAGE 3 — 发给 LLM 的 Prompt（masked payload）")

    payload_json = json.dumps(top5, ensure_ascii=False, indent=2)
    print(f"""
  System Prompt（摘要）：
  {DIV2}
  "You are a senior sales-intelligence analyst. Customer-identifying
   fields have been replaced with opaque tokens like [CUST_001],
   [PHONE_002]. Treat tokens as opaque IDs — do NOT invent names,
   do NOT try to guess identities. Produce a markdown report with:
   ## Executive Summary / ## Top Opportunities / ## Risk & Recommendations"
""")
    print("  User Message（前 40 行）：")
    print(DIV2)
    lines = f"Here are the top 5 masked sales quotes:\n\n```json\n{payload_json}\n```".splitlines()
    for line in lines[:40]:
        print(f"  {line}")
    if len(lines) > 40:
        print(f"  ... (共 {len(lines)} 行)")

    # ================================================================
    # STAGE 4 — LLM 输出（模拟，保留 token 不解析）
    # ================================================================
    section("STAGE 4 — LLM 返回的 Markdown 报告（含 token，未回填）")

    simulated_llm_output = f"""\
## Executive Summary
- {top5[0]['customer_name']} 和 {top5[1]['customer_name']} 均持有 HiveMind RAG Enterprise 报价，\
合计金额超 $99,800，建议优先跟进。
- 区域 {top5[0].get('region','?')} 在本期 TOP-5 中占比最高，显示出强劲的 Enterprise 需求。
- {top5[2]['customer_name']} 状态为 "{top5[2]['status']}"，可作为同区域拓展的标杆案例。

## Top Opportunities

| # | 客户 Token | 产品 | 金额 (USD) | 状态 |
|---|-----------|------|-----------|------|
| 1 | {top5[0]['customer_name']} | {top5[0]['product_name']} | ${top5[0]['amount_cents']//100:,} | {top5[0]['status']} |
| 2 | {top5[1]['customer_name']} | {top5[1]['product_name']} | ${top5[1]['amount_cents']//100:,} | {top5[1]['status']} |
| 3 | {top5[2]['customer_name']} | {top5[2]['product_name']} | ${top5[2]['amount_cents']//100:,} | {top5[2]['status']} |
| 4 | {top5[3]['customer_name']} | {top5[3]['product_name']} | ${top5[3]['amount_cents']//100:,} | {top5[3]['status']} |
| 5 | {top5[4]['customer_name']} | {top5[4]['product_name']} | ${top5[4]['amount_cents']//100:,} | {top5[4]['status']} |

## Risk & Recommendations
- 联系 {top5[0]['customer_phone']} 时请确认是否仍为有效号码，该客户最近无互动记录。
- {top5[1]['customer_email']} 域名需注意竞争对手背景，沟通时保持信息保密。
- 建议本周对所有 draft 状态报价发起跟进邮件。
"""

    print()
    for line in simulated_llm_output.splitlines():
        print(f"  {line}")

    print(f"\n  >>> 注意：报告中所有客户标识仍为 token，尚未回填。")
    print(f"      例：'{top5[0]['customer_name']}' = 某真实客户（LLM 不知道是谁）")

    # ================================================================
    # STAGE 5 — UNMASK：token 回填为原始 PII
    # ================================================================
    section("STAGE 5 — UNMASK：将 token 替换回原始 PII 值")

    final_report = vault.unmask(simulated_llm_output)

    print(f"""
  操作：单遍正则 re.sub() 扫描全文，将每个 [KIND_NNN] 替换为 vault 中对应的原始值
  正则：\\[(?:CUST|PHONE|EMAIL|COMPANY)_\\d{{3,}}\\]
  复杂度：O(文本长度) — 一次扫描完成，不做多轮替换
""")

    print("  Token 回填对照（本报告用到的 token）：")
    print(f"  {'Token':<18} {'回填值'}")
    print(f"  {'-'*18} {'-'*30}")
    mapping = vault.mapping()
    for tok in sorted(set(t for t in mapping if t in simulated_llm_output)):
        print(f"  {tok:<18} {mapping[tok]}")

    print(f"\n  最终报告（交付给人类读者）：")
    print(DIV2)
    for line in final_report.splitlines():
        print(f"  {line}")

    # ================================================================
    # 汇总
    # ================================================================
    section("汇总 — 各阶段数据流转")
    print(f"""
  阶段  输入                    操作                      输出
  {'-'*65}
  0     PostgreSQL DB           SELECT ... LIMIT 50       {len(raw_records)} 条原始记录（含 PII）
  1     {len(raw_records)} 条原始记录          TokenVault.mask()         {len(masked_all)} 条 masked 记录 + vault({len(vault)} tokens)
  2     {len(masked_all)} 条 masked 记录       top_n(5, strategy)        5 条 masked TOP-5
  3     5 条 masked TOP-5       构建 Prompt（system+user） LLM 的输入（无 PII）
  4     LLM 的输入              BALANCED tier ainvoke()   Markdown 报告（含 token）
  5     报告（含 token）         TokenVault.unmask()       最终报告（PII 已回填）

  安全保证：
    · LLM 整个生命周期只看到 [CUST_xxx] / [PHONE_xxx] / [EMAIL_xxx] / [COMPANY_xxx]
    · Vault 仅存在于单次请求内存中，不落库，请求结束即销毁
    · unmask 在服务端（backend）执行后才返回给调用方
    · 若 LLM 尝试猜测或还原 token，其输出的"猜测值"不会被 vault 识别，
      unmask 时保持原样，不会误替换
""")

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
