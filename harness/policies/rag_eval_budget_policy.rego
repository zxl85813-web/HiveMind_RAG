# =============================================================================
# RAG Evaluation Budget Policy
# =============================================================================
# OPA Policy — 控制 LLM API 调用的成本上限
#
# 在触发策略决定"真实评估"后，此策略检查预算是否允许执行。
# 超出阈值时自动降级为 Mock 模式，防止 CI 费用失控。
#
# 阈值设计:
#   日预算 80% → 告警并降级（留 20% 给生产环境紧急调用）
#   月预算 90% → 告警并降级（留 10% 缓冲）
#
# 与 Feature Flag 联动:
#   llm_cost_daily_limit_usd 可通过 Harness Feature Flag 动态调整，
#   无需修改此 Policy 文件。
# =============================================================================

package hivemind.rag_eval.budget

import future.keywords.if

# ── 阈值常量 ──────────────────────────────────────────────────────────────────
daily_alert_threshold   := 0.80   # 80% 日预算
monthly_alert_threshold := 0.90   # 90% 月预算

# ── 预算使用率计算 ────────────────────────────────────────────────────────────
daily_usage_pct   := input.daily_cost_usd   / input.daily_limit_usd   * 100
monthly_usage_pct := input.monthly_cost_usd / input.monthly_limit_usd * 100

# ── 预算超出检查 ──────────────────────────────────────────────────────────────
daily_exceeded if {
    daily_usage_pct >= daily_alert_threshold * 100
}

monthly_exceeded if {
    monthly_usage_pct >= monthly_alert_threshold * 100
}

budget_exceeded if { daily_exceeded }
budget_exceeded if { monthly_exceeded }

# ── 最终决策 ──────────────────────────────────────────────────────────────────

# 预算充足 → 允许真实评估
allow := {
    "permitted": true,
    "mode": "real_eval",
    "reason": "budget within limits",
    "daily_usage_pct": daily_usage_pct,
    "monthly_usage_pct": monthly_usage_pct,
} if {
    input.requested_mode == "real_eval"
    not budget_exceeded
}

# 日预算超出 → 降级为 Mock
allow := {
    "permitted": false,
    "mode": "mock_eval",
    "reason": sprintf("daily budget %.1f%% >= %.0f%% threshold", [daily_usage_pct, daily_alert_threshold * 100]),
    "daily_usage_pct": daily_usage_pct,
    "monthly_usage_pct": monthly_usage_pct,
} if {
    input.requested_mode == "real_eval"
    daily_exceeded
}

# 月预算超出 → 降级为 Mock
allow := {
    "permitted": false,
    "mode": "mock_eval",
    "reason": sprintf("monthly budget %.1f%% >= %.0f%% threshold", [monthly_usage_pct, monthly_alert_threshold * 100]),
    "daily_usage_pct": daily_usage_pct,
    "monthly_usage_pct": monthly_usage_pct,
} if {
    input.requested_mode == "real_eval"
    not daily_exceeded
    monthly_exceeded
}

# Mock 模式直接放行
default allow := {
    "permitted": true,
    "mode": "mock_eval",
    "reason": "mock mode requested, no budget check needed",
    "daily_usage_pct": 0,
    "monthly_usage_pct": 0,
}
