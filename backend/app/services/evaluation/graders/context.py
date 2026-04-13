"""
ContextGraders — 上下文质量评估器

包含两个独立评估器:
  1. ContextPrecisionGrader: 检索结果中有多少是真正有用的？（信噪比）
  2. ContextRecallGrader: 回答所需的信息是否都被检索到了？（覆盖率）
"""

from .base import BaseGrader


class ContextPrecisionGrader(BaseGrader):
    """
    上下文精确度: 检索到的文档中，有多少是回答问题真正需要的？

    高精确度 = 检索结果干净，噪音少
    低精确度 = 检索了很多无关文档，浪费 Token
    """

    dimension = "context_precision"

    def _build_prompt(
        self,
        question: str,
        answer: str,
        ground_truth: str,
        contexts: list[str],
    ) -> str:
        context_blocks = ""
        for i, ctx in enumerate(contexts[:10], 1):
            snippet = ctx[:500]
            context_blocks += f"\n[Document {i}]:\n{snippet}\n"

        return f"""You are a Context Precision Evaluator. Your job is to determine how many of the retrieved documents are actually relevant to answering the question.

## Task
1. Read the question.
2. For EACH retrieved document, determine if it contains information useful for answering the question.
3. Calculate precision = (relevant documents) / (total documents).

## Input
**Question**: {question}

**Retrieved Documents**:
{context_blocks}

## Instructions
- A document is "relevant" if it contains ANY information that helps answer the question.
- A document is "irrelevant" if it's off-topic or contains only tangentially related information.

## Output (JSON only)
{{
  "document_assessments": [
    {{"doc_id": 1, "relevant": true, "reason": "Contains info about..."}},
    {{"doc_id": 2, "relevant": false, "reason": "Off-topic, discusses..."}}
  ],
  "relevant_count": 0,
  "total_count": 0,
  "score": 0.0,
  "reasoning": "Overall context precision assessment"
}}"""

    def _parse_response(self, response: str) -> tuple[float, str]:
        import json

        try:
            data = json.loads(response)
            assessments = data.get("document_assessments", [])
            if assessments:
                relevant = sum(1 for a in assessments if a.get("relevant", False))
                total = len(assessments)
                score = relevant / total if total > 0 else 0.0
            else:
                score = float(data.get("score", 0.0))

            score = max(0.0, min(1.0, score))
            return score, data.get("reasoning", "")
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            return 0.0, f"Parse error: {e}"


class ContextRecallGrader(BaseGrader):
    """
    上下文召回率: 回答问题所需的关键信息是否都被检索到了？

    高召回率 = 所有必要信息都在上下文中
    低召回率 = 关键信息缺失，LLM 被迫猜测或遗漏
    """

    dimension = "context_recall"

    def _build_prompt(
        self,
        question: str,
        answer: str,
        ground_truth: str,
        contexts: list[str],
    ) -> str:
        context_text = "\n---\n".join(contexts[:5]) if contexts else "(no context)"

        return f"""You are a Context Recall Evaluator. Your job is to determine whether the retrieved context contains all the information needed to produce the ground truth answer.

## Task
1. Break the Ground Truth into key information points.
2. For EACH point, check if it can be found in the retrieved context.
3. Calculate recall = (found points) / (total points).

## Input
**Question**: {question}

**Ground Truth (Reference Answer)**:
{ground_truth}

**Retrieved Context**:
{context_text}

## Instructions
- An information point is "found" if the context contains equivalent information (exact match not required).
- An information point is "missing" if the context has no related information.

## Output (JSON only)
{{
  "gt_info_points": [
    {{"point": "...", "found_in_context": true, "evidence": "brief quote"}},
    {{"point": "...", "found_in_context": false, "evidence": "not found"}}
  ],
  "found_count": 0,
  "total_count": 0,
  "score": 0.0,
  "reasoning": "Overall context recall assessment"
}}"""

    def _parse_response(self, response: str) -> tuple[float, str]:
        import json

        try:
            data = json.loads(response)
            points = data.get("gt_info_points", [])
            if points:
                found = sum(1 for p in points if p.get("found_in_context", False))
                total = len(points)
                score = found / total if total > 0 else 0.0
            else:
                score = float(data.get("score", 0.0))

            score = max(0.0, min(1.0, score))
            return score, data.get("reasoning", "")
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            return 0.0, f"Parse error: {e}"
