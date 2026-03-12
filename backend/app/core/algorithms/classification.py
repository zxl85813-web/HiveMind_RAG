"""
通用推断引擎 (Classification Engine)
集成 Pydantic + jxnl/instructor 的超可靠分类器 (推荐选型)，
同时也支持级联降级 (规则 -> 向量 -> LLM) 提升性能与成本控制。
"""

from enum import Enum
from typing import TypeVar, Any

import instructor
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.llm import get_llm_service


T = TypeVar("T", bound=Enum)
M = TypeVar("M", bound=BaseModel)


class ClassifierService:
    """Unified classification service for intents, entities, and routing decisions."""

    @property
    def _client(self):
        # Dynamically fetch the client and wrap it with instructor
        # We do this as a property to allow test mocking or deferred init
        llm = get_llm_service()
        # Note: Instructor hooks into AsyncOpenAI client directly
        return instructor.from_openai(llm.client)

    async def classify_enum(
        self, text: str, target_enum: type[T], fallback: T | None = None, instruction: str = "Classify the following text:"
    ) -> tuple[T, float]:
        """
        Classify text into one of the target_enum values using Instructor.
        Returns the enum value and confidence score (defaulting to 1.0 for now, as logprobs might not always be available).
        """
        logger.debug(f"Classifying '{text[0:20]}...' against {target_enum.__name__}")  # type: ignore
        
        # Create a dynamic Pydantic model to enforce enum output
        class EnumExtractionModel(BaseModel):
            label: target_enum = Field(..., description="The highly matching category based on context.")

        try:
            resp: EnumExtractionModel = await self._client.chat.completions.create(
                model=settings.LLM_MODEL,
                response_model=EnumExtractionModel,
                messages=[
                    {"role": "system", "content": instruction},
                    {"role": "user", "content": text},
                ],
                temperature=0.0, # Greedy decoding for classification
                max_retries=2
            )
            return resp.label, 1.0
        except Exception as e:
            logger.warning(f"Failed to classify using LLM: {e}")
            return fallback or list(target_enum.__members__.values())[0], 0.0  # type: ignore

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
                max_retries=2
            )
            return resp
        except Exception as e:
            logger.error(f"Instructor extraction failed for {target_model.__name__}: {e}")
            raise e


# Global instance
classifier_service = ClassifierService()
