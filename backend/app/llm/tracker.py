"""
LLM Token Tracker — Counts tokens and estimates API cost.

所属模块: llm
职责: LLM 调用的 Token 计量与成本估算，与 JWT 无关。
注册位置: REGISTRY.md > LLM > TokenTracker

v2.0 变更:
    - 加入 DeepSeek V4 / V3 / Flash 等模型的真实定价表
    - calculate_cost() 新增 cache_hit_tokens 参数，区分 cache hit / miss 费率
    - 新增 get_pricing() 工具方法，方便外部查询定价结构
"""

try:
    import tiktoken
except ImportError:
    tiktoken = None

from loguru import logger

# ---------------------------------------------------------------------------
# 模型定价表 (USD / 1M tokens)
# 格式: { model_key: (input_miss, input_hit, output) }
# input_hit 为 None 表示该模型/提供商不支持前缀缓存折扣
# ---------------------------------------------------------------------------
_PRICING: dict[str, tuple[float, float | None, float]] = {
    # ── DeepSeek V4 (官方 API) ──────────────────────────────────────────────
    "deepseek-v4-pro":                  (1.74,  0.145,  3.48),
    "deepseek-v4-flash":                (0.14,  0.028,  0.28),
    "deepseek-ai/deepseek-v4-pro":      (1.74,  0.145,  3.48),
    "deepseek-ai/deepseek-v4-flash":    (0.14,  0.028,  0.28),

    # ── DeepSeek V3 系列 (SiliconFlow / 官方) ───────────────────────────────
    "deepseek-v3":                      (0.27,  0.07,   1.10),
    "deepseek-ai/deepseek-v3":          (0.27,  0.07,   1.10),
    "deepseek-ai/deepseek-v3.2":        (0.27,  0.07,   1.10),
    "pro/deepseek-ai/deepseek-v3":      (0.27,  0.07,   1.10),

    # ── DeepSeek Reasoner ───────────────────────────────────────────────────
    "deepseek-reasoner":                (0.55,  0.14,   2.19),
    "deepseek-r1":                      (0.55,  0.14,   2.19),

    # ── Ark (火山引擎) DeepSeek V3 ──────────────────────────────────────────
    "deepseek-v3-2-251201":             (0.27,  0.07,   1.10),

    # ── GLM-5 (SiliconFlow) ─────────────────────────────────────────────────
    "pro/zai-org/glm-5":                (0.80,  None,   2.00),
    "glm-5":                            (0.80,  None,   2.00),

    # ── Kimi / Moonshot ─────────────────────────────────────────────────────
    "moonshot-v1-8k":                   (0.12,  None,   0.12),
    "moonshot-v1-32k":                  (0.24,  None,   0.24),
    "kimi-k2.5":                        (0.50,  None,   2.50),

    # ── OpenAI (备用) ────────────────────────────────────────────────────────
    "gpt-4o":                           (2.50,  1.25,   10.0),
    "gpt-4o-mini":                      (0.15,  0.075,  0.60),
    "gpt-3.5-turbo":                    (0.50,  None,   1.50),
    "gpt-4-turbo":                      (10.0,  None,   30.0),
}

# 默认兜底定价（未知模型）
_DEFAULT_PRICING: tuple[float, float | None, float] = (1.0, None, 2.0)


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
    def get_pricing(model: str) -> tuple[float, float | None, float]:
        """
        查询模型定价结构。

        Returns:
            (input_miss_per_1m, input_hit_per_1m_or_None, output_per_1m)
            input_hit 为 None 表示该模型不支持缓存折扣。
        """
        key = model.lower()
        if key in _PRICING:
            return _PRICING[key]
        # 模糊匹配：前缀命中
        for k, v in _PRICING.items():
            if key.startswith(k) or k.startswith(key):
                return v
        logger.debug(f"[TokenTracker] Unknown model pricing: {model!r}, using default")
        return _DEFAULT_PRICING

    @staticmethod
    def calculate_cost(
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "gpt-3.5-turbo",
        cache_hit_tokens: int = 0,
    ) -> float:
        """
        Estimate USD cost based on model pricing.

        Args:
            prompt_tokens:     Total input tokens (包含 cache_hit_tokens).
            completion_tokens: Output tokens.
            model:             Model name (used for pricing lookup).
            cache_hit_tokens:  Subset of prompt_tokens that were served from
                               prefix cache (billed at the cheaper hit rate).
                               Defaults to 0 (全部按 cache miss 计费).

        Returns:
            Estimated cost in USD.

        Example (DeepSeek V4-Pro, 10k input with 8k cache hit, 500 output):
            calculate_cost(10000, 500, "deepseek-v4-pro", cache_hit_tokens=8000)
            → (2000 * 1.74 + 8000 * 0.145 + 500 * 3.48) / 1_000_000
            → $0.00348 + $0.00116 + $0.00174 = $0.00638
        """
        input_miss_rate, input_hit_rate, output_rate = TokenTracker.get_pricing(model)

        # cache_hit_tokens 不能超过 prompt_tokens
        cache_hit_tokens = min(cache_hit_tokens, prompt_tokens)
        cache_miss_tokens = prompt_tokens - cache_hit_tokens

        # 如果该模型不支持缓存折扣，全部按 miss 计费
        effective_hit_rate = input_hit_rate if input_hit_rate is not None else input_miss_rate

        cost = (
            cache_miss_tokens * input_miss_rate
            + cache_hit_tokens * effective_hit_rate
            + completion_tokens * output_rate
        ) / 1_000_000

        return round(cost, 8)

    @staticmethod
    def estimate_cache_savings(
        prompt_tokens: int,
        cache_hit_tokens: int,
        model: str,
    ) -> float:
        """
        计算因缓存命中节省的费用（相比全部 cache miss 的差值）。

        Args:
            prompt_tokens:    总输入 token 数。
            cache_hit_tokens: 命中缓存的 token 数。
            model:            模型名称。

        Returns:
            节省的 USD 金额（正数）。
        """
        input_miss_rate, input_hit_rate, _ = TokenTracker.get_pricing(model)
        if input_hit_rate is None:
            return 0.0
        savings = cache_hit_tokens * (input_miss_rate - input_hit_rate) / 1_000_000
        return round(savings, 8)


# Back-compat alias so existing imports still work during migration period
TokenService = TokenTracker
