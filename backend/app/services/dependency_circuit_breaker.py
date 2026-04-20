"""
Dependency-level circuit breaker manager (Phase 5 / TASK-SG-003).

Supports:
- timeout by dependency
- rolling error-rate threshold
- open duration
- half-open probes

@covers REQ-015
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Literal

from loguru import logger

from app.core.config import settings

DependencyName = Literal["llm", "es", "neo4j"]


@dataclass
class _DepState:
    state: Literal["CLOSED", "OPEN", "HALF_OPEN"] = "CLOSED"
    opened_at: float = 0.0
    half_open_remaining: int = 0


class DependencyCircuitBreakerManager:
    def __init__(self):
        self._states: dict[DependencyName, _DepState] = {
            "llm": _DepState(),
            "es": _DepState(),
            "neo4j": _DepState(),
        }
        self._events: dict[DependencyName, deque[bool]] = {
            "llm": deque(maxlen=max(1, settings.CB_WINDOW_SIZE)),
            "es": deque(maxlen=max(1, settings.CB_WINDOW_SIZE)),
            "neo4j": deque(maxlen=max(1, settings.CB_WINDOW_SIZE)),
        }

    def _timeout_ms(self, dep: DependencyName) -> int:
        if dep == "llm":
            return int(settings.CB_TIMEOUT_LLM_MS)
        if dep == "es":
            return int(settings.CB_TIMEOUT_ES_MS)
        return int(settings.CB_TIMEOUT_NEO4J_MS)

    def _now(self) -> float:
        return time.time()

    def _can_attempt(self, dep: DependencyName) -> bool:
        if not settings.CB_ENABLED:
            return True

        st = self._states[dep]
        if st.state == "CLOSED":
            return True

        if st.state == "OPEN":
            if self._now() - st.opened_at >= float(settings.CB_OPEN_DURATION_SEC):
                st.state = "HALF_OPEN"
                st.half_open_remaining = max(1, int(settings.CB_HALF_OPEN_PROBES))
                logger.warning(f"[CircuitBreaker] {dep} OPEN -> HALF_OPEN")
                return True
            return False

        # HALF_OPEN
        if st.half_open_remaining > 0:
            st.half_open_remaining -= 1
            return True
        return False

    def _record_success(self, dep: DependencyName) -> None:
        if not settings.CB_ENABLED:
            return

        st = self._states[dep]
        self._events[dep].append(True)

        if st.state in {"OPEN", "HALF_OPEN"}:
            st.state = "CLOSED"
            st.opened_at = 0.0
            st.half_open_remaining = 0
            logger.info(f"[CircuitBreaker] {dep} -> CLOSED")

    def _record_failure(self, dep: DependencyName) -> None:
        if not settings.CB_ENABLED:
            return

        st = self._states[dep]
        events = self._events[dep]
        events.append(False)

        total = len(events)
        if total < int(settings.CB_MIN_REQUESTS):
            return

        failures = sum(1 for ok in events if not ok)
        error_rate = failures / max(1, total)

        if error_rate >= float(settings.CB_ERROR_RATE_THRESHOLD) or st.state == "HALF_OPEN":
            st.state = "OPEN"
            st.opened_at = self._now()
            st.half_open_remaining = 0
            logger.error(
                "[CircuitBreaker] {} -> OPEN (error_rate={:.2f}, failures={}, total={})",
                dep,
                error_rate,
                failures,
                total,
            )

    async def execute(self, dep: DependencyName, fn: Callable[[], Awaitable[object]]) -> object:
        if not self._can_attempt(dep):
            raise RuntimeError(f"Dependency circuit OPEN: {dep}")

        timeout = max(100, self._timeout_ms(dep)) / 1000.0
        try:
            result = await asyncio.wait_for(fn(), timeout=timeout)
            self._record_success(dep)
            return result
        except Exception:
            self._record_failure(dep)
            raise

    def snapshot(self) -> dict[str, object]:
        data: dict[str, object] = {}
        for dep, st in self._states.items():
            events = self._events[dep]
            total = len(events)
            failures = sum(1 for ok in events if not ok)
            data[dep] = {
                "state": st.state,
                "open_duration_sec": int(settings.CB_OPEN_DURATION_SEC),
                "timeout_ms": self._timeout_ms(dep),
                "window_total": total,
                "window_failures": failures,
                "window_error_rate": round((failures / total), 4) if total else 0.0,
            }
        return data


breaker_manager = DependencyCircuitBreakerManager()
