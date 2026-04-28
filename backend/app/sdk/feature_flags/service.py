"""
FeatureFlagService
==================
优先级链（高 → 低）:
  1. Harness Feature Flags SDK（需要 HARNESS_FF_SDK_KEY 配置）
  2. settings 环境变量（FlagDefinition.settings_fallback）
  3. FlagDefinition.default 兜底值

设计原则:
  - 任何一层失败都静默降级，不抛异常，不影响业务
  - 支持带用户上下文的 is_enabled()，用于灰度判断
  - 所有读取结果写入本地缓存（TTL 30s），避免每次请求都调用 Harness API
  - 提供 get_snapshot() 供 /observability/feature-flags 端点展示当前状态
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any

from loguru import logger

from app.sdk.feature_flags.flags import REGISTRY, FlagDefinition, FlagType


class _CacheEntry:
    __slots__ = ("value", "expires_at")

    def __init__(self, value: Any, ttl: float = 30.0) -> None:
        self.value = value
        self.expires_at = time.monotonic() + ttl


class FeatureFlagService:
    """
    Feature Flag 服务。

    单例通过 `from app.sdk.feature_flags import ff` 获取。
    """

    # 缓存 TTL（秒）。Harness SDK 本身也有缓存，这里是额外的本地层。
    _CACHE_TTL = 30.0

    def __init__(self) -> None:
        self._cache: dict[str, _CacheEntry] = {}
        self._harness_client: Any | None = None
        self._harness_ready: bool = False
        self._init_attempted: bool = False

    # ── Harness SDK 初始化（懒加载）──────────────────────────────────────────

    def _ensure_harness(self) -> bool:
        """
        尝试初始化 Harness FF Python SDK。
        返回 True 表示 SDK 可用，False 表示降级到 settings。
        """
        if self._init_attempted:
            return self._harness_ready

        self._init_attempted = True

        try:
            from app.core.config import settings  # 延迟导入，避免循环

            sdk_key = getattr(settings, "HARNESS_FF_SDK_KEY", None)
            if not sdk_key:
                logger.info(
                    "[FeatureFlags] HARNESS_FF_SDK_KEY not set — using settings fallback for all flags."
                )
                return False

            # 动态导入，SDK 未安装时不影响启动
            from featureflags.client import CfClient  # type: ignore[import]
            from featureflags.config import with_base_url, with_events_url  # type: ignore[import]

            self._harness_client = CfClient(
                sdk_key,
                with_base_url("https://config.ff.harness.io/api/1.0"),
                with_events_url("https://events.ff.harness.io/api/1.0"),
            )
            self._harness_client.wait_for_initialization(timeout=5)
            self._harness_ready = True
            logger.info("[FeatureFlags] ✅ Harness FF SDK initialized successfully.")
            return True

        except ImportError:
            logger.warning(
                "[FeatureFlags] harness-featureflags package not installed. "
                "Run: pip install harness-featureflags  — falling back to settings."
            )
        except Exception as exc:
            logger.warning(
                "[FeatureFlags] Harness FF SDK init failed ({}). Falling back to settings.",
                exc,
            )

        return False

    # ── 内部读取逻辑 ──────────────────────────────────────────────────────────

    def _read_from_harness(self, flag_def: FlagDefinition, user_id: str = "anonymous") -> Any | None:
        """从 Harness SDK 读取 flag 值，失败返回 None。"""
        if not self._ensure_harness() or self._harness_client is None:
            return None

        try:
            from featureflags.evaluations.auth_target import Target  # type: ignore[import]

            target = Target(identifier=user_id, name=user_id)

            match flag_def.flag_type:
                case FlagType.BOOL:
                    return self._harness_client.bool_variation(
                        flag_def.key, target, flag_def.default
                    )
                case FlagType.STRING:
                    return self._harness_client.string_variation(
                        flag_def.key, target, str(flag_def.default)
                    )
                case FlagType.INT:
                    return int(
                        self._harness_client.number_variation(
                            flag_def.key, target, float(flag_def.default)
                        )
                    )
                case FlagType.FLOAT:
                    return float(
                        self._harness_client.number_variation(
                            flag_def.key, target, float(flag_def.default)
                        )
                    )
        except Exception as exc:
            logger.debug("[FeatureFlags] Harness read failed for '{}': {}", flag_def.key, exc)

        return None

    def _read_from_settings(self, flag_def: FlagDefinition) -> Any | None:
        """从 settings 环境变量读取 flag 值，失败返回 None。"""
        if not flag_def.settings_fallback:
            return None

        try:
            from app.core.config import settings  # 延迟导入

            raw = getattr(settings, flag_def.settings_fallback, None)
            if raw is None:
                return None

            match flag_def.flag_type:
                case FlagType.BOOL:
                    if isinstance(raw, bool):
                        return raw
                    return str(raw).lower() in ("true", "1", "yes")
                case FlagType.STRING:
                    return str(raw)
                case FlagType.INT:
                    return int(raw)
                case FlagType.FLOAT:
                    return float(raw)
        except Exception as exc:
            logger.debug(
                "[FeatureFlags] settings fallback failed for '{}': {}", flag_def.key, exc
            )

        return None

    def _resolve(self, key: str, user_id: str = "anonymous") -> Any:
        """
        完整优先级链解析：Harness → settings → default。
        结果写入本地缓存（TTL 30s）。
        """
        cache_key = f"{key}:{user_id}"
        entry = self._cache.get(cache_key)
        if entry and time.monotonic() < entry.expires_at:
            return entry.value

        flag_def = REGISTRY.get(key)
        if flag_def is None:
            logger.warning("[FeatureFlags] Unknown flag key: '{}'. Returning None.", key)
            return None

        # 1. Harness SDK
        value = self._read_from_harness(flag_def, user_id)

        # 2. settings 降级
        if value is None:
            value = self._read_from_settings(flag_def)

        # 3. 兜底默认值
        if value is None:
            value = flag_def.default

        self._cache[cache_key] = _CacheEntry(value, self._CACHE_TTL)
        return value

    # ── 公开 API ──────────────────────────────────────────────────────────────

    def get_bool(self, key: str, *, user_id: str = "anonymous", default: bool = False) -> bool:
        """读取布尔 Flag。"""
        value = self._resolve(key, user_id)
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        return str(value).lower() in ("true", "1", "yes")

    def get_str(self, key: str, *, user_id: str = "anonymous", default: str = "") -> str:
        """读取字符串 Flag。"""
        value = self._resolve(key, user_id)
        return str(value) if value is not None else default

    def get_int(self, key: str, *, user_id: str = "anonymous", default: int = 0) -> int:
        """读取整数 Flag。"""
        value = self._resolve(key, user_id)
        try:
            return int(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    def get_float(self, key: str, *, user_id: str = "anonymous", default: float = 0.0) -> float:
        """读取浮点 Flag。"""
        value = self._resolve(key, user_id)
        try:
            return float(value) if value is not None else default
        except (TypeError, ValueError):
            return default

    def is_enabled(self, key: str, *, user_id: str | None = None, query: str | None = None) -> bool:
        """
        带用户上下文的灰度判断。

        对于 BOOL 类型 flag：直接返回 flag 值。
        对于 INT 类型 flag（灰度百分比）：用 user_id + query 做稳定哈希，
        判断是否落入灰度桶。
        """
        flag_def = REGISTRY.get(key)
        if flag_def is None:
            return False

        uid = user_id or "anonymous"

        if flag_def.flag_type == FlagType.INT:
            # 灰度百分比模式
            percent = self.get_int(key, user_id=uid, default=0)
            if percent <= 0:
                return False
            if percent >= 100:
                return True
            seed = f"{uid}|{(query or '')[:128]}"
            bucket = int(hashlib.sha256(seed.encode()).hexdigest()[:8], 16) % 100
            return bucket < percent

        return self.get_bool(key, user_id=uid, default=False)

    def invalidate(self, key: str | None = None) -> None:
        """
        手动清除缓存。
        key=None 时清除全部缓存（用于测试或强制刷新）。
        """
        if key is None:
            self._cache.clear()
            logger.debug("[FeatureFlags] Full cache cleared.")
        else:
            keys_to_delete = [k for k in self._cache if k.startswith(f"{key}:")]
            for k in keys_to_delete:
                del self._cache[k]
            logger.debug("[FeatureFlags] Cache cleared for flag: '{}'.", key)

    def get_snapshot(self) -> dict[str, Any]:
        """
        返回所有 Flag 的当前值快照，供 /observability/feature-flags 端点使用。
        """
        snapshot: dict[str, Any] = {}
        for key, flag_def in REGISTRY.items():
            value = self._resolve(key)
            snapshot[key] = {
                "value": value,
                "type": flag_def.flag_type.value,
                "source": self._detect_source(flag_def, value),
                "description": flag_def.description,
                "tags": flag_def.tags,
            }
        return snapshot

    def _detect_source(self, flag_def: FlagDefinition, resolved_value: Any) -> str:
        """判断当前值来自哪一层（harness | settings | default）。"""
        if self._harness_ready:
            harness_val = self._read_from_harness(flag_def)
            if harness_val is not None and harness_val == resolved_value:
                return "harness"

        settings_val = self._read_from_settings(flag_def)
        if settings_val is not None and settings_val == resolved_value:
            return "settings"

        return "default"
