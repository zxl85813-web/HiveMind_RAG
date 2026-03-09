"""
Knowledge Overlap Engine — Detects if document content is already known by the LLM.
Uses Knowledge Probing/Closed-Book Testing (M2.3.6).
"""

# ruff: noqa: W293

import json
from typing import Any

from loguru import logger
from pydantic import BaseModel

from app.agents.llm_router import LLMRouter, ModelTier


class ProbeQA(BaseModel):
    question: str
    fact: str


class OverlapResult(BaseModel):
    overlap_score: float  # 0.0 to 1.0
    probes: list[dict[str, Any]]
    is_known: bool


class KnowledgeOverlapEngine:
    """Evaluates the incremental value of a document (private vs public knowledge)."""

    @staticmethod
    async def check_overlap(text: str, max_probes: int = 5) -> OverlapResult:
        """
        Performs closed-book testing to see if LLM already knows the content.
        """
        router = LLMRouter()
        fast_model = router.get_model(ModelTier.FAST)
        balanced_model = router.get_model(ModelTier.BALANCED)

        # 1. Generate Probes (Questions + Facts)
        # We need specific facts that can be tested.
        logger.info("🧪 Generating probes for knowledge overlap check...")

        prompt_gen = f"""
        Extract {max_probes} unique, specific factual claims from the following text.
        For each claim, generate a direct question and the corresponding answer (fact) found in the text.
        The questions should be answerable ONLY if someone has read the text or already knows the topic.
        
        Format as JSON list:
        [{{"question": "...", "fact": "..."}}]
        
        Text:
        {text[:2000]}
        """

        try:
            res = await fast_model.ainvoke(prompt_gen)
            # Basic JSON extraction (robust enough for most models)
            content = res.content
            start_idx = content.find("[")
            end_idx = content.rfind("]") + 1
            probes_data = json.loads(content[start_idx:end_idx])
            probes = [ProbeQA(**p) for p in probes_data]
        except Exception as e:
            logger.error(f"Failed to generate probes: {e}")
            return OverlapResult(overlap_score=0.0, probes=[], is_known=False)

        if not probes:
            return OverlapResult(overlap_score=0.0, probes=[], is_known=False)

        # 2. Closed-Book Test (Answer without context)
        # Ask a DIFFERENT model or same model in a new session without context.
        logger.info(f"🧪 Running closed-book test on {len(probes)} probes...")
        correct_count = 0
        results = []

        for p in probes:
            # We use a clean prompt to ensure no leakage
            prompt_test = (
                "Answer the following question briefly based on your general knowledge. "
                "If you don't know, say 'I don't know'.\n"
                f"Question: {p.question}"
            )
            res_test = await balanced_model.ainvoke(prompt_test)
            llm_answer = res_test.content

            # 3. Verify correctness using LLM as a judge
            prompt_verify = f"""
            Compare the 'Fact' with the 'LLM Answer'.
            Determine if the LLM Answer is essentially correct and matches the Fact.
            Fact: {p.fact}
            LLM Answer: {llm_answer}
            
            Return ONLY "YES" or "NO".
            """
            res_verify = await fast_model.ainvoke(prompt_verify)
            is_correct = "YES" in res_verify.content.upper()

            if is_correct:
                correct_count += 1

            results.append({"question": p.question, "fact": p.fact, "llm_answer": llm_answer, "is_correct": is_correct})

        overlap_score = correct_count / len(probes)
        is_known = overlap_score >= 0.7  # Heuristic threshold

        logger.info(f"🧪 Overlap Score: {overlap_score:.2f} (Known: {is_known})")

        return OverlapResult(overlap_score=overlap_score, probes=results, is_known=is_known)
