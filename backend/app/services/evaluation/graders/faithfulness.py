"""
FaithfulnessGrader — 忠实度评估器

评估方法 (RAGAS 标准):
  1. 将 AI 回答拆分为独立声明 (claims)
  2. 逐一验证每个声明是否有上下文支撑
  3. 计算有支撑声明的比例

这比"一次性打分"精确得多，因为它强制 LLM 逐句审查。
"""

from .base import BaseGrader


class FaithfulnessGrader(BaseGrader):
    dimension = "faithfulness"

    def _build_prompt(
        self,
        question: str,
        answer: str,
        ground_truth: str,
        contexts: list[str],
    ) -> str:
        context_text = "\n---\n".join(contexts[:5]) if contexts else "(no context provided)"

        return f"""You are a Faithfulness Evaluator. Your job is to determine whether the AI answer is supported by the provided context.

## Task
1. Break the AI answer into individual factual claims (statements).
2. For EACH claim, determine if it can be inferred from the context.
3. Calculate the faithfulness score = (supported claims) / (total claims).

## Input
**Question**: {question}

**Context (Retrieved Documents)**:
{context_text}

**AI Answer**:
{answer}

## Instructions
- A claim is "supported" if the context contains information that directly or indirectly supports it.
- A claim is "unsupported" if it introduces information NOT present in the context (hallucination).
- Be strict: vague or partially supported claims should be marked as unsupported.

## Output (JSON only)
{{
  "claims": [
    {{"claim": "...", "supported": true, "evidence": "brief quote from context"}},
    {{"claim": "...", "supported": false, "evidence": "not found in context"}}
  ],
  "supported_count": 0,
  "total_count": 0,
  "score": 0.0,
  "reasoning": "Overall assessment of faithfulness"
}}"""

    def _parse_response(self, response: str) -> tuple[float, str]:
        """自定义解析: 从 claims 列表计算分数"""
        import json

        try:
            data = json.loads(response)

            # 优先使用 claims 列表计算
            claims = data.get("claims", [])
            if claims:
                supported = sum(1 for c in claims if c.get("supported", False))
                total = len(claims)
                score = supported / total if total > 0 else 0.0
            else:
                score = float(data.get("score", 0.0))

            score = max(0.0, min(1.0, score))
            reasoning = data.get("reasoning", "")

            return score, reasoning
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            return 0.0, f"Parse error: {e}"
