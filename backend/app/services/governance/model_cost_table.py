"""Per-model token cost table (USD per 1M tokens, public list prices).

All values are stored as **USD micro-cents per 1K tokens** (1 USD = 1_000_000 micro)
to keep the accountant in integer arithmetic.

Sources (snapshot as of 2026-04):
- OpenAI: https://openai.com/api/pricing/
- Anthropic: https://www.anthropic.com/pricing
- DeepSeek: https://api-docs.deepseek.com/quick_start/pricing
- Moonshot Kimi: https://platform.moonshot.cn/docs/pricing
- Qwen / SiliconFlow / Volcengine Ark: 公开计费页快照

`UNKNOWN_*` constants are conservative fallbacks used when a model isn't in the
table — preferring to *over-charge* than to under-charge so budgets stay safe.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelPrice:
    """Per-1K-token price expressed in **USD micro-cents** (1 USD = 1_000_000)."""
    prompt_micro_per_1k: int
    completion_micro_per_1k: int

    @classmethod
    def from_usd_per_million(cls, prompt_usd_per_m: float, completion_usd_per_m: float) -> "ModelPrice":
        """Helper: $X / 1M tokens  -> micro-cents per 1K tokens."""
        # USD/M  -> USD/1K is /1000. Then *1_000_000 -> micro = same number.
        return cls(
            prompt_micro_per_1k=int(round(prompt_usd_per_m * 1000)),
            completion_micro_per_1k=int(round(completion_usd_per_m * 1000)),
        )


# Public price snapshot (USD per 1M tokens)
_PRICES_USD_PER_M: dict[str, tuple[float, float]] = {
    # ── OpenAI ──────────────────────────────────────────────
    "gpt-4o":            (5.00, 15.00),
    "gpt-4o-mini":       (0.15, 0.60),
    "gpt-4.1":           (2.00, 8.00),
    "gpt-4.1-mini":      (0.40, 1.60),
    "gpt-4.1-nano":      (0.10, 0.40),
    "o1":                (15.00, 60.00),
    "o1-mini":           (3.00, 12.00),
    "o3-mini":           (1.10, 4.40),

    # ── Anthropic ───────────────────────────────────────────
    "claude-3-5-sonnet": (3.00, 15.00),
    "claude-3-5-haiku":  (0.80, 4.00),
    "claude-3-opus":     (15.00, 75.00),
    "claude-3-7-sonnet": (3.00, 15.00),

    # ── DeepSeek ────────────────────────────────────────────
    "deepseek-chat":     (0.27, 1.10),
    "deepseek-v3":       (0.27, 1.10),
    "deepseek-r1":       (0.55, 2.19),
    "deepseek-ai/deepseek-v3": (0.27, 1.10),
    "deepseek-ai/deepseek-r1": (0.55, 2.19),

    # ── Moonshot Kimi ──────────────────────────────────────
    "moonshot-v1-8k":    (1.65, 1.65),    # ¥12 / M ~= $1.65
    "moonshot-v1-32k":   (3.30, 3.30),    # ¥24 / M
    "moonshot-v1-128k":  (8.25, 8.25),    # ¥60 / M
    "kimi-k1.5":         (1.65, 1.65),

    # ── Alibaba Qwen ───────────────────────────────────────
    "qwen-plus":         (0.55, 1.65),
    "qwen-max":          (3.30, 9.90),
    "qwen-turbo":        (0.30, 0.60),
    "qwen2.5-72b-instruct": (0.55, 1.65),

    # ── Google Gemini ───────────────────────────────────────
    "gemini-2.0-flash":  (0.10, 0.40),
    "gemini-1.5-pro":    (1.25, 5.00),
    "gemini-1.5-flash":  (0.075, 0.30),

    # ── Local / self-hosted (zero marginal cost) ────────────
    "local":             (0.0, 0.0),
    "ollama":            (0.0, 0.0),
}


def _build_table() -> dict[str, ModelPrice]:
    return {
        name.lower(): ModelPrice.from_usd_per_million(p, c)
        for name, (p, c) in _PRICES_USD_PER_M.items()
    }


_TABLE: dict[str, ModelPrice] = _build_table()

# Conservative fallback (≈ DeepSeek-V3 mid-tier) so unknown models still meter.
UNKNOWN_PRICE = ModelPrice.from_usd_per_million(0.50, 1.50)


def lookup_price(model: str | None) -> ModelPrice:
    """Find a price entry, matching by exact name then by prefix."""
    if not model:
        return UNKNOWN_PRICE
    key = model.lower().strip()
    if key in _TABLE:
        return _TABLE[key]
    # Prefix fallback — handles versioned names like 'gpt-4o-2024-08-06'.
    for name, price in _TABLE.items():
        if key.startswith(name):
            return price
    return UNKNOWN_PRICE


def register_price(model: str, prompt_usd_per_m: float, completion_usd_per_m: float) -> None:
    """Allow runtime registration (e.g. from settings or admin API)."""
    _TABLE[model.lower().strip()] = ModelPrice.from_usd_per_million(
        prompt_usd_per_m, completion_usd_per_m
    )


def known_models() -> list[str]:
    return sorted(_TABLE.keys())
