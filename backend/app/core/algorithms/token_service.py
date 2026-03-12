"""
统一分词与计费基座 (Tokenization Service)
为整个系统的文本长短感知提供标准尺子和统一裁剪工具，支持 tiktoken 计量和安全截断。
"""

import tiktoken
from loguru import logger


class TokenService:
    """Tokenization and budgeting service."""

    @staticmethod
    def count_tokens(text: str, model: str = "gpt-4o") -> int:
        """Calculate the number of tokens in the given text for a specific model."""
        if not text:
            return 0
        try:
            enc = tiktoken.encoding_for_model(model)
            return len(enc.encode(text))
        except KeyError:
            # Fallback to cl100k_base if model is unknown
            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception as e:
            logger.warning(f"Failed to count tokens: {e}")
            # Rough estimation: 1 token ~= 4 chars (English) or 1 char (Chinese)
            return len(text)

    @staticmethod
    def truncate_to_budget(text: str, budget: int, model: str = "gpt-4o") -> str:
        """Safely truncate text to a specified token budget."""
        if not text or budget <= 0:
            return ""

        try:
            enc = tiktoken.encoding_for_model(model)
        except KeyError:
            enc = tiktoken.get_encoding("cl100k_base")

        tokens = enc.encode(text)
        if len(tokens) <= budget:
            return text

        # Decode only up to the budget
        return enc.decode(tokens[:budget])


# Global instance
token_service = TokenService()
