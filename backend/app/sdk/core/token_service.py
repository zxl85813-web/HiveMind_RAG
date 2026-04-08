"""
Centralized Token Management Service.
Handles token counting, budget enforcement, and context truncation.
"""

from typing import List, Union

import tiktoken
from langchain_core.messages import BaseMessage
from loguru import logger
from app.sdk.discovery.registry import register_component


@register_component(
    "TokenService", 
    category="CoreSDK", 
    description="Centralized token utility for budget enforcement and semantic truncation."
)
class TokenService:
    """
    Standardized token utility using tiktoken (cl100k_base).
    Used for ensuring prompts stay within model context windows (Harness Engineering).
    """

    _encoding = None

    @classmethod
    def get_encoding(cls, model_name: str = "gpt-4o"):
        """Cached access to the tiktoken encoding."""
        if cls._encoding is None:
            try:
                # Default to cl100k_base which is compatible with gpt-3.5-turbo, gpt-4, gpt-4o
                cls._encoding = tiktoken.encoding_for_model(model_name)
            except Exception as e:
                logger.warning(f"Failed to find encoding for {model_name}, falling back to cl100k_base: {e}")
                cls._encoding = tiktoken.get_encoding("cl100k_base")
        return cls._encoding

    @classmethod
    def count_tokens(cls, text: str, model_name: str = "gpt-4o") -> int:
        """Counts tokens for a given string."""
        if not text:
            return 0
        encoding = cls.get_encoding(model_name)
        return len(encoding.encode(text))

    @classmethod
    def count_message_tokens(cls, messages: List[BaseMessage], model_name: str = "gpt-4o") -> int:
        """
        Approximate token count for a list of messages.
        Note: Exact counting for ChatModels requires special padding (role name, etc.).
        This provides a safe lower-bound estimate.
        """
        total = 0
        for msg in messages:
            total += 4  # overhead for message structure
            total += cls.count_tokens(str(msg.content), model_name)
        total += 3  # overhead for system reply start
        return total

    @classmethod
    def truncate_to_budget(cls, text: str, budget: int, model_name: str = "gpt-4o") -> str:
        """
        Truncates content if it exceeds the token budget.
        Tries to truncate at newlines to maintain semantic readability.
        """
        if cls.count_tokens(text, model_name) <= budget:
            return text

        logger.info(f"📏 [TokenService] Truncating context to fit budget of {budget} tokens.")
        
        encoding = cls.get_encoding(model_name)
        tokens = encoding.encode(text)
        
        # Binary search for cutting point or just take first budget tokens
        truncated_tokens = tokens[:budget]
        raw_truncated_text = encoding.decode(truncated_tokens)
        
        # Refine: Cut at the last newline to avoid partial sentences
        last_newline = raw_truncated_text.rfind("\n")
        if last_newline != -1 and len(raw_truncated_text) - last_newline < 200:
            return raw_truncated_text[:last_newline] + "\n... [Truncated due to context budget] ..."
            
        return raw_truncated_text + "... [Truncated due to context budget] ..."

    @classmethod
    def calculate_budget_plan(cls, total_window: int | None = None) -> dict:
        """
        Returns standard budget allocation (P0 Hardening design).
        [Linked: REQ-014-P0_ARCHITECTURE_HARDENING]
        """
        from .config import settings
        
        limit = total_window or settings.CONTEXT_WINDOW_LIMIT
        return {
            "system_prompt": int(limit * settings.BUDGET_SYSTEM_RATIO),
            "memory": int(limit * settings.BUDGET_MEMORY_RATIO),
            "rag_context": int(limit * settings.BUDGET_RAG_RATIO),
            "history": int(limit * settings.BUDGET_HISTORY_RATIO),
            "output": int(limit * settings.BUDGET_OUTPUT_RATIO),
        }
