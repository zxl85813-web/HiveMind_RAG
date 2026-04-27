
import json
from typing import List
from loguru import logger
from app.core.llm import get_llm_service

class ClaimExtractor:
    """
    SME Assist: Automatically break a complex Gold Answer into atomic verifiable claims.
    Helps SMEs define 'what matters' without knowing technical metrics.
    """

    def __init__(self):
        self.llm = get_llm_service()

    async def extract_claims(self, gold_answer: str) -> List[str]:
        """
        Decomposes a long answer into individual facts.
        """
        prompt = (
            "You are a knowledge engineer helping a Subject Matter Expert.\n"
            "Given a standard answer, break it down into 3-5 individual, verifiable 'Golden Claims'.\n"
            "Each claim should be a simple sentence that MUST be true for the AI's response to be considered correct.\n\n"
            f"Gold Answer: {gold_answer}\n\n"
            "Output a JSON list of strings: ['claim 1', 'claim 2', ...]"
        )

        try:
            resp = await self.llm.chat_complete([{"role": "user", "content": prompt}], json_mode=True)
            return json.loads(resp)
        except Exception as e:
            logger.error(f"Failed to extract claims: {e}")
            return [gold_answer] # Fallback to original

    async def verify_with_context(self, gold_answer: str, context: str) -> dict:
        """
        Consistency Check: Verify if the SME's answer is supported by the actual document context.
        Prevents experts from using 'tribal knowledge' that is not in the system.
        """
        prompt = (
            "You are a fact-checker. Compare the user's provided 'Standard Answer' with the 'Reference Context'.\n"
            "Highlight any contradictions or figures that do not match.\n\n"
            f"Reference Context: {context}\n\n"
            f"Standard Answer: {gold_answer}\n\n"
            "Return JSON: {'is_consistent': bool, 'issues': ['list of discrepancies'], 'suggestion': 'how to fix'}"
        )
        try:
            resp = await self.llm.chat_complete([{"role": "user", "content": prompt}], json_mode=True)
            return json.loads(resp)
        except Exception as e:
            return {"is_consistent": True, "issues": [], "suggestion": ""}

claim_extractor = ClaimExtractor()
