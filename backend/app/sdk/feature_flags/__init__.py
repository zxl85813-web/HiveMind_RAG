"""
HiveMind Feature Flag SDK
=========================
优先从 Harness Feature Flags 读取，降级时回退到 settings 环境变量。

用法:
    from app.sdk.feature_flags import ff

    # 布尔开关
    if ff.get_bool("nvidia_thinking_enabled"):
        ...

    # 字符串值（LLM Provider 切换）
    provider = ff.get_str("reasoning_provider", default="moonshot")

    # 整数值（灰度百分比）
    gray = ff.get_int("service_gray_percent", default=0)

    # 带用户上下文的灰度判断
    if ff.is_enabled("debate_mode", user_id=user_id):
        ...
"""

from app.sdk.feature_flags.service import FeatureFlagService

ff = FeatureFlagService()

__all__ = ["ff", "FeatureFlagService"]
