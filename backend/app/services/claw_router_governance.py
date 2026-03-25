"""
ClawRouterGovernance — Multi-factor dynamic model routing.
Logic separated into dedicated service for Phase 4/5. 
"""

import math
from typing import Any
from loguru import logger
from app.core.config import settings

class ClawRouterGovernance:
    def __init__(self):
        # Default tier distribution (can be loaded from DB/Redis later)
        self.eco_threshold = 0.4
        self.premium_threshold = 0.8

    def decide(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        """
        Routing decision based on complexity, cost and session state.
        Currently using length-based complexity as MVP.
        """
        # Calculate context length
        content = " ".join([m.get("content", "") for m in messages])
        complexity_score = min(1.0, len(content) / 2000.0) # Normalizing to 0-1 (max 2000 chars)

        tier = "eco"
        model = settings.DEFAULT_SIMPLE_MODEL

        if complexity_score > self.premium_threshold:
            tier = "premium"
            model = settings.DEFAULT_COMPLEX_MODEL
        elif complexity_score > self.eco_threshold:
            tier = "balanced"
            model = settings.DEFAULT_MEDIUM_MODEL
        
        # Override for specific system roles if needed
        # (e.g. reasoning tasks forced to premium)

        return {
            "tier": tier,
            "model": model,
            "score": complexity_score,
            "reason_code": "COMPLEXITY_DRIVEN",
            "is_cached": False
        }

# Singleton instance
claw_router_governance = ClawRouterGovernance()
