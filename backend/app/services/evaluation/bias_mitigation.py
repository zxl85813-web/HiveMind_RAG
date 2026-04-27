
import json
from typing import List, Dict, Any, Optional
from loguru import logger
from app.core.llm import get_llm_service

class BiasMitigationGrader:
    """
    Implements techniques to mitigate common LLM-as-Judge biases:
    1. Position Bias (A/B testing)
    2. Verbosity Bias (Preference for longer answers)
    3. Self-Correction (Reflection loop)
    """

    def __init__(self):
        self.llm = get_llm_service()

    async def ab_comparison(self, question: str, answer_a: str, answer_b: str, context: str = "") -> Dict[str, Any]:
        """
        Runs a shuffled A/B comparison to mitigate position bias.
        Candidate A and B are presented in both (A, B) and (B, A) orders.
        """
        # Run 1: Original Order
        res1 = await self._compare(question, answer_a, answer_b, context)
        
        # Run 2: Swapped Order
        res2 = await self._compare(question, answer_b, answer_a, context)
        
        # Logic: 
        # res1["winner"] is "A" or "B"
        # res2["winner"] is "A" or "B" (referring to the swapped positions)
        
        # Mapping back to actual candidates
        winner1 = "candidate_a" if res1["winner"] == "A" else "candidate_b"
        # In res2, Choice A is answer_b, Choice B is answer_a
        winner2 = "candidate_b" if res2["winner"] == "A" else "candidate_a"
        
        consensus = winner1 == winner2
        
        return {
            "winner": winner1 if consensus else "tie/inconsistent",
            "consistency": consensus,
            "run_1": res1,
            "run_2": res2,
            "bias_detected": not consensus
        }

    async def reflected_grade(self, grader_type: str, grader_logic, **kwargs) -> Dict[str, Any]:
        """
        Implements self-correction bias mitigation.
        1. Get initial grade.
        2. Ask the judge to critique its own grade for potential bias.
        3. Finalize grade.
        """
        # 1. Initial Grade
        initial_result = await grader_logic.grade(**kwargs)
        
        # 2. Reflection
        reflection_prompt = (
            f"You previously graded a RAG response for {grader_type} and gave a score of {initial_result.score}.\n"
            f"Reasoning: {initial_result.reasoning}\n\n"
            "Now, strictly review your own judgment for potential biases:\n"
            "1. Verbosity Bias: Did you favor the answer just because it was longer?\n"
            "2. Halo Effect: Did you ignore minor factual errors because the tone was confident?\n"
            "3. Grounding: Is the score truly reflecting the evidence in the context?\n\n"
            "If you find any bias, provide a corrected score. Otherwise, confirm the initial score.\n"
            "Respond in JSON: {'corrected_score': float, 'analysis': '...', 'changed': bool}"
        )
        
        try:
            resp = await self.llm.chat_complete([{"role": "user", "content": reflection_prompt}], json_mode=True)
            ref_data = json.loads(resp)
            
            final_score = ref_data["corrected_score"] if ref_data["changed"] else initial_result.score
            
            return {
                "initial_score": initial_result.score,
                "final_score": final_score,
                "reflection": ref_data["analysis"],
                "was_biased": ref_data["changed"]
            }
        except Exception as e:
            logger.error(f"Reflection loop failed: {e}")
            return {"initial_score": initial_result.score, "final_score": initial_result.score, "error": str(e)}

    async def _compare(self, question: str, choice_a: str, choice_b: str, context: str) -> Dict[str, Any]:
        prompt = (
            "You are a neutral judge. Compare two AI answers to the same question based on accuracy and helpfulness.\n"
            f"Context: {context}\n"
            f"Question: {question}\n\n"
            f"Answer A: {choice_a}\n\n"
            f"Answer B: {choice_b}\n\n"
            "Determine which answer is better (A or B), or if it's a TIE.\n"
            "Return JSON: {'winner': 'A'|'B'|'TIE', 'reasoning': '...'}"
        )
        try:
            resp = await self.llm.chat_complete([{"role": "user", "content": prompt}], json_mode=True)
            return json.loads(resp)
        except Exception as e:
            return {"winner": "TIE", "reasoning": f"Error: {e}"}
