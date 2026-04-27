"""
BaseGrader — 评估器抽象基类

核心设计:
  1. 强制 CoT: 每个 Grader 必须先输出推理过程，再输出分数
  2. 多次采样: 支持 N 次独立评分取均值，计算置信度
  3. 硬规则兜底: 评分后经过 AssertionLayer 校验
"""

import json
import statistics
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field

from app.core.llm import get_llm_service


class GradeResult(BaseModel):
    """单维度评分结果"""

    dimension: str = Field(description="评估维度名称")
    score: float = Field(description="最终评分 0.0-1.0")
    confidence: str = Field(default="high", description="置信度: high / medium / low")
    std_dev: float = Field(default=0.0, description="多次采样的标准差")
    reasoning: str = Field(default="", description="评分理由 (CoT)")
    raw_scores: list[float] = Field(default_factory=list, description="原始采样分数")
    metadata: dict[str, Any] = Field(default_factory=dict, description="额外元数据")


class BaseGrader(ABC):
    """
    评估器抽象基类。

    子类必须实现:
      - dimension: 维度名称
      - _build_prompt(): 构建评估 Prompt
      - _parse_response(): 解析 LLM 返回
    """

    dimension: str = "base"
    n_samples: int = 1  # 默认单次采样，可在子类或调用时覆盖

    def __init__(self, n_samples: int | None = None):
        self.llm = get_llm_service()
        if n_samples is not None:
            self.n_samples = n_samples

    async def grade(
        self,
        question: str,
        answer: str,
        ground_truth: str = "",
        contexts: list[str] | None = None,
        n_samples: int | None = None,
    ) -> GradeResult:
        """
        执行评分。

        Args:
            question: 用户问题
            answer: AI 生成的回答
            ground_truth: 标准答案（可选）
            contexts: 检索到的上下文列表（可选）
            n_samples: 采样次数覆盖

        Returns:
            GradeResult 包含分数、置信度、推理过程
        """
        samples = n_samples or self.n_samples
        scores: list[float] = []
        reasonings: list[str] = []

        for i in range(samples):
            try:
                prompt = self._build_prompt(
                    question=question,
                    answer=answer,
                    ground_truth=ground_truth,
                    contexts=contexts or [],
                )
                resp = await self.llm.chat_complete(
                    [{"role": "user", "content": prompt}],
                    temperature=0.1,
                    json_mode=True,
                )
                score, reasoning = self._parse_response(resp)
                scores.append(score)
                reasonings.append(reasoning)
            except Exception as e:
                logger.warning(
                    f"[{self.dimension}] Sample {i + 1}/{samples} failed: {e}"
                )

        if not scores:
            return GradeResult(
                dimension=self.dimension,
                score=0.0,
                confidence="low",
                reasoning="All grading attempts failed",
            )

        # 计算统计量
        mean_score = statistics.mean(scores)
        std_dev = statistics.stdev(scores) if len(scores) > 1 else 0.0

        # 置信度判定
        if std_dev > 0.25:
            confidence = "low"
        elif std_dev > 0.1:
            confidence = "medium"
        else:
            confidence = "high"

        return GradeResult(
            dimension=self.dimension,
            score=round(mean_score, 3),
            confidence=confidence,
            std_dev=round(std_dev, 3),
            reasoning=reasonings[0] if reasonings else "",
            raw_scores=scores,
        )

    @abstractmethod
    def _build_prompt(
        self,
        question: str,
        answer: str,
        ground_truth: str,
        contexts: list[str],
    ) -> str:
        """构建评估 Prompt，子类必须实现"""
        ...

    def _parse_response(self, response: str) -> tuple[float, str]:
        """
        解析 LLM 返回的 JSON，提取 score 和 reasoning。
        子类可覆盖以自定义解析逻辑。
        """
        try:
            # Robust parsing: handle cases where LLM includes markdown code blocks
            clean_response = response.strip()
            if "```json" in clean_response:
                clean_response = clean_response.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_response:
                clean_response = clean_response.split("```")[1].split("```")[0].strip()
            
            data = json.loads(clean_response)
            score = float(data.get("score", 0.0))
            score = max(0.0, min(1.0, score))  # clamp
            reasoning = str(data.get("reasoning", ""))
            return score, reasoning
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning(f"[{self.dimension}] Failed to parse response: {e}")
            return 0.0, f"Parse error: {e}"
