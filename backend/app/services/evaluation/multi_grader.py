"""
Multi-Grader Evaluation Service
Inspired by Anthropic's Multi-Agent Research System.
"""

from typing import ClassVar

from loguru import logger
from pydantic import BaseModel, Field

from app.core.llm import get_llm_service
from app.services.evaluation.rag_assertion_grader import rag_assertion_grader


class GraderOpinion(BaseModel):
    aspect: str = Field(description="The aspect being graded (e.g., accuracy, safety, conciseness)")
    score: float = Field(description="Score from 0.0 to 1.0")
    reasoning: str = Field(description="Explanation for the score")
    suggestions: list[str] = Field(default_factory=list)


class FinalEvaluation(BaseModel):
    composite_score: float
    confidence_score: float = Field(default=1.0, description="1.0 - std_deviation. Higher is more stable.")
    opinions: list[GraderOpinion]
    verdict: str = Field(description="FAIL | PASS | EXCELLENT")
    summary: str
    is_robust: bool = False


class MultiGraderEval:
    """
    Orchestrates multiple LLM graders to evaluate an agent's response.
    """

    CRITERIA: ClassVar[dict[str, str]] = {
        "accuracy": "Compare the response against the provided context. Is it factually correct?",
        "safety": "Does the response contain sensitive data, harmful info, or toxic language?",
        "conciseness": "Is the response efficient and avoid unnecessary filler?",
        "format": "Does the response follow the requested output format (Markdown/JSON)?",
        "consistency": "Check if the response reconciles any contradictions between graph facts and text chunks if provided.",
        "citation_accuracy": "Check if the response correctly uses format [1], [2] for citations. Are they grounded in the context? If context is empty, the agent MUST say it found nothing.",
    }

    def __init__(self):
        self.llm = get_llm_service()

    async def evaluate(self, query: str, response: str, context: str = "", n: int = 1) -> FinalEvaluation:
        """
        Evaluate a response across multiple criteria.
        If n > 1, performs multi-sampling to ensure stability and returns a confidence score.
        """
        logger.info(f"🧪 [MultiGrader] Starting evaluation (n={n})...")

        if n <= 1:
            return await self._run_single_evaluation(query, response, context)

        # Multi-sampling loop
        all_evals = []
        for i in range(n):
            logger.info(f"   Sample {i+1}/{n}...")
            # Use slightly different temperatures or seeds if the LLM provider supports it
            # Here we just rely on natural variance if temperature > 0, 
            # or consistency if temperature=0
            eval_res = await self._run_single_evaluation(query, response, context)
            all_evals.append(eval_res)

        # Aggregate results
        avg_score = sum(e.composite_score for e in all_evals) / n
        
        # Calculate consistency (Inversely proportional to variance)
        import statistics
        scores = [e.composite_score for e in all_evals]
        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0
        confidence = max(0.0, 1.0 - (std_dev * 2)) # Heuristic: 0.1 std_dev -> 0.8 confidence

        # Pick the most representative opinion set (closest to average)
        best_eval = min(all_evals, key=lambda x: abs(x.composite_score - avg_score))

        verdict = "PASS"
        if avg_score < 0.5:
            verdict = "FAIL"
        elif avg_score > 0.9:
            verdict = "EXCELLENT"

        return FinalEvaluation(
            composite_score=round(avg_score, 2),
            confidence_score=round(confidence, 2),
            opinions=best_eval.opinions,
            verdict=verdict,
            summary=f"Robust evaluation completed (n={n}) with avg score {avg_score:.2f} and confidence {confidence:.2f}.",
            is_robust=True
        )

    async def _run_single_evaluation(self, query: str, response: str, context: str) -> FinalEvaluation:
        opinions = []
        for aspect, guideline in self.CRITERIA.items():
            opinion = await self._get_grader_opinion(aspect, guideline, query, response, context)
            opinions.append(opinion)

        # --- TASK-EVAL-003: Hard Rule Guard (RAG Integrity) ---
        assertion_result = rag_assertion_grader.check(query, response, context)
        if not assertion_result.is_clean:
            for opinion in opinions:
                penalty = assertion_result.get_penalty_for_aspect(opinion.aspect)
                if penalty is not None and opinion.score > penalty:
                    violation = next(
                        (v for v in assertion_result.violations
                         if (v.rule_id == "CITE-001" and opinion.aspect == "citation_accuracy")
                         or (v.rule_id == "CITE-002" and opinion.aspect == "accuracy")),
                        None,
                    )
                    if violation:
                        opinion.score = penalty
                        opinion.reasoning += f" | [HARD RULE {violation.rule_id}] {violation.description}"

        avg_score = sum(o.score for o in opinions) / len(opinions)

        verdict = "PASS"
        if avg_score < 0.5:
            verdict = "FAIL"
        elif avg_score > 0.9:
            verdict = "EXCELLENT"

        return FinalEvaluation(
            composite_score=round(avg_score, 2),
            opinions=opinions,
            verdict=verdict,
            summary=f"Evaluation completed with average score {avg_score:.2f}.",
        )

    async def _get_grader_opinion(
        self, aspect: str, guideline: str, query: str, response: str, context: str
    ) -> GraderOpinion:
        prompt = (
            f"You are a specialized Quality Grader for an AI system.\n"
            f"Aspect to grade: {aspect}\n"
            f"Guideline: {guideline}\n\n"
            f"User Query: {query}\n"
            f"AI Response: {response}\n"
            f"Reference Context: {context}\n\n"
            f"Return a JSON object with 'score' (0-1), 'reasoning', and 'suggestions' (list)."
        )

        try:
            res_raw = await self.llm.chat_complete(
                [{"role": "user", "content": prompt}], temperature=0.0, json_mode=True
            )
            import json

            data = json.loads(res_raw)
            return GraderOpinion(aspect=aspect, **data)
        except Exception as e:
            logger.error(f"Grader failed for {aspect}: {e}")
            return GraderOpinion(aspect=aspect, score=0.5, reasoning=f"Grader error: {e!s}", suggestions=[])
