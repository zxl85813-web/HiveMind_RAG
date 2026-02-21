"""
数据脱敏 — PII 和敏感数据保护。

功能:
    - 对话日志中的敏感信息脱敏 (邮箱/手机/身份证/API Key)
    - LLM 输入/输出过滤
    - 审计日志脱敏

参见: REGISTRY.md > 后端 > audit > sanitizer
"""

import re
from typing import Any

# === 脱敏规则 ===

PATTERNS: list[tuple[str, str, str]] = [
    # (名称, 正则, 替换模板)
    ("email", r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL]"),
    ("phone_cn", r"1[3-9]\d{9}", "[PHONE]"),
    ("id_card_cn", r"\d{17}[\dXx]", "[ID_CARD]"),
    ("api_key", r"sk-[a-zA-Z0-9]{32,}", "[API_KEY]"),
    ("jwt_token", r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+", "[JWT]"),
    ("credit_card", r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "[CREDIT_CARD]"),
    ("ip_address", r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP]"),
]


def sanitize_text(text: str, rules: list[str] | None = None) -> str:
    """
    对文本进行脱敏处理。

    Args:
        text: 原始文本
        rules: 要应用的规则名列表, None 则应用全部

    Returns:
        脱敏后的文本
    """
    for name, pattern, replacement in PATTERNS:
        if rules and name not in rules:
            continue
        text = re.sub(pattern, replacement, text)
    return text


def sanitize_dict(data: dict[str, Any], sensitive_fields: list[str] | None = None) -> dict[str, Any]:
    """
    对字典中的敏感字段进行脱敏。

    Args:
        data: 原始数据
        sensitive_fields: 需要脱敏的字段名, 默认常见敏感字段

    Returns:
        脱敏后的数据 (新字典, 不修改原始)
    """
    default_fields = {"password", "token", "api_key", "secret", "authorization"}
    fields_to_mask = set(sensitive_fields) if sensitive_fields else default_fields

    result = {}
    for key, value in data.items():
        if key.lower() in fields_to_mask:
            result[key] = "***REDACTED***"
        elif isinstance(value, str):
            result[key] = sanitize_text(value)
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value, sensitive_fields)
        else:
            result[key] = value
    return result
