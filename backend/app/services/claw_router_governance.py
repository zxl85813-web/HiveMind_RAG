"""
ClawRouter governance layer (Phase 5 / TASK-SG-006).

Implements:
- multi-factor weighted score (complexity/token/SLA/cost)
- dynamic Eco/Premium route decision
- cost guardrail downgrade logic
"""

from __future__ import annotations

import re
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from app.core.config import settings


@dataclass
class _RoutingEvent:
    ts: float
    tier: str
    model: str
    score: float
    reason_code: str
    complexity: float
    token_pressure: float
    sla_pressure: float
    cost_pressure: float


class ClawRouterGovernance:
    def __init__(self):
        self._premium_threshold = 0.62
        self._max_tokens_for_eco_guard = 2200
        self._cost_guard_enabled = True
        self._weights = {
            "complexity": 0.38,
            "token_pressure": 0.24,
            "sla_pressure": 0.20,
            "cost_pressure": 0.18,
        }
        self._config_version = 1
        self._updated_at_ts = time.time()
        self._stats: dict[str, int] = {
            "eco_routes": 0,
            "premium_routes": 0,
            "cost_guard_downgrades": 0,
        }
        self._recent_events: deque[_RoutingEvent] = deque(maxlen=120)

    def decide(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        text = " ".join(m.get("content", "") for m in messages).strip()

        complexity = self._complexity_score(text)
        token_pressure = self._token_pressure(text)
        sla_pressure = self._sla_pressure(text)
        cost_pressure = self._cost_pressure(text)

        score = (
            complexity * self._weights["complexity"]
            + token_pressure * self._weights["token_pressure"]
            + sla_pressure * self._weights["sla_pressure"]
            + cost_pressure * self._weights["cost_pressure"]
        )

        tier = "premium" if score >= self._premium_threshold else "eco"
        reason_code = "claw_router.dynamic"

        estimated_tokens = max(1, len(text) // 4)
        if (
            self._cost_guard_enabled
            and tier == "premium"
            and estimated_tokens >= self._max_tokens_for_eco_guard
            and complexity < 0.80
        ):
            tier = "eco"
            reason_code = "claw_router.cost_guard_downgrade"
            self._stats["cost_guard_downgrades"] += 1

        model = self._model_for_tier(tier)
        if tier == "eco":
            self._stats["eco_routes"] += 1
        else:
            self._stats["premium_routes"] += 1

        self._recent_events.append(
            _RoutingEvent(
                ts=time.time(),
                tier=tier,
                model=model,
                score=round(score, 4),
                reason_code=reason_code,
                complexity=round(complexity, 4),
                token_pressure=round(token_pressure, 4),
                sla_pressure=round(sla_pressure, 4),
                cost_pressure=round(cost_pressure, 4),
            )
        )

        return {
            "tier": tier,
            "model": model,
            "score": round(score, 4),
            "reason_code": reason_code,
            "factors": {
                "complexity": round(complexity, 4),
                "token_pressure": round(token_pressure, 4),
                "sla_pressure": round(sla_pressure, 4),
                "cost_pressure": round(cost_pressure, 4),
            },
            "estimated_tokens": estimated_tokens,
        }

    def update_config(self, payload: dict[str, Any]) -> dict[str, object]:
        if "premium_threshold" in payload:
            premium_threshold = float(payload["premium_threshold"])
            if not 0.0 <= premium_threshold <= 1.0:
                raise ValueError("premium_threshold must be between 0 and 1")
            self._premium_threshold = premium_threshold

        if "max_tokens_for_eco_guard" in payload:
            max_tokens = int(payload["max_tokens_for_eco_guard"])
            if max_tokens < 1:
                raise ValueError("max_tokens_for_eco_guard must be >= 1")
            self._max_tokens_for_eco_guard = max_tokens

        if "cost_guard_enabled" in payload:
            self._cost_guard_enabled = bool(payload["cost_guard_enabled"])

        if "weights" in payload:
            raw_weights = payload["weights"]
            if not isinstance(raw_weights, dict):
                raise ValueError("weights must be an object")

            required_keys = {"complexity", "token_pressure", "sla_pressure", "cost_pressure"}
            if set(raw_weights.keys()) != required_keys:
                raise ValueError("weights must include complexity/token_pressure/sla_pressure/cost_pressure")

            parsed_weights = {k: float(v) for k, v in raw_weights.items()}
            for value in parsed_weights.values():
                if value < 0:
                    raise ValueError("weights values must be >= 0")
            weight_sum = sum(parsed_weights.values())
            if weight_sum <= 0:
                raise ValueError("weights sum must be > 0")

            self._weights = {k: v / weight_sum for k, v in parsed_weights.items()}

        self._config_version += 1
        self._updated_at_ts = time.time()
        return self.snapshot()

    def snapshot(self) -> dict[str, object]:
        total_decisions = self._stats["eco_routes"] + self._stats["premium_routes"]
        eco_ratio = round(self._stats["eco_routes"] / total_decisions, 4) if total_decisions else 0.0
        premium_ratio = round(self._stats["premium_routes"] / total_decisions, 4) if total_decisions else 0.0
        downgrade_ratio = (
            round(self._stats["cost_guard_downgrades"] / total_decisions, 4) if total_decisions else 0.0
        )

        return {
            "config_version": self._config_version,
            "updated_at_ts": self._updated_at_ts,
            "premium_threshold": self._premium_threshold,
            "max_tokens_for_eco_guard": self._max_tokens_for_eco_guard,
            "cost_guard_enabled": self._cost_guard_enabled,
            "weights": dict(self._weights),
            "stats": dict(self._stats),
            "metrics": {
                "total_decisions": total_decisions,
                "eco_ratio": eco_ratio,
                "premium_ratio": premium_ratio,
                "cost_guard_downgrade_ratio": downgrade_ratio,
            },
            "recent_events": [
                {
                    "ts": ev.ts,
                    "tier": ev.tier,
                    "model": ev.model,
                    "score": ev.score,
                    "reason_code": ev.reason_code,
                    "complexity": ev.complexity,
                    "token_pressure": ev.token_pressure,
                    "sla_pressure": ev.sla_pressure,
                    "cost_pressure": ev.cost_pressure,
                }
                for ev in self._recent_events
            ],
        }

    def _model_for_tier(self, tier: str) -> str:
        if tier == "premium":
            return settings.DEFAULT_COMPLEX_MODEL or settings.MODEL_GLM5
        return settings.DEFAULT_MEDIUM_MODEL or settings.MODEL_DEEPSEEK_V3

    def _complexity_score(self, text: str) -> float:
        if not text:
            return 0.0
        lowered = text.lower()
        keywords = [
            "architecture",
            "设计",
            "proof",
            "优化",
            "tradeoff",
            "benchmark",
            "multi-step",
            "推理",
            "debug",
            "故障",
            "root cause",
        ]
        hit = sum(1 for kw in keywords if kw in lowered)
        structure_bonus = 0.0
        if "```" in text:
            structure_bonus += 0.2
        if re.search(r"\b(if|for|while|async|await|class|def)\b", lowered):
            structure_bonus += 0.15
        return min(1.0, hit * 0.12 + structure_bonus)

    def _token_pressure(self, text: str) -> float:
        tokens = max(1, len(text) // 4)
        return min(1.0, tokens / 3000.0)

    def _sla_pressure(self, text: str) -> float:
        lowered = text.lower()
        urgent_markers = ["urgent", "asap", "p0", "线上", "紧急", "立即"]
        return 0.9 if any(m in lowered for m in urgent_markers) else 0.45

    def _cost_pressure(self, text: str) -> float:
        lowered = text.lower()
        cost_markers = ["low cost", "cheap", "省钱", "cost", "预算", "token"]
        return 0.25 if any(m in lowered for m in cost_markers) else 0.55


claw_router_governance = ClawRouterGovernance()
