"""
记忆治理：价值密度评估引擎 (Memory Value Density Engine)
用于识别高价值记忆（入图谱、入摘要）与低价值记忆（仅入向量）。
"""

from loguru import logger
from pydantic import BaseModel, Field


class ValueDensityScore(BaseModel):
    score: float = Field(..., description="Value density score from 0.0 to 1.0")
    tier_recommendation: str = Field(..., description="VECTOR | ABSTRACT | GRAPH")
    reasoning: str = Field(..., description="Brief reasoning for the score")
    keywords: list[str] = Field(default_factory=list, description="Key high-value terms FOUND")

class MemoryGovernanceService:
    """
    负责评估记忆片段的价值密度。
    核心逻辑：使用 LLM 识别事实密度、决策价值和长期复用性。
    """

    async def evaluate_density(self, content: str) -> ValueDensityScore:
        """
        评估文本的价值密度。
        """
        if len(content) < 10:
            return ValueDensityScore(
                score=0.1,
                tier_recommendation="VECTOR",
                reasoning="Content too short to be of high value.",
                keywords=[]
            )

        from app.core.algorithms.classification import classifier_service

        prompt = (
            "Evaluate the 'Value Density' of the following memory segment. "
            "High value includes: Factual records, architectural decisions, technical solutions, user preferences, project insights.\n"
            "Low value includes: Small talk, greetings, error logs without context, redundant chatter.\n\n"
            f"Content:\n{content}"
        )

        try:
            logger.debug(f"⚖️ [MemoryGov] Evaluating value density for content length: {len(content)}")
            result = await classifier_service.extract_model(
                text=prompt,
                target_model=ValueDensityScore,
                instruction="You are a data librarian. Categorize information by its long-term retrieval value."
            )
            return result
        except Exception as e:
            logger.error(f"Memory value density evaluation failed: {e}")
            # Fallback to balanced approach
            return ValueDensityScore(
                score=0.5,
                tier_recommendation="ABSTRACT",
                reasoning=f"Evaluation failed: {e}",
                keywords=[]
            )

memory_governance_service = MemoryGovernanceService()
