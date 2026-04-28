"""
Feature Flag 注册表
===================
所有 Flag 的定义、默认值（回退到 settings）、说明。

新增 Flag 只需在 REGISTRY 中添加一条记录，无需修改其他文件。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class FlagType(StrEnum):
    BOOL = "bool"
    STRING = "string"
    INT = "int"
    FLOAT = "float"


@dataclass
class FlagDefinition:
    """单个 Feature Flag 的完整定义。"""
    key: str                          # Harness FF 中的 flag identifier
    flag_type: FlagType               # 值类型
    settings_fallback: str            # settings 中对应的字段名（降级用）
    default: Any                      # 最终兜底默认值
    description: str                  # 说明
    tags: list[str] = field(default_factory=list)  # 分类标签


# =============================================================================
# Flag 注册表
# =============================================================================
# 分组说明:
#   llm-routing   — LLM Provider / 模型选择
#   reasoning     — 推理模式（NVIDIA NIM / chain-of-thought）
#   governance    — 服务治理灰度
#   ai-features   — AI 功能开关（辩论引擎、A/B 测试等）
# =============================================================================

REGISTRY: dict[str, FlagDefinition] = {

    # ── LLM Routing ──────────────────────────────────────────────────────────

    "reasoning_provider": FlagDefinition(
        key="reasoning_provider",
        flag_type=FlagType.STRING,
        settings_fallback="REASONING_PROVIDER",
        default="moonshot",
        description="推理层 LLM Provider（moonshot | ark | nvidia | siliconflow）",
        tags=["llm-routing"],
    ),

    "default_reasoning_model": FlagDefinition(
        key="default_reasoning_model",
        flag_type=FlagType.STRING,
        settings_fallback="DEFAULT_REASONING_MODEL",
        default="kimi-k2.5",
        description="推理层默认模型名称",
        tags=["llm-routing"],
    ),

    "default_complex_model": FlagDefinition(
        key="default_complex_model",
        flag_type=FlagType.STRING,
        settings_fallback="DEFAULT_COMPLEX_MODEL",
        default="deepseek-ai/DeepSeek-V4-Pro",
        description="Complex 层默认模型名称",
        tags=["llm-routing"],
    ),

    "default_simple_model": FlagDefinition(
        key="default_simple_model",
        flag_type=FlagType.STRING,
        settings_fallback="DEFAULT_SIMPLE_MODEL",
        default="deepseek-ai/DeepSeek-V4-Flash",
        description="Simple/Medium 层默认模型名称",
        tags=["llm-routing"],
    ),

    # ── NVIDIA NIM Reasoning ─────────────────────────────────────────────────

    "nvidia_thinking_enabled": FlagDefinition(
        key="nvidia_thinking_enabled",
        flag_type=FlagType.BOOL,
        settings_fallback="NVIDIA_THINKING_ENABLED",
        default=True,
        description="是否启用 NVIDIA NIM chain-of-thought 推理模式",
        tags=["reasoning"],
    ),

    "nvidia_reasoning_effort": FlagDefinition(
        key="nvidia_reasoning_effort",
        flag_type=FlagType.STRING,
        settings_fallback="NVIDIA_REASONING_EFFORT",
        default="max",
        description="NVIDIA NIM 推理强度（low | medium | max）",
        tags=["reasoning"],
    ),

    # ── Service Governance Gray Release ──────────────────────────────────────

    "service_gray_percent": FlagDefinition(
        key="service_gray_percent",
        flag_type=FlagType.INT,
        settings_fallback="SERVICE_GOVERNANCE_GRAY_PERCENT",
        default=0,
        description="服务治理灰度百分比（0-100），控制 split 路径流量比例",
        tags=["governance"],
    ),

    "service_topology_mode": FlagDefinition(
        key="service_topology_mode",
        flag_type=FlagType.STRING,
        settings_fallback="SERVICE_TOPOLOGY_MODE",
        default="monolith",
        description="服务拓扑模式（monolith | split）",
        tags=["governance"],
    ),

    # ── AI Features ──────────────────────────────────────────────────────────

    "debate_mode_enabled": FlagDefinition(
        key="debate_mode_enabled",
        flag_type=FlagType.BOOL,
        settings_fallback="",          # 无对应 settings 字段，默认关闭
        default=False,
        description="是否启用多模型辩论引擎（DebateOrchestrator）",
        tags=["ai-features"],
    ),

    "swarm_ab_test_enabled": FlagDefinition(
        key="swarm_ab_test_enabled",
        flag_type=FlagType.BOOL,
        settings_fallback="",
        default=False,
        description="是否启用 Swarm 策略 A/B 测试（EvalPage 对比跑分）",
        tags=["ai-features"],
    ),

    "rag_hallucination_breaker": FlagDefinition(
        key="rag_hallucination_breaker",
        flag_type=FlagType.BOOL,
        settings_fallback="",
        default=False,
        description="是否启用幻觉熔断器（低分触发重写查询并二次召回）",
        tags=["ai-features"],
    ),

    "llm_cost_daily_limit_usd": FlagDefinition(
        key="llm_cost_daily_limit_usd",
        flag_type=FlagType.FLOAT,
        settings_fallback="BUDGET_DAILY_LIMIT_USD",
        default=10.0,
        description="LLM 每日成本上限（USD），超出后降级到 Flash 模型",
        tags=["governance"],
    ),
}
