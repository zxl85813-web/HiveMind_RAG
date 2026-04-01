"""
Unified fallback orchestrator for Phase 5 / TASK-SG-004.

Priority chain:
1) semantic cache
2) local lightweight model
3) backup provider
"""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from loguru import logger

from app.services.cache_service import CacheService


@dataclass
class _FallbackEvent:
    ts: float
    reason_code: str
    query_preview: str


class FallbackOrchestrator:
    def __init__(self):
        self._stats: dict[str, int] = {
            "cache_hit": 0,
            "local_lightweight_success": 0,
            "backup_provider_success": 0,
            "fallback_exhausted": 0,
        }
        self._recent_events: deque[_FallbackEvent] = deque(maxlen=50)

    async def recover_text(
        self,
        *,
        query: str | None,
        local_invoke: Callable[[], Awaitable[str]] | None,
        backup_invoke: Callable[[], Awaitable[str]] | None,
    ) -> tuple[str, str]:
        """Run fallback chain and return (content, reason_code)."""
        query_text = (query or "").strip()

        if query_text:
            cached = await CacheService.get_cached_response(query_text)
            if cached and cached.get("content"):
                self._stats["cache_hit"] += 1
                self._record_event("cache_hit", query_text)
                logger.warning("[FallbackOrchestrator] using semantic cache")
                return str(cached["content"]), "fallback.cache_hit"

        if local_invoke is not None:
            try:
                local_content = (await local_invoke()).strip()
                if local_content:
                    self._stats["local_lightweight_success"] += 1
                    self._record_event("local_lightweight_success", query_text)
                    logger.warning("[FallbackOrchestrator] using local lightweight model")
                    return local_content, "fallback.local_lightweight"
            except Exception as e:
                logger.warning(f"[FallbackOrchestrator] local lightweight failed: {e}")

        if backup_invoke is not None:
            try:
                backup_content = (await backup_invoke()).strip()
                if backup_content:
                    self._stats["backup_provider_success"] += 1
                    self._record_event("backup_provider_success", query_text)
                    logger.warning("[FallbackOrchestrator] using backup provider")
                    return backup_content, "fallback.backup_provider"
            except Exception as e:
                logger.warning(f"[FallbackOrchestrator] backup provider failed: {e}")

        self._stats["fallback_exhausted"] += 1
        self._record_event("fallback_exhausted", query_text)
        raise RuntimeError("Fallback chain exhausted")

    def snapshot(self) -> dict[str, object]:
        return {
            "stats": dict(self._stats),
            "recent_events": [
                {
                    "ts": ev.ts,
                    "reason_code": ev.reason_code,
                    "query_preview": ev.query_preview,
                }
                for ev in self._recent_events
            ],
        }

    def _record_event(self, reason_code: str, query: str) -> None:
        self._recent_events.append(
            _FallbackEvent(
                ts=time.time(),
                reason_code=reason_code,
                query_preview=query[:120],
            )
        )


fallback_orchestrator = FallbackOrchestrator()
