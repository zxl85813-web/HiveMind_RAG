"""
通用推断引擎 (Classification Engine)
集成 Pydantic + jxnl/instructor 的超可靠分类器 (推荐选型)，
同时支持级联降级 (规则 -> 向量 -> LLM) 提升性能与成本控制：

  Tier 0 — Rule-based:  O(n) 关键词/正则匹配，纳秒级，确定性最强。
  Tier 1 — Vector-based: 余弦相似度 Embedding 分类，毫秒级，无需 LLM。
  Tier 2 — LLM-based:   instructor + Pydantic 结构化推断，最强但最慢。

5.3 核心算法库重构 — classify_cascade() 实现三层降级。
"""

import math
import re
from enum import Enum
from typing import Literal, TypeVar

import instructor
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.llm import get_llm_service

T = TypeVar("T", bound=Enum)
M = TypeVar("M", bound=BaseModel)

# Confidence threshold: if vector similarity hits this we skip LLM.
_VECTOR_CONFIDENCE_THRESHOLD: float = 0.65


def _cosine(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    return dot / (n1 * n2) if n1 and n2 else 0.0


class ClassifierService:
    """Unified classification service for intents, entities, and routing decisions."""

    @property
    def _client(self):
        # Dynamically fetch the client and wrap it with instructor.
        # Property allows test mocking / deferred init.
        llm = get_llm_service()
        return instructor.from_openai(llm.client)

    # ── Three-tier cascade (5.3) ──────────────────────────────────────────────

    async def classify_cascade(
        self,
        text: str,
        categories: dict[str, str],
        default: str | None = None,
        vector_threshold: float = _VECTOR_CONFIDENCE_THRESHOLD,
    ) -> tuple[str, float, Literal["rule", "vector", "llm", "default"]]:
        """
        Cascade classification: rule → vector → LLM.

        Parameters
        ----------
        text:
            The input text to classify.
        categories:
            Mapping of ``{label: hint}`` where ``hint`` is a comma-separated list
            of representative keywords/phrases for that label (used for rule and
            vector tiers).  Example::

                {"rag": "搜索,查找,文档问答", "code": "代码,调试,Python"}

        default:
            Fallback label if all tiers fail.
        vector_threshold:
            Minimum cosine similarity required to accept the vector tier result.

        Returns
        -------
        (label, confidence, tier_used)
        """
        text_lower = text.lower()

        # ── Tier 0: Rule-based (keyword matching) ──────────────────────────
        for label, hints in categories.items():
            keywords = [k.strip().lower() for k in re.split(r"[,，;；]", hints) if k.strip()]
            if any(kw in text_lower for kw in keywords):
                logger.debug(f"[Classify T0-Rule] '{label}' matched keyword in '{text[:40]}'")
                return label, 1.0, "rule"

        # ── Tier 1: Vector-based (embedding cosine similarity) ─────────────
        try:
            from app.core.embeddings import get_embedding_service

            emb_service = get_embedding_service()
            text_vec = emb_service.embed_query(text)

            best_label = default or next(iter(categories))
            best_score = -1.0

            for label, hints in categories.items():
                hint_vec = emb_service.embed_query(hints)
                score = _cosine(text_vec, hint_vec)
                if score > best_score:
                    best_score = score
                    best_label = label

            if best_score >= vector_threshold:
                logger.debug(f"[Classify T1-Vec] '{best_label}' score={best_score:.3f}")
                return best_label, best_score, "vector"

            logger.debug(f"[Classify T1-Vec] Best score {best_score:.3f} below threshold — escalating to LLM")

        except Exception as e:
            logger.warning(f"[Classify T1-Vec] Embedding failed: {e} — falling back to LLM")

        # ── Tier 2: LLM-based (instructor + Pydantic) ──────────────────────
        try:
            label_list = list(categories.keys())
            description = "\n".join(f"- {lbl}: {hint}" for lbl, hint in categories.items())

            class _LabelModel(BaseModel):
                label: str = Field(..., description=f"Must be one of: {label_list}")

            resp: _LabelModel = await self._client.chat.completions.create(
                model=settings.LLM_MODEL,
                response_model=_LabelModel,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Classify the user input into EXACTLY one of the listed categories.\n"
                            f"Categories:\n{description}"
                        ),
                    },
                    {"role": "user", "content": text},
                ],
                temperature=0.0,
                max_retries=2,
            )
            label_out = resp.label if resp.label in label_list else (default or label_list[0])
            logger.debug(f"[Classify T2-LLM] '{label_out}'")
            return label_out, 1.0, "llm"

        except Exception as e:
            logger.error(f"[Classify T2-LLM] Failed: {e}")
            fallback = default or (next(iter(categories)) if categories else "unknown")
            return fallback, 0.0, "default"

    # ── Original typed-enum helper (unchanged) ────────────────────────────────

    async def classify_enum(
        self, text: str, target_enum: type[T], fallback: T | None = None, instruction: str = "Classify the following text:"
    ) -> tuple[T, float]:
        """
        Classify text into one of the target_enum values using Instructor.
        Returns the enum value and confidence score.
        """
        logger.debug(f"Classifying '{text[0:20]}...' against {target_enum.__name__}")  # type: ignore

        class EnumExtractionModel(BaseModel):
            label: target_enum = Field(..., description="The highly matching category based on context.")  # type: ignore[valid-type]

        try:
            resp: EnumExtractionModel = await self._client.chat.completions.create(
                model=settings.LLM_MODEL,
                response_model=EnumExtractionModel,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": text},
                ],
                temperature=0.0,
                max_retries=2,
            )
            return resp.label, 1.0
        except Exception as e:
            logger.warning(f"Failed to classify using LLM: {e}")
            return fallback or next(iter(target_enum.__members__.values())), 0.0  # type: ignore

    async def extract_model(self, text: str, target_model: type[M], instruction: str = "Extract data matching the schema:") -> M:
        """
        Extract structured data matching the target Pydantic model using LLM and Instructor.
        """
        logger.debug(f"Extracting structure {target_model.__name__} from text")
        try:
            resp: M = await self._client.chat.completions.create(
                model=settings.LLM_MODEL,
                response_model=target_model,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": text},
                ],
                temperature=0.1,
                max_retries=2,
            )
            return resp
        except Exception as e:
            logger.error(f"Instructor extraction failed for {target_model.__name__}: {e}")
            raise


# Global instance
classifier_service = ClassifierService()
