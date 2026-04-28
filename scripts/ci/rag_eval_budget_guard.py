#!/usr/bin/env python3
"""
RAG Evaluation Budget Guard
============================
CI 预算守卫：决定本次 RAG 评估应该用真实 LLM 还是 Mock 模式。

决策优先级链:
  1. --force-real 标志 → 始终真实评估（手动触发时使用）
  2. OPA Policy 触发规则 → 根据 event/branch/changed-paths 决定
  3. 预算检查 → 超出阈值时强制降级为 Mock

输出（写入 GITHUB_OUTPUT）:
  eval_mode         real_eval | mock_eval
  eval_reason       决策原因（用于 Summary 展示）
  should_run_real   true | false
  should_run_mock   true | false
  daily_usage_pct   当日已用预算百分比（0-100）
  monthly_usage_pct 当月已用预算百分比（0-100）

成本缓存文件 (.ci_cost_cache.json):
  {
    "daily_cost_usd": 3.5,
    "monthly_cost_usd": 42.0,
    "last_updated": "2026-04-27T10:00:00",
    "last_eval_cost_usd": 0.12
  }
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# ── 常量 ──────────────────────────────────────────────────────────────────────
CACHE_FILE = Path(".ci_cost_cache.json")
GITHUB_OUTPUT = os.environ.get("GITHUB_OUTPUT", "")

# 预算告警阈值（超出后降级为 Mock）
DAILY_ALERT_THRESHOLD = 0.80    # 80% 日预算
MONTHLY_ALERT_THRESHOLD = 0.90  # 90% 月预算

# RAG 核心路径：这些路径变更时才触发真实评估（develop 分支）
RAG_CORE_PATHS = {
    "backend/app/services/evaluation/",
    "backend/app/services/generation/",
    "backend/app/prompts/",
    "backend/app/services/rag_gateway.py",
    "backend/app/services/retrieval/",
    "benchmarks/",
}

# 每次真实评估的预估成本（USD）
# 基于 5 个 query × 3 grading rounds × DeepSeek-V3 价格估算
ESTIMATED_EVAL_COST_USD = 0.15


# ── 工具函数 ──────────────────────────────────────────────────────────────────

def write_output(key: str, value: str) -> None:
    """写入 GitHub Actions output。"""
    if GITHUB_OUTPUT:
        with open(GITHUB_OUTPUT, "a", encoding="utf-8") as f:
            f.write(f"{key}={value}\n")
    print(f"  [output] {key}={value}")


def load_cost_cache() -> dict:
    """加载成本缓存，不存在时返回空缓存。"""
    if CACHE_FILE.exists():
        try:
            data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            # 检查是否是今天的数据，如果不是则重置日成本
            last_updated = datetime.fromisoformat(data.get("last_updated", "2000-01-01"))
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            if last_updated.date() < now.date():
                print("  [cache] New day detected, resetting daily cost.")
                data["daily_cost_usd"] = 0.0
            return data
        except Exception as e:
            print(f"  [cache] Failed to load cache: {e}, using empty cache.")

    return {
        "daily_cost_usd": 0.0,
        "monthly_cost_usd": 0.0,
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "last_eval_cost_usd": 0.0,
    }


def save_cost_cache(cache: dict) -> None:
    """保存成本缓存（预估本次评估成本后更新）。"""
    cache["daily_cost_usd"] = cache.get("daily_cost_usd", 0.0) + ESTIMATED_EVAL_COST_USD
    cache["monthly_cost_usd"] = cache.get("monthly_cost_usd", 0.0) + ESTIMATED_EVAL_COST_USD
    cache["last_updated"] = datetime.now(timezone.utc).isoformat()
    cache["last_eval_cost_usd"] = ESTIMATED_EVAL_COST_USD
    CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    print(f"  [cache] Updated: daily=${cache['daily_cost_usd']:.3f}, monthly=${cache['monthly_cost_usd']:.3f}")


def check_rag_core_changed(changed_paths: str) -> bool:
    """检查变更文件中是否包含 RAG 核心路径。"""
    if not changed_paths.strip():
        return False
    paths = changed_paths.strip().split()
    for path in paths:
        for core_path in RAG_CORE_PATHS:
            if path.startswith(core_path) or path == core_path.rstrip("/"):
                return True
    return False


# ── OPA Policy 逻辑（Python 实现，与 rego 文件保持一致）────────────────────

def apply_trigger_policy(
    *,
    event: str,
    branch: str,
    source_branch: str,
    changed_paths: str,
    force_real: bool,
) -> tuple[str, str]:
    """
    触发策略（对应 harness/policies/rag_eval_trigger_policy.rego）。

    返回: (mode, reason)
      mode: "real_eval" | "mock_eval"
    """
    # 规则 1: 强制真实评估（手动触发时）
    if force_real:
        return "real_eval", "force_real flag set by operator"

    # 规则 2: workflow_dispatch → 真实评估
    if event == "workflow_dispatch":
        return "real_eval", "manual workflow_dispatch trigger"

    # 规则 3: main 分支 push → 真实评估（生产门禁）
    if event == "push" and branch == "main":
        return "real_eval", "push to main branch (production gate)"

    # 规则 4: release/* PR → main → 真实评估
    if event == "pull_request" and branch == "main":
        if source_branch.startswith("release/"):
            return "real_eval", f"release PR to main (branch: {source_branch})"
        # 非 release 分支的 PR → main → Mock
        return "mock_eval", f"non-release PR to main (branch: {source_branch}), use mock"

    # 规则 5: develop 分支 push → 仅 RAG 核心路径变更时真实评估
    if event == "push" and branch == "develop":
        if check_rag_core_changed(changed_paths):
            return "real_eval", "develop push with RAG core path changes"
        return "mock_eval", "develop push without RAG core changes, use mock"

    # 规则 6: feature PR → develop → Mock（快速反馈，零成本）
    if event == "pull_request" and branch == "develop":
        return "mock_eval", f"feature PR to develop (branch: {source_branch}), use mock for fast feedback"

    # 规则 7: 其他情况 → Mock（保守策略）
    return "mock_eval", f"unmatched event={event} branch={branch}, defaulting to mock"


def apply_budget_policy(
    *,
    mode: str,
    daily_cost: float,
    monthly_cost: float,
    daily_limit: float,
    monthly_limit: float,
) -> tuple[str, str]:
    """
    预算策略（对应 harness/policies/rag_eval_budget_policy.rego）。

    如果触发策略决定真实评估，但预算超出阈值，则降级为 Mock。
    返回: (final_mode, reason)
    """
    if mode != "real_eval":
        return mode, ""  # 已经是 Mock，不需要检查预算

    daily_pct = (daily_cost / daily_limit * 100) if daily_limit > 0 else 0
    monthly_pct = (monthly_cost / monthly_limit * 100) if monthly_limit > 0 else 0

    if daily_pct >= DAILY_ALERT_THRESHOLD * 100:
        return (
            "mock_eval",
            f"daily budget {daily_pct:.1f}% >= {DAILY_ALERT_THRESHOLD*100:.0f}% threshold, downgraded to mock",
        )

    if monthly_pct >= MONTHLY_ALERT_THRESHOLD * 100:
        return (
            "mock_eval",
            f"monthly budget {monthly_pct:.1f}% >= {MONTHLY_ALERT_THRESHOLD*100:.0f}% threshold, downgraded to mock",
        )

    return "real_eval", ""


# ── 主逻辑 ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="RAG Evaluation Budget Guard")
    parser.add_argument("--event",          required=True,  help="GitHub event name")
    parser.add_argument("--branch",         required=True,  help="Target branch")
    parser.add_argument("--source-branch",  default="",     help="Source branch (for PRs)")
    parser.add_argument("--changed-paths",  default="",     help="Space-separated changed file paths")
    parser.add_argument("--daily-limit",    type=float, default=10.0, help="Daily LLM cost limit (USD)")
    parser.add_argument("--monthly-limit",  type=float, default=100.0, help="Monthly LLM cost limit (USD)")
    parser.add_argument("--force-real",     action="store_true", help="Force real evaluation")
    args = parser.parse_args()

    print("=" * 60)
    print("  RAG Evaluation Budget Guard")
    print(f"  Event:   {args.event}")
    print(f"  Branch:  {args.branch}")
    print(f"  Source:  {args.source_branch or '(none)'}")
    print(f"  Force:   {args.force_real}")
    print("=" * 60)

    # 1. 加载成本缓存
    cache = load_cost_cache()

    # 从环境变量读取（GitHub Variables 注入，比缓存更准确）
    env_daily = float(os.environ.get("CI_DAILY_LLM_COST_USD", "0") or "0")
    env_monthly = float(os.environ.get("CI_MONTHLY_LLM_COST_USD", "0") or "0")

    # 取环境变量和缓存的较大值（更保守）
    daily_cost = max(env_daily, cache.get("daily_cost_usd", 0.0))
    monthly_cost = max(env_monthly, cache.get("monthly_cost_usd", 0.0))

    daily_pct = round(daily_cost / args.daily_limit * 100, 1) if args.daily_limit > 0 else 0
    monthly_pct = round(monthly_cost / args.monthly_limit * 100, 1) if args.monthly_limit > 0 else 0

    print(f"\n  Budget Status:")
    print(f"    Daily:   ${daily_cost:.3f} / ${args.daily_limit:.1f} ({daily_pct}%)")
    print(f"    Monthly: ${monthly_cost:.3f} / ${args.monthly_limit:.1f} ({monthly_pct}%)")

    # 2. 应用触发策略
    mode, trigger_reason = apply_trigger_policy(
        event=args.event,
        branch=args.branch,
        source_branch=args.source_branch,
        changed_paths=args.changed_paths,
        force_real=args.force_real,
    )
    print(f"\n  Trigger Policy: {mode} — {trigger_reason}")

    # 3. 应用预算策略（可能降级）
    final_mode, budget_reason = apply_budget_policy(
        mode=mode,
        daily_cost=daily_cost,
        monthly_cost=monthly_cost,
        daily_limit=args.daily_limit,
        monthly_limit=args.monthly_limit,
    )

    if budget_reason:
        print(f"  Budget Policy:  {final_mode} — {budget_reason}")
        reason = budget_reason
    else:
        reason = trigger_reason

    # 4. 输出决策
    print(f"\n  ✅ Final Decision: {final_mode}")
    print(f"  Reason: {reason}")

    write_output("eval_mode",         final_mode)
    write_output("eval_reason",       reason.replace("\n", " "))
    write_output("should_run_real",   "true" if final_mode == "real_eval" else "false")
    write_output("should_run_mock",   "true" if final_mode == "mock_eval" else "false")
    write_output("daily_usage_pct",   str(daily_pct))
    write_output("monthly_usage_pct", str(monthly_pct))

    # 5. 如果决定真实评估，预更新成本缓存（乐观估算）
    if final_mode == "real_eval":
        save_cost_cache(cache)
        print(f"\n  Cost cache updated (estimated +${ESTIMATED_EVAL_COST_USD:.3f})")

    print("=" * 60)


if __name__ == "__main__":
    main()
