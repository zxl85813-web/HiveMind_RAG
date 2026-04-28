# =============================================================================
# RAG Evaluation Trigger Policy
# =============================================================================
# OPA (Open Policy Agent) Policy — 控制 RAG 评估的触发条件
#
# 用途:
#   1. 在 Harness Pipeline 中作为 Policy Step 执行（Harness OPA 集成）
#   2. 作为 scripts/ci/rag_eval_budget_guard.py 的逻辑规范文档
#   3. 未来可接入 Harness Policy as Code 框架统一管理
#
# 接入 Harness 方式:
#   Harness UI → Project Settings → Policies → New Policy
#   → 粘贴此文件内容 → 绑定到 Pipeline Stage
#
# 本地测试:
#   opa eval -d rag_eval_trigger_policy.rego \
#     -i '{"event":"push","branch":"main","source_branch":"","changed_paths":[]}' \
#     "data.hivemind.rag_eval.trigger"
# =============================================================================

package hivemind.rag_eval

import future.keywords.if
import future.keywords.in

# ── RAG 核心路径定义 ──────────────────────────────────────────────────────────
rag_core_paths := {
    "backend/app/services/evaluation/",
    "backend/app/services/generation/",
    "backend/app/prompts/",
    "backend/app/services/rag_gateway.py",
    "backend/app/services/retrieval/",
    "benchmarks/",
}

# ── 辅助规则：检查变更文件是否触及 RAG 核心路径 ──────────────────────────────
rag_core_changed if {
    some path in input.changed_paths
    some core_path in rag_core_paths
    startswith(path, core_path)
}

# ── 触发决策规则 ──────────────────────────────────────────────────────────────

# 规则 1: 强制真实评估（操作员手动触发）
trigger := {"mode": "real_eval", "reason": "force_real flag set by operator"} if {
    input.force_real == true
}

# 规则 2: workflow_dispatch → 真实评估
trigger := {"mode": "real_eval", "reason": "manual workflow_dispatch trigger"} if {
    input.force_real != true
    input.event == "workflow_dispatch"
}

# 规则 3: main 分支 push → 真实评估（生产门禁）
trigger := {"mode": "real_eval", "reason": "push to main branch (production gate)"} if {
    input.force_real != true
    input.event == "push"
    input.branch == "main"
}

# 规则 4a: release/* PR → main → 真实评估
trigger := {"mode": "real_eval", "reason": sprintf("release PR to main (branch: %v)", [input.source_branch])} if {
    input.force_real != true
    input.event == "pull_request"
    input.branch == "main"
    startswith(input.source_branch, "release/")
}

# 规则 4b: 非 release PR → main → Mock
trigger := {"mode": "mock_eval", "reason": sprintf("non-release PR to main (branch: %v)", [input.source_branch])} if {
    input.force_real != true
    input.event == "pull_request"
    input.branch == "main"
    not startswith(input.source_branch, "release/")
}

# 规则 5a: develop push + RAG 核心路径变更 → 真实评估
trigger := {"mode": "real_eval", "reason": "develop push with RAG core path changes"} if {
    input.force_real != true
    input.event == "push"
    input.branch == "develop"
    rag_core_changed
}

# 规则 5b: develop push + 无 RAG 核心路径变更 → Mock
trigger := {"mode": "mock_eval", "reason": "develop push without RAG core changes"} if {
    input.force_real != true
    input.event == "push"
    input.branch == "develop"
    not rag_core_changed
}

# 规则 6: feature PR → develop → Mock（快速反馈，零成本）
trigger := {"mode": "mock_eval", "reason": sprintf("feature PR to develop (branch: %v)", [input.source_branch])} if {
    input.force_real != true
    input.event == "pull_request"
    input.branch == "develop"
}

# 规则 7: 兜底 → Mock（保守策略）
default trigger := {"mode": "mock_eval", "reason": "unmatched event/branch combination, defaulting to mock"}
