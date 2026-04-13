import json
from loguru import logger
from app.agents.schemas import RoutingDecision, ReflectionResult

class SwarmParser:
    """Helper for parsing LLM structured outputs."""

    @staticmethod
    def parse_routing_decision(content: str) -> RoutingDecision:
        """Parse LLM output into RoutingDecision, with fallback."""
        cleaned = SwarmParser.clean_json(content)
        try:
            data = json.loads(cleaned)
            return RoutingDecision(**data)
        except Exception as e:
            logger.warning(f"Failed to parse routing JSON. Content: {cleaned[:200]!r}. Error: {e}")
            return RoutingDecision(
                next_agent="FINISH",
                uncertainty=1.0,
                reasoning="JSON extraction failed",
                task_refinement="",
            )

    @staticmethod
    def parse_reflection_result(content: str) -> ReflectionResult:
        """Parse LLM output into ReflectionResult, with fallback."""
        cleaned = SwarmParser.clean_json(content)
        try:
            data = json.loads(cleaned)
            return ReflectionResult(**data)
        except Exception as e:
            logger.warning(f"Failed to parse reflection JSON. Content: {cleaned[:200]!r}. Error: {e}")
            return ReflectionResult(
                quality_score=0.7,
                issues=[],
                suggestions=[],
                verdict="APPROVE",
            )

    @staticmethod
    def clean_json(content: str) -> str:
        """Remove markdown code fences from LLM output."""
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        return content.strip()
