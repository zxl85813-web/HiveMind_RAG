"""
LLM Token Tracker — Counts tokens and estimates API cost.

所属模块: llm
职责: LLM 调用的 Token 计量与成本估算，与 JWT 无关。
注册位置: REGISTRY.md > LLM > TokenTracker
"""
try:
    import tiktoken
except ImportError:
    tiktoken = None

from loguru import logger


class TokenTracker:
    """Utility for tracking LLM token usage and estimating costs."""

    @staticmethod
    def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
        """Count tokens accurately using tiktoken.

        Args:
            text: The text to count tokens for.
            model: The model name to use for encoding.

        Returns:
            The estimated token count.
        """
        if not text:
            return 0

        if tiktoken:
            try:
                try:
                    encoding = tiktoken.encoding_for_model(model)
                except KeyError:
                    # Fallback for unknown models (DeepSeek, Kimi, etc.)
                    encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
            except Exception as e:
                logger.warning(f"tiktoken counting failed: {e}")

        # Fallback: ~4 characters per token
        return len(text) // 4 + 1

    @staticmethod
    def calculate_cost(
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "gpt-3.5-turbo"
    ) -> float:
        """Estimate USD cost based on model pricing.

        Args:
            prompt_tokens: Number of input tokens.
            completion_tokens: Number of output tokens.
            model: The model name (used for pricing lookup).

        Returns:
            Estimated cost in USD.
        """
        # Standard pricing: prompt $0.0015/1k, completion $0.002/1k
        return (prompt_tokens * 0.0015 + completion_tokens * 0.002) / 1000


# Back-compat alias so existing imports still work during migration period
TokenService = TokenTracker
