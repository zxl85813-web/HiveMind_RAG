"""
HarnessEngine — M8.0.1 Graph-Integrated Harness
=================================================
图谱感知的运行时治理引擎。

执行链路:
  WorkerAgent.execute()
    → _run_logic()                    # Agent 生成输出
    → harness.check_agent_output()    # 🆕 Computational + Policy 检查
    → _reflect()                      # LLM 自我反思
    → record_swarm_span()             # 写入 Trace

设计:
  - Context-Aware: 根据 agent_name 选择不同的策略组合
  - Warning vs Error: warning 记录但放行，error 阻断
  - 所有检查结果写入 HarnessResult，供 Trace 和图谱记录
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from .computational_sensors import (
    ASTValidationSensor,
    IncompleteCodeSensor,
    JSONSchemaSensor,
)
from .policies import HiveConformancePolicy, SecuritySentinelPolicy
from .policy import HarnessPolicy, HarnessResult, PolicyResult


# ── Agent → Policy 映射 ──────────────────────────────────────────────────────
# 每种 Agent 类型使用不同的策略组合。
# 新增 Agent 类型时只需在这里加一行。

def _build_default_policies() -> list[HarnessPolicy]:
    return [SecuritySentinelPolicy(), HiveConformancePolicy()]


def _build_code_policies() -> list[HarnessPolicy]:
    return [
        SecuritySentinelPolicy(),
        ASTValidationSensor(),
        IncompleteCodeSensor(),
    ]


def _build_reviewer_policies() -> list[HarnessPolicy]:
    return [
        JSONSchemaSensor(),
        IncompleteCodeSensor(),
    ]


def _build_research_policies() -> list[HarnessPolicy]:
    return [
        IncompleteCodeSensor(),
    ]


AGENT_POLICY_MAP: dict[str, list[HarnessPolicy]] = {
    "CodeAgent": _build_code_policies(),
    "HVM-Reviewer": _build_reviewer_policies(),
    "ResearchAgent": _build_research_policies(),
}

# 所有 Agent 共享的全局策略（始终执行）
GLOBAL_POLICIES: list[HarnessPolicy] = _build_default_policies()


class HarnessEngine:
    """
    HiveMind AI 护栏引擎 (Harness Engine)。

    Responsible for multi-dimensional checking of AI agent outputs.
    Supports context-aware policy selection based on agent type.
    """

    def __init__(self) -> None:
        self._global_policies = GLOBAL_POLICIES
        self._agent_policies = AGENT_POLICY_MAP
        logger.info(
            f"🛡️ HarnessEngine initialized: {len(self._global_policies)} global policies, "
            f"{len(self._agent_policies)} agent-specific profiles"
        )

    def get_policies_for_agent(self, agent_name: str) -> list[HarnessPolicy]:
        """获取指定 Agent 的策略列表（全局 + Agent 专属）。"""
        agent_specific = self._agent_policies.get(agent_name, [])
        return self._global_policies + agent_specific

    async def check_agent_output(
        self,
        *,
        content: str,
        agent_name: str,
        task_id: str = "",
        task_instruction: str = "",
        output_type: str = "text",
    ) -> HarnessResult:
        """
        对 Agent 输出执行完整的 Harness 检查。

        这是 WorkerAgent.execute() 调用的主入口。

        Args:
            content: Agent 输出的原始文本
            agent_name: Agent 名称
            task_id: 任务 ID
            task_instruction: 任务指令
            output_type: 输出类型 (code / json / text / markdown)

        Returns:
            HarnessResult: 聚合结果，包含 errors 和 warnings
        """
        t0 = time.monotonic()

        context: dict[str, Any] = {
            "content": content,
            "agent_name": agent_name,
            "task_id": task_id,
            "task_instruction": task_instruction,
            "output_type": output_type,
        }

        policies = self.get_policies_for_agent(agent_name)
        errors: list[PolicyResult] = []
        warnings: list[PolicyResult] = []

        for policy in policies:
            pt0 = time.monotonic()
            try:
                result = await policy.validate(context)
            except Exception as exc:
                logger.error(f"Harness policy {policy.name} crashed: {exc}")
                result = PolicyResult(
                    passed=False,
                    message=f"Policy {policy.name} internal error: {exc}",
                    level="warning",  # 策略自身崩溃不应阻断 Agent
                    check_type="policy",
                )

            result.policy_name = policy.name
            result.latency_ms = (time.monotonic() - pt0) * 1000

            if not result.passed:
                effective_level = result.level or policy.default_level
                if effective_level == "error":
                    errors.append(result)
                    logger.warning(
                        f"🛡️ Harness [ERROR] {policy.name} → {result.message}"
                    )
                else:
                    warnings.append(result)
                    logger.info(
                        f"🛡️ Harness [WARN] {policy.name} → {result.message}"
                    )

        total_ms = (time.monotonic() - t0) * 1000
        passed = len(errors) == 0

        if passed and not warnings:
            logger.info(
                f"🛡️ Harness [PASS] {agent_name}/{task_id} — "
                f"{len(policies)} policies in {total_ms:.1f}ms"
            )
        elif passed:
            logger.info(
                f"🛡️ Harness [PASS+WARN] {agent_name}/{task_id} — "
                f"{len(warnings)} warning(s) in {total_ms:.1f}ms"
            )
        else:
            logger.warning(
                f"🛡️ Harness [BLOCKED] {agent_name}/{task_id} — "
                f"{len(errors)} error(s), {len(warnings)} warning(s) in {total_ms:.1f}ms"
            )

        return HarnessResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            total_latency_ms=total_ms,
        )

    # ── 向后兼容的旧接口 ──────────────────────────────────────────────────

    async def check_change(self, change_context: dict[str, Any]) -> PolicyResult:
        """
        向后兼容：验证一个代码变更请求。

        新代码应使用 check_agent_output()。
        """
        result = await self.check_agent_output(
            content=change_context.get("content", ""),
            agent_name=change_context.get("agent_name", "unknown"),
            task_id=change_context.get("task_id", ""),
            output_type=change_context.get("output_type", "text"),
        )
        if result.passed:
            return PolicyResult(passed=True, message="Checked by HiveMind Harness")
        first_error = result.errors[0] if result.errors else result.warnings[0]
        return first_error

    async def verify_output(self, content: str, output_type: str = "text") -> PolicyResult:
        """
        M8.0.4: 验证 AI 生成的内容是否符合规范。

        仅运行 Computational Sensors（零 LLM 成本）。
        """
        sensors: list[HarnessPolicy] = [
            ASTValidationSensor(),
            JSONSchemaSensor(),
            IncompleteCodeSensor(),
        ]

        for sensor in sensors:
            result = await sensor.validate({"content": content, "output_type": output_type})
            if not result.passed and result.level == "error":
                return result

        return PolicyResult(passed=True, message="Output verification passed", check_type="computational")


# ── 单例 ──────────────────────────────────────────────────────────────────────

_harness_engine: HarnessEngine | None = None


def get_harness_engine() -> HarnessEngine:
    global _harness_engine
    if not _harness_engine:
        _harness_engine = HarnessEngine()
    return _harness_engine
