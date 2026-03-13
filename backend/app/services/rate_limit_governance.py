"""
Route-level rate limit governance center (Phase 5 / TASK-SG-005).

Provides:
- token bucket limits at route/user/key granularity
- in-memory hot update for policy set
- operational snapshot for observability
"""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Any


@dataclass
class BucketRule:
    enabled: bool
    capacity: int
    refill_per_sec: float


@dataclass
class RouteRateLimitPolicy:
    route: str
    route_rule: BucketRule
    user_rule: BucketRule
    key_rule: BucketRule
    updated_at: float


@dataclass
class _BucketState:
    tokens: float
    last_refill_ts: float


@dataclass
class _Violation:
    ts: float
    route: str
    dimension: str
    subject: str
    retry_after_sec: int


class RateLimitGovernanceCenter:
    def __init__(self):
        self._policies: dict[str, RouteRateLimitPolicy] = {}
        self._buckets: dict[str, _BucketState] = {}
        self._violations: deque[_Violation] = deque(maxlen=200)
        self._stats: dict[str, int] = {
            "allowed": 0,
            "blocked": 0,
            "policy_updates": 0,
        }
        self._load_defaults()

    def _load_defaults(self) -> None:
        now = time.time()
        defaults = [
            RouteRateLimitPolicy(
                route="/api/v1/chat/completions",
                route_rule=BucketRule(enabled=True, capacity=40, refill_per_sec=40 / 60.0),
                user_rule=BucketRule(enabled=True, capacity=20, refill_per_sec=20 / 60.0),
                key_rule=BucketRule(enabled=True, capacity=30, refill_per_sec=30 / 60.0),
                updated_at=now,
            ),
            RouteRateLimitPolicy(
                route="/api/v1/knowledge/documents",
                route_rule=BucketRule(enabled=True, capacity=30, refill_per_sec=30 / 60.0),
                user_rule=BucketRule(enabled=True, capacity=10, refill_per_sec=10 / 60.0),
                key_rule=BucketRule(enabled=True, capacity=15, refill_per_sec=15 / 60.0),
                updated_at=now,
            ),
        ]
        self._policies = {p.route: p for p in defaults}

    def update_policies(self, policies: list[dict[str, Any]]) -> dict[str, object]:
        now = time.time()
        updated: dict[str, RouteRateLimitPolicy] = {}
        for item in policies:
            route = str(item.get("route", "")).strip()
            if not route:
                continue

            route_rule = self._parse_rule(item.get("route_rule"), default_capacity=100)
            user_rule = self._parse_rule(item.get("user_rule"), default_capacity=60)
            key_rule = self._parse_rule(item.get("key_rule"), default_capacity=80)

            updated[route] = RouteRateLimitPolicy(
                route=route,
                route_rule=route_rule,
                user_rule=user_rule,
                key_rule=key_rule,
                updated_at=now,
            )

        self._policies = updated
        self._stats["policy_updates"] += 1
        return self.snapshot()

    def check(self, *, route: str, user_id: str | None, api_key: str | None) -> dict[str, object]:
        policy = self._policies.get(route)
        if policy is None:
            self._stats["allowed"] += 1
            return {
                "allowed": True,
                "route": route,
                "dimension": None,
                "retry_after_sec": 0,
                "remaining": -1,
                "reason_code": None,
            }

        checks = [
            ("route", policy.route_rule, f"route:{route}"),
            ("user", policy.user_rule, f"user:{route}:{user_id or 'anonymous'}"),
            ("key", policy.key_rule, f"key:{route}:{self._normalize_key(api_key)}"),
        ]

        min_remaining = 10**9
        for dimension, rule, bucket_id in checks:
            if dimension == "key" and not api_key:
                continue

            allowed, retry_after, remaining = self._consume(bucket_id=bucket_id, rule=rule)
            min_remaining = min(min_remaining, remaining)
            if not allowed:
                self._stats["blocked"] += 1
                subject = user_id or self._normalize_key(api_key)
                self._violations.append(
                    _Violation(
                        ts=time.time(),
                        route=route,
                        dimension=dimension,
                        subject=subject,
                        retry_after_sec=retry_after,
                    )
                )
                return {
                    "allowed": False,
                    "route": route,
                    "dimension": dimension,
                    "retry_after_sec": retry_after,
                    "remaining": max(0, remaining),
                    "reason_code": f"rate_limited.{dimension}",
                }

        self._stats["allowed"] += 1
        return {
            "allowed": True,
            "route": route,
            "dimension": None,
            "retry_after_sec": 0,
            "remaining": max(0, min_remaining if min_remaining < 10**9 else -1),
            "reason_code": None,
        }

    def snapshot(self) -> dict[str, object]:
        return {
            "stats": dict(self._stats),
            "policy_count": len(self._policies),
            "policies": [
                {
                    "route": p.route,
                    "route_rule": self._rule_to_dict(p.route_rule),
                    "user_rule": self._rule_to_dict(p.user_rule),
                    "key_rule": self._rule_to_dict(p.key_rule),
                    "updated_at": p.updated_at,
                }
                for p in sorted(self._policies.values(), key=lambda x: x.route)
            ],
            "recent_violations": [
                {
                    "ts": v.ts,
                    "route": v.route,
                    "dimension": v.dimension,
                    "subject": v.subject,
                    "retry_after_sec": v.retry_after_sec,
                }
                for v in self._violations
            ],
        }

    def _consume(self, *, bucket_id: str, rule: BucketRule) -> tuple[bool, int, int]:
        if not rule.enabled:
            return True, 0, max(0, rule.capacity)

        now = time.time()
        capacity = max(1, int(rule.capacity))
        refill_rate = max(0.0, float(rule.refill_per_sec))

        st = self._buckets.get(bucket_id)
        if st is None:
            st = _BucketState(tokens=float(capacity), last_refill_ts=now)
            self._buckets[bucket_id] = st

        elapsed = max(0.0, now - st.last_refill_ts)
        if elapsed > 0 and refill_rate > 0:
            st.tokens = min(float(capacity), st.tokens + elapsed * refill_rate)
            st.last_refill_ts = now
        else:
            st.last_refill_ts = now

        if st.tokens >= 1.0:
            st.tokens -= 1.0
            return True, 0, int(st.tokens)

        if refill_rate <= 0:
            return False, 60, 0

        retry_after = int((1.0 - st.tokens) / refill_rate) + 1
        return False, max(1, retry_after), 0

    def _parse_rule(self, raw: Any, *, default_capacity: int) -> BucketRule:
        if not isinstance(raw, dict):
            return BucketRule(enabled=True, capacity=default_capacity, refill_per_sec=default_capacity / 60.0)

        enabled = bool(raw.get("enabled", True))
        capacity = max(1, int(raw.get("capacity", default_capacity)))
        refill_per_sec = float(raw.get("refill_per_sec", capacity / 60.0))
        return BucketRule(enabled=enabled, capacity=capacity, refill_per_sec=max(0.0, refill_per_sec))

    def _normalize_key(self, api_key: str | None) -> str:
        if not api_key:
            return "none"
        compact = "".join(ch for ch in api_key if ch.isalnum())
        return (compact[:8] + "..." + compact[-4:]) if len(compact) > 12 else compact

    def _rule_to_dict(self, rule: BucketRule) -> dict[str, object]:
        return {
            "enabled": rule.enabled,
            "capacity": rule.capacity,
            "refill_per_sec": round(rule.refill_per_sec, 6),
        }


rate_limit_governance_center = RateLimitGovernanceCenter()
