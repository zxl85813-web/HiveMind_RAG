"""
CorrectnessGrader — 答案正确性评估器

评估方法:
  1. 从 Ground Truth 提取关键事实点
  2. 逐一检查 AI 回答是否包含这些事实
  3. 检查 AI 回答是否引入了与 GT 矛盾的错误事实
  4. 综合计算正确性分数

这比简单的"语义相似度"更精确，因为它关注事实层面的对错。
"""

from .base import BaseGrader


class CorrectnessGrader(BaseGrader):
    dimension = "answer_correctness"

    def _build_prompt(
        self,
        question: str,
        answer: str,
        ground_truth: str,
        contexts: list[str],
    ) -> str:
        return f"""You are an Answer Correctness Evaluator. Your job is to determine whether the AI answer is factually correct compared to the ground truth.

## Task
1. Extract key factual claims from the Ground Truth (GT).
2. For each GT fact, check if the AI answer includes it (True Positive), misses it (False Negative), or contradicts it (Error).
3. Check if the AI answer introduces facts NOT in the GT (may be acceptable if correct, penalize if wrong).
4. Calculate correctness score.

## Input
**Question**: {question}

**Ground Truth (Reference Answer)**:
{ground_truth}

**AI Answer**:
{answer}

## Scoring Formula
- TP (True Positives): GT facts correctly present in AI answer
- FN (False Negatives): GT facts missing from AI answer
- FP (False Positives): AI facts that contradict GT
- Score = TP / (TP + FN + FP)

## Output (JSON only)
{{
  "gt_facts": [
    {{"fact": "...", "status": "TP|FN|FP", "note": "brief explanation"}}
  ],
  "extra_ai_facts": [
    {{"fact": "...", "correct": true, "note": "..."}}
  ],
  "tp_count": 0,
  "fn_count": 0,
  "fp_count": 0,
  "score": 0.0,
  "reasoning": "Overall correctness assessment"
}}"""

    def _parse_response(self, response: str) -> tuple[float, str]:
        """自定义解析: 从事实对比列表计算分数"""
        import json

        try:
            data = json.loads(response)

            gt_facts = data.get("gt_facts", [])
            if gt_facts:
                tp = sum(1 for f in gt_facts if f.get("status") == "TP")
                fn = sum(1 for f in gt_facts if f.get("status") == "FN")
                fp = sum(1 for f in gt_facts if f.get("status") == "FP")

                # 额外的错误 AI 事实也算 FP
                extra = data.get("extra_ai_facts", [])
                fp += sum(1 for f in extra if not f.get("correct", True))

                denominator = tp + fn + fp
                score = tp / denominator if denominator > 0 else 0.0
            else:
                score = float(data.get("score", 0.0))

            score = max(0.0, min(1.0, score))
            reasoning = data.get("reasoning", "")

            return score, reasoning
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            return 0.0, f"Parse error: {e}"
