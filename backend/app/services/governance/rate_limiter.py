"""
Sliding-window rate limiter — RPM/RPS per tenant (and optionally per user).

Why sliding window (not fixed bucket)?
--------------------------------------
Fixed buckets allow 2x burst at the boundary (e.g. 60 reqs at 11:59:59 +
60 reqs at 12:00:01 looks like 60/min but feels like 120/min). Sliding
window keeps the last N seconds of timestamps, so the perceived rate is
true at every instant.

Implementation
--------------
- ``deque[float]`` of UTC monotonic timestamps per key.
- Read path: drop expired (`< now - window`) from the left, compare len to limit.
- Bounded by limit*2 to cap memory in pathological burst-then-idle scenarios.
- All in-memory, lock-protected. Process-singleton — the gate is a soft hint
  in multi-replica deploys (acceptable: per-replica enforcement is still
  effective at the edge, and Postgres token cap is the hard backstop).

Keys
----
- ``("tenant", tenant_id)`` for RPM
- ``("tenant_sec", tenant_id)`` for RPS
- ``("user", tenant_id, user_id)`` for per-user RPM (future)
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Optional

from loguru import logger


class RateLimitExceeded(Exception):
    """Raised when sliding-window check trips."""

    def __init__(self, *, scope: str, key: str, limit: int, window_sec: int, observed: int) -> None:
        self.scope = scope
        self.key = key
        self.limit = limit
        self.window_sec = window_sec
        self.observed = observed
        super().__init__(
            f"rate limit exceeded: scope={scope} key={key} {observed}/{limit} per {window_sec}s"
        )


class SlidingWindowRateLimiter:
    """In-process sliding window over deques."""

    def __init__(self) -> None:
        # key -> (deque[float], window_sec)
        self._windows: dict[tuple, tuple[deque[float], int]] = {}
        self._lock = threading.Lock()

    def _bump(self, key: tuple, window_sec: int, limit: int) -> int:
        """Append now, return current count within window."""
        now = time.monotonic()
        with self._lock:
            entry = self._windows.get(key)
            if entry is None:
                dq: deque[float] = deque(maxlen=max(limit * 2, 8))
                self._windows[key] = (dq, window_sec)
            else:
                dq, _ = entry
            cutoff = now - window_sec
            # Drop expired from the left
            while dq and dq[0] < cutoff:
                dq.popleft()
            dq.append(now)
            return len(dq)

    def hit(
        self,
        *,
        scope: str,
        key: str,
        limit: int,
        window_sec: int,
    ) -> None:
        """Record a request. Raise RateLimitExceeded if it pushes us over."""
        if limit <= 0:
            return  # disabled
        composite = (scope, key, window_sec)
        observed = self._bump(composite, window_sec, limit)
        if observed > limit:
            logger.warning(
                "🚦 Rate limit tripped: scope={} key={} observed={} limit={}/{}s",
                scope, key, observed, limit, window_sec,
            )
            raise RateLimitExceeded(
                scope=scope, key=key, limit=limit,
                window_sec=window_sec, observed=observed,
            )

    def peek(self, scope: str, key: str, window_sec: int) -> int:
        """Return current count within window (no insert). Useful for tests."""
        composite = (scope, key, window_sec)
        with self._lock:
            entry = self._windows.get(composite)
            if entry is None:
                return 0
            dq, _ = entry
            cutoff = time.monotonic() - window_sec
            while dq and dq[0] < cutoff:
                dq.popleft()
            return len(dq)

    def reset(self, scope: Optional[str] = None, key: Optional[str] = None) -> None:
        """Drop windows. Call without args to clear all (tests)."""
        with self._lock:
            if scope is None:
                self._windows.clear()
                return
            for k in [k for k in self._windows if k[0] == scope and (key is None or k[1] == key)]:
                self._windows.pop(k, None)


# Process-singleton
_limiter: Optional[SlidingWindowRateLimiter] = None
_singleton_lock = threading.Lock()


def get_rate_limiter() -> SlidingWindowRateLimiter:
    global _limiter
    if _limiter is None:
        with _singleton_lock:
            if _limiter is None:
                _limiter = SlidingWindowRateLimiter()
                logger.info("🚦 SlidingWindowRateLimiter initialized")
    return _limiter
