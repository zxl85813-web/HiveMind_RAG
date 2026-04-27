
import json
from .base import BaseGrader

class InstructionFollowingGrader(BaseGrader):
    """
    指令遵循度评测器: 检查 AI 是否遵循了特定的格式、风格或约束要求。
    """
    dimension = "instruction_following"

    def _build_prompt(
        self,
        question: str,
        answer: str,
        ground_truth: str,
        contexts: list[str],
    ) -> str:
        return f"""You are an Instruction Following Evaluator. Your goal is to check if the AI answer followed the specific constraints provided in the query or the system prompt.

## Task
1. Identify all explicit and implicit instructions in the question (e.g., "format as JSON", "use bullet points", "be concise", "mention [X]").
2. Check if the AI answer followed each of these instructions.
3. Calculate the compliance score.

## Input
**Question**: {question}

**AI Answer**:
{answer}

## Output (JSON only)
{{
  "instructions": [
    {{"instruction": "...", "followed": true, "comment": "..."}},
    {{"instruction": "...", "followed": false, "comment": "..."}}
  ],
  "score": 0.0,
  "reasoning": "Overall summary of instruction following."
}}"""

    def _parse_response(self, response: str) -> tuple[float, str]:
        try:
            data = json.loads(response)
            instructions = data.get("instructions", [])
            if instructions:
                followed = sum(1 for i in instructions if i.get("followed", False))
                score = followed / len(instructions) if instructions else 1.0
            else:
                score = float(data.get("score", 0.0))
            
            return score, data.get("reasoning", "")
        except Exception as e:
            return 0.0, f"Parse error: {e}"
