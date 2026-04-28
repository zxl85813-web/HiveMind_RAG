"""
Harness Policy Base — M8.0.3 Warning vs Error 分级
===================================================
所有 Harness 拦截策略的基类和结果数据结构。

level 语义:
  - "error"   → 阻断 Agent 输出，触发修正重试或拒绝
  - "warning" → 记录但放行，写入 Trace 供后续 Steering Loop 分析
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PolicyResult:
    """单次策略检查的结果。"""

    passed: bool
    message: str | None = None
    level: str = "error"  # "error" | "warning"
    policy_name: str = ""  # 由 Engine 自动填充
    check_type: str = "policy"  # "policy" | "computational" | "inferential"
    latency_ms: float = 0.0  # 检查耗时
    details: dict[str, Any] = field(default_factory=dict)  # 额外上下文


@dataclass
class HarnessResult:
    """
    一次完整 Harness 检查的聚合结果。

    包含所有策略的检查结果，区分 errors 和 warnings。
    """

    passed: bool  # 没有 error 级别的失败
    errors: list[PolicyResult] = field(default_factory=list)
    warnings: list[PolicyResult] = field(default_factory=list)
    total_latency_ms: float = 0.0

    @property
    def all_results(self) -> list[PolicyResult]:
        return self.errors + self.warnings

    @property
    def summary(self) -> str:
        if self.passed and not self.warnings:
            return "All checks passed."
        parts = []
        if self.errors:
            parts.append(f"{len(self.errors)} error(s)")
        if self.warnings:
            parts.append(f"{len(self.warnings)} warning(s)")
        return ", ".join(parts)


class HarnessPolicy(ABC):
    """所有 Harness 拦截策略的基类。"""

    @property
    @abstractmethod
    def name(self) -> str:
        """策略唯一标识名。"""
        ...

    @property
    def default_level(self) -> str:
        """默认严重级别，子类可覆盖。"""
        return "error"

    @abstractmethod
    async def validate(self, context: dict[str, Any]) -> PolicyResult:
        """
        执行策略校验。

        context 标准字段:
          - content: str          Agent 输出的原始文本
          - agent_name: str       Agent 名称 (CodeAgent / ResearchAgent / ...)
          - task_id: str          任务 ID
          - task_instruction: str 任务指令
          - output_type: str      输出类型 (code / json / text / markdown)
        """
        ...
