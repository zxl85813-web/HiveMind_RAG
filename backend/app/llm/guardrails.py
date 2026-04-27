"""
Prompt 安全防护 — 注入检测 + 输出过滤。

防护层次:
    1. 输入检测: 识别 prompt injection / jailbreak 尝试
    2. 输出过滤: 过滤 LLM 输出中的有害/不当内容
    3. 上下文隔离: 确保系统 prompt 不被用户覆盖

参见: REGISTRY.md > 后端 > llm > guardrails
@covers REQ-012
"""

import re

from loguru import logger

# === Prompt Injection 检测模式 ===

INJECTION_PATTERNS: list[tuple[str, str]] = [
    # (规则名, 正则)
    (
        "system_override",
        r"(?i)(ignore|forget|disregard)\s+(all\s+)?(previous|above|prior)\s+(instructions|rules|prompts)",
    ),
    ("role_hijack", r"(?i)(you\s+are\s+now|act\s+as|pretend\s+to\s+be|roleplay\s+as)"),
    (
        "prompt_leak",
        r"(?i)(show|reveal|tell|print|display|output)\s+(me\s+)?(your|the|system)\s+(prompt|instructions|rules)",
    ),
    ("delimiter_break", r"(?i)(```|---|\*\*\*)\s*(system|instruction|rule)"),
    ("encoding_attack", r"(?i)(base64|hex|unicode|rot13)\s*(encode|decode|convert)"),
]


class GuardrailResult:
    """防护检测结果。"""

    def __init__(
        self, safe: bool, risk_level: str = "none", matched_rules: list[str] | None = None, sanitized_input: str = ""
    ):
        self.safe = safe
        self.risk_level = risk_level  # none | low | medium | high | critical
        self.matched_rules = matched_rules or []
        self.sanitized_input = sanitized_input


def check_input(user_input: str) -> GuardrailResult:
    """
    检测用户输入是否包含 prompt injection 尝试。

    Returns:
        GuardrailResult: safe=True 则安全, False 则有风险
    """
    matched = []
    for name, pattern in INJECTION_PATTERNS:
        if re.search(pattern, user_input):
            matched.append(name)

    if not matched:
        return GuardrailResult(safe=True, risk_level="none", sanitized_input=user_input)

    risk = "medium" if len(matched) == 1 else "high"
    logger.warning(
        "⚠️ Prompt injection detected | rules={} | risk={}",
        matched,
        risk,
    )

    return GuardrailResult(
        safe=False,
        risk_level=risk,
        matched_rules=matched,
        sanitized_input=user_input,  # TODO: 实际净化处理
    )


def filter_output(llm_output: str) -> str:
    """
    过滤 LLM 输出中的不当内容。

    当前规则:
        - 移除泄露的系统指令
        - 移除内部 API 路径泄露
    """
    # 过滤系统提示泄露
    output = re.sub(r"(?i)(system\s*prompt|system\s*instruction):\s*.+", "[FILTERED]", llm_output)

    # 过滤内部路径信息
    output = re.sub(r"/app/[a-zA-Z0-9_/]+\.py", "[INTERNAL_PATH]", output)

    return output
