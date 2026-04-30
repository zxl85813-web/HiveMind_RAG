"""Quick demo: run pipeline (skip_llm) and pretty-print all stages."""
import asyncio, json, sys, io
from pathlib import Path
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.core.database import async_session_factory
from app.services.quote import QuoteIntelligenceService, TokenVault

DIVIDER = "=" * 64

async def main():
    svc = QuoteIntelligenceService()

    # ---------- Stage 1+2: fetch & mask (all strategies) ----------
    async with async_session_factory() as db:
        result = await svc.run(
            db, tenant_id="default", top_n=5,
            ranking="amount_weighted_recency", skip_llm=True,
        )

    print(f"\n{DIVIDER}")
    print("STAGE 1 — FETCH")
    print(f"{DIVIDER}")
    print(f"  从 DB 取得报价记录数  : {result.fetched_count}")
    print(f"  ranking 策略         : {result.ranking}")

    print(f"\n{DIVIDER}")
    print("STAGE 2 — MASK  (PII → 不透明 token)")
    print(f"{DIVIDER}")
    print(f"  生成唯一 PII token 数 : {result.token_count}")
    print(f"\n  前 3 条 masked 记录：")
    for i, rec in enumerate(result.masked_records[:3]):
        print(f"\n  [{i+1}] {json.dumps(rec, ensure_ascii=False, indent=6)}")

    print(f"\n{DIVIDER}")
    print("STAGE 3 — TOP-N 算法排序  (amount_weighted_recency)")
    print(f"{DIVIDER}")
    print(f"  selected_count = {result.selected_count}")
    print(f"  金额（分）排行：")
    for i, rec in enumerate(result.masked_records):
        print(f"    #{i+1}  {rec['customer_name']}  {rec['product_name']}  "
              f"${rec['amount_cents']//100:,}  status={rec['status']}")

    # ---------- Stage 4: simulate LLM output (hand-crafted) ----------
    print(f"\n{DIVIDER}")
    print("STAGE 4 — LLM 分析（模拟输出，展示 token 如何出现在报告中）")
    print(f"{DIVIDER}")
    recs = result.masked_records
    simulated_masked_report = f"""## Executive Summary
- [CUST_001] 和 [CUST_002] 合计贡献了本期最大交易额，均集中在 Enterprise 产品线
- 区域 {recs[0].get('region','?')} 占 top-5 交易的 60%，建议加大本地资源投入
- [CUST_003] 状态为 "won"，可作为标杆案例用于 {recs[1].get('region','?')} 拓展

## Top Opportunities

| # | 客户 | 产品 | 金额 | 状态 |
|---|------|------|------|------|
""" + "".join(
    f"| {i+1} | {r['customer_name']} | {r['product_name']} | ${r['amount_cents']//100:,} | {r['status']} |\n"
    for i, r in enumerate(recs)
) + """
## Risk & Recommendations
- [PHONE_001] 电话尚未确认联系成功，建议本周跟进
- [EMAIL_002] 邮件地址域名为竞争对手，注意信息保密
"""

    print(simulated_masked_report)

    # ---------- Stage 5: unmask ----------
    print(f"\n{DIVIDER}")
    print("STAGE 5 — UNMASK（回填原始 PII，交付给人类读者）")
    print(f"{DIVIDER}")

    # rebuild vault from the same data
    records_plain = []
    async with async_session_factory() as db:
        quotes = await svc.fetch(db, "default", limit=50)
        records_plain = svc.to_dicts(quotes)
    _, vault = svc.mask_records(records_plain)
    # top-N with same strategy to get same vault state
    svc.top_n(svc.mask_records(records_plain)[0], 5)

    # Because we need the vault that covers the simulated tokens,
    # build a minimal one manually for the demo.
    demo_vault = TokenVault()
    for rec_plain, rec_masked in zip(records_plain[:5], result.masked_records):
        demo_vault._token_to_value[rec_masked["customer_name"]] = rec_plain["customer_name"]
        demo_vault._token_to_value[rec_masked["customer_phone"]] = rec_plain["customer_phone"]
        demo_vault._token_to_value[rec_masked["customer_email"]] = rec_plain["customer_email"]
        if rec_masked.get("customer_company"):
            demo_vault._token_to_value[rec_masked["customer_company"]] = rec_plain.get("customer_company","")

    final_report = demo_vault.unmask(simulated_masked_report)
    print(final_report)

    print(f"\n{DIVIDER}")
    print("SMOKE CHECK 汇总")
    print(f"{DIVIDER}")
    checks = [
        ("fetched > 0", result.fetched_count > 0),
        ("selected == 5", result.selected_count == 5),
        ("PII token 数 > 0", result.token_count > 0),
        ("masked 记录无原始姓名", all(
            not any(p in json.dumps(r) for p in ["Alice","Bob","Carol","David","Eva","Frank"])
            for r in result.masked_records
        )),
        ("final_report 含真实姓名", any(
            n in final_report for n in [records_plain[0]["customer_name"],
                                         records_plain[1]["customer_name"]]
        )),
    ]
    for label, passed in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}  {label}")

    all_pass = all(p for _, p in checks)
    print(f"\n{'ALL PASS ✓' if all_pass else 'SOME TESTS FAILED ✗'}")
    return 0 if all_pass else 1

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
