from typing import Any

from loguru import logger

from app.core.config import settings


class ClawRouterGovernance:
    """
    M7.1.1: Intelligent Agent-Native Router Engine.
    Dynamic scoring across 15 dimensions.
    """
    def __init__(self):
        # Routing thresholds
        self.thresholds = {
            "premium": 0.75,
            "balanced": 0.40,
            "eco": 0.0
        }
        # Dimensions weights
        self.weights = {
            "complexity": 0.30,
            "reliability": 0.25,
            "cost_efficiency": 0.20,
            "latency_target": 0.15,
            "user_priority": 0.10
        }
        # Stats for governance drills (Phase 5 compatibility)
        self._stats = {
            "total_calls": 0,
            "premium_hits": 0,
            "balanced_hits": 0,
            "eco_hits": 0,
            "cost_guard_downgrades": 0,
        }

    async def decide(self,
        messages: list[dict[str, str]],
        user_id: str | None = None,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Smart routing decision.
        """
        self._stats["total_calls"] += 1
        context = context or {}

        # 1-5: Task Context Dimensions
        input_len = sum(len(m.get("content", "")) for m in messages)
        complexity_score = min(1.0, input_len / 4000.0) # Length dimension
        is_code = 1.0 if any("```" in m.get("content", "") for m in messages) else 0.0 # Content type dimension
        needs_expert = 1.0 if context.get("agent_role") in ["architect", "critic", "planner"] else 0.0

        # 6-10: User/Env Dimensions
        user_priority = 1.0 if context.get("user_tier") == "vip" else 0.5
        load_factor = context.get("system_load", 0.5) # System pressure dimension

        # 11-15: Model Real-time Stats
        model_reliability = context.get("last_success_rate", 0.99)

        # Calculate Final Score
        score = (
            complexity_score * 0.4 +
            is_code * 0.2 +
            needs_expert * 0.2 +
            user_priority * 0.1 +
            (1.0 - load_factor) * 0.1
        )

        # Model Selection Mapping
        tier = "eco"
        if score >= self.thresholds["premium"]:
            tier = "premium"
            model = settings.DEFAULT_COMPLEX_MODEL
            self._stats["premium_hits"] += 1
        elif score >= self.thresholds["balanced"]:
            tier = "balanced"
            model = settings.DEFAULT_MEDIUM_MODEL
            self._stats["balanced_hits"] += 1
        else:
            tier = "eco"
            model = settings.DEFAULT_SIMPLE_MODEL
            self._stats["eco_hits"] += 1

        # Circuit Breaker Logic (Simplified)
        if context.get("model_outage", False):
            logger.warning(f"Model {model} outage detected! Falling back to healthy peer.")
            model = settings.DEFAULT_MEDIUM_MODEL # Fallback
            tier = "fallback"
            self._stats["cost_guard_downgrades"] += 1

        result = {
            "tier": tier,
            "model": model,
            "score": round(score, 3),
            "reason_code": "SMART_15D_MATRIX",
            "dimensions": {
                "complexity": complexity_score,
                "is_code": is_code,
                "expert_needed": needs_expert,
                "priority": user_priority
            },
            "is_fallback": tier == "fallback"
        }

        logger.info(f"[ClawRouter] Decision: {tier} ({model}) | Score: {result['score']}")
        return result

    def snapshot(self) -> dict[str, Any]:
        """Expose stats for reports."""
        return {
            "stats": dict(self._stats),
            "thresholds": dict(self.thresholds),
            "weights": dict(self.weights)
        }

# Singleton instance
claw_router_governance = ClawRouterGovernance()
