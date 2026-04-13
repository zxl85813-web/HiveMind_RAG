"""
RelevanceGrader — 答案相关性评估器

评估方法 (RAGAS 标准):
  1. 从 AI 回答逆向生成 N 个可能的问题
  2. 计算逆向问题与原始问题的语义相似度
  3. 高相似度 = 回答高度相关

这比直接问"回答是否相关"更客观，因为它通过逆向验证消除主观偏差。
"""

from .base import BaseGrader


class RelevanceGrader(BaseGrader):
    dimension = "answer_relevance"

    def _build_prompt(
        self,
        question: str,
        answer: str,
        ground_truth: str,
        contexts: list[str],
    ) -> str:
        return f"""You are an Answer Relevance Evaluator. Your job is to determine whether the AI answer directly addresses the user's question.

## Task
1. Read the original question carefully.
2. Read the AI answer.
3. Generate 3 questions that the AI answer would be a good response to.
4. Compare these generated questions with the original question.
5. Score how well the answer addresses the original question.

## Input
**Original Question**: {question}

**AI Answer**:
{answer}

## Scoring Guide
- 1.0: The answer directly and completely addresses the question
- 0.7-0.9: The answer mostly addresses the question with minor tangents
- 0.4-0.6: The answer partially addresses the question but includes significant irrelevant content
- 0.1-0.3: The answer barely relates to the question
- 0.0: The answer is completely unrelated to the question

## Output (JSON only)
{{
  "generated_questions": [
    "Question 1 that this answer would address",
    "Question 2 that this answer would address",
    "Question 3 that this answer would address"
  ],
  "similarity_analysis": "How similar are the generated questions to the original?",
  "score": 0.0,
  "reasoning": "Why this score was given"
}}"""
