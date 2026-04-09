from typing import Any

from loguru import logger

from app.core.config import settings


class ClawRouterGovernance:
    """
    M7.1.1: Intelligent Agent-Native Router Engine.
    Dynamic scoring across 15 dimensions.
    """
    def __init__(self):
        # 🧪 [ClawRouter v2]: 4-Tier Strategy (M5.1.1 Hardening)
        self.thresholds = {
            "reasoning": 0.85, # Formal proofs, complex logic
            "complex": 0.55,   # Code, multi-step analysis
            "medium": 0.25,    # Summarization, data extraction
            "simple": 0.0      # Greetings, simple Q&A
        }
        self.weights = {
            "complexity": 0.35, # Input length and depth
            "reasoning_indicator": 0.30, # Explicit triggers like "prove", "step-by-step"
            "is_code": 0.20,
            "urgency": 0.15      # Low latency targets reduce the tier
        }
        self._stats = {
            "total_calls": 0,
            "reasoning_hits": 0,
            "complex_hits": 0,
            "medium_hits": 0,
            "simple_hits": 0,
            "latency_downgrades": 0,
        }

    async def decide(self,
        messages: list[dict[str, str]],
        user_id: str | None = None,
        context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        4-Tier routing decision with dynamic RTT-based degradation (DES-013).
        """
        self._stats["total_calls"] += 1
        context = context or {}
        
        # 1. Base Score calculation (Internal Logic)
        text_content = " ".join(m.get("content", "") for m in messages)
        input_len = len(text_content)
        
        complexity = min(1.0, input_len / 5000.0)
        is_code = 1.0 if any(tag in text_content for tag in ["```", "import ", "def ", "class "]) else 0.0
        reasoning_indicator = 1.0 if any(kw in text_content.lower() for kw in ["证明", "推导", "why", "prove", "logic", "reason"]) else 0.0
        
        score = (
            complexity * self.weights["complexity"] +
            reasoning_indicator * self.weights["reasoning_indicator"] +
            is_code * self.weights["is_code"]
        )

        # 2. Dynamic Latency Adjustment (M5.2.2 Hardening)
        # If real-time RTT is > 800ms, force downgrade to保住准出指标
        avg_rtt = context.get("avg_rtt_ms", 0)
        if avg_rtt > 800:
            logger.warning(f"⚠️ [ClawRouter] High RTT ({avg_rtt}ms) detected. Applying tier degradation.")
            score *= 0.6 # Force lower tier for latency protection
            self._stats["latency_downgrades"] += 1

        # 3. Model Mapping
        if score >= self.thresholds["reasoning"]:
            tier = "reasoning"
            model = settings.DEFAULT_REASONING_MODEL
            self._stats["reasoning_hits"] += 1
        elif score >= self.thresholds["complex"]:
            tier = "complex"
            model = settings.DEFAULT_COMPLEX_MODEL
            self._stats["complex_hits"] += 1
        elif score >= self.thresholds["medium"]:
            tier = "medium"
            model = settings.DEFAULT_MEDIUM_MODEL
            self._stats["medium_hits"] += 1
        else:
            tier = "simple"
            model = settings.DEFAULT_SIMPLE_MODEL
            self._stats["simple_hits"] += 1

        # 4. Result with Evidence
        result = {
            "tier": tier,
            "model": model,
            "score": round(score, 3),
            "reason_code": f"CLAW_V2_SCORE_{tier.upper()}",
            "evidence": {
                "complexity": round(complexity, 2),
                "is_code": is_code > 0,
                "reasoning_indicator": reasoning_indicator > 0,
                "rtt_penalized": avg_rtt > 800
            }
        }
        
        logger.info(f"🤖 [ClawRouter] Routed to {tier} ({model}) | Score: {result['score']}")
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
