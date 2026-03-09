"""
Multi-LLM Router — intelligent model selection, cost optimization, and failover.

Routes requests based on task complexity (Model Tiering):
- REASONING (High Cost): Complex analysis, planning, multi-step deduction (e.g. o1, deepseek-r1)
- BALANCED (Mid Cost): Default agent logic, robust tool use (e.g. gpt-4o, deepseek-v3)
- FAST (Low Cost): Summarization, entity extraction, simple routing (e.g. gpt-4o-mini, qwen-plus)

Concept: Cost-Aware Swarm Orchestration.
High-end reasoning is only invoked for ambiguous or high-stakes reasoning phases.
"""

from enum import StrEnum

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from loguru import logger

from app.core.config import settings


class ModelTier(StrEnum):
    """Classification of models by capability and cost."""

    FAST = "fast"  # Simple reasoning, extremely cheap
    BALANCED = "balanced"  # Standard agent tool use & logic
    REASONING = "reasoning"  # Complex planning & error correction


class LLMRouter:
    """
    Orchestrates multiple LLM instances to balance quality and cost.
    Ensures that "simple tasks" use "cheap models" (FAST tier).
    """

    def __init__(self) -> None:
        self._instances: dict[ModelTier, BaseChatModel] = {}
        self._setup_default_routes()
        logger.info("🔀 LLMRouter initialized with cost-optimization tiers")

    def _setup_default_routes(self) -> None:
        """Initialize default models for each tier from settings. Supports per-tier providers."""
        try:
            # Determine provider overrides or use global fallback
            global_provider = settings.LLM_PROVIDER
            logger.debug(f"LLM Routing: Global Provider={global_provider}")

            # --- Reasoning Tier ---
            r_provider = settings.REASONING_PROVIDER or global_provider
            try:
                self._instances[ModelTier.REASONING] = self._create_llm(
                    model=settings.DEFAULT_REASONING_MODEL, provider=r_provider, temperature=0.6
                )
                logger.debug(f"✅ Loaded REASONING tier: {settings.DEFAULT_REASONING_MODEL} via {r_provider}")
            except Exception as e:
                logger.error(f"❌ Failed to load REASONING tier: {e}")

            # --- Balanced Tier ---
            b_provider = settings.BALANCED_PROVIDER or global_provider
            try:
                self._instances[ModelTier.BALANCED] = self._create_llm(
                    model=settings.LLM_MODEL, provider=b_provider, temperature=0.7
                )
                logger.debug(f"✅ Loaded BALANCED tier: {settings.LLM_MODEL} via {b_provider}")
            except Exception as e:
                logger.error(f"❌ Failed to load BALANCED tier: {e}")

            # --- Fast Tier ---
            f_provider = settings.FAST_PROVIDER or global_provider
            try:
                self._instances[ModelTier.FAST] = self._create_llm(
                    model=settings.DEFAULT_CHAT_MODEL, provider=f_provider, temperature=0.3
                )
                logger.debug(f"✅ Loaded FAST tier: {settings.DEFAULT_CHAT_MODEL} via {f_provider}")
            except Exception as e:
                logger.error(f"❌ Failed to load FAST tier: {e}")

            if not self._instances:
                raise RuntimeError("No LLM tiers could be initialized. Check your .env credentials.")

        except Exception as e:
            logger.error(f"Critical failure in LLMRouter setup: {e}")

    def _create_llm(self, model: str, provider: str, temperature: float = 0.7) -> BaseChatModel:
        """Internal factory for LangChain model instances."""
        # Standardize provider name
        p = provider.lower()

        # Prepare configuration
        config = {
            "model": model,
            "temperature": temperature,
        }

        # Inject provider-specific credentials from settings
        if p == "siliconflow":
            config["api_key"] = settings.LLM_API_KEY
            config["base_url"] = settings.LLM_BASE_URL
        elif p in ["moonshot", "kimi"]:
            config["api_key"] = settings.KIMI_API_KEY
            config["base_url"] = settings.KIMI_API_BASE  # Using the fixed setting name
        elif p == "openai":
            config["api_key"] = settings.OPENAI_API_KEY
            config["base_url"] = settings.OPENAI_BASE_URL
        elif p == "deepseek":
            config["api_key"] = settings.DEEPSEEK_API_KEY
            config["base_url"] = settings.DEEPSEEK_BASE_URL
        else:
            # Generic fallback
            config["api_key"] = settings.LLM_API_KEY or settings.OPENAI_API_KEY
            config["base_url"] = settings.LLM_BASE_URL or settings.OPENAI_BASE_URL

        if not config.get("api_key"):
            raise ValueError(f"Missing API Key for provider '{p}'")

        return ChatOpenAI(**config)

    def get_model(self, tier: ModelTier = ModelTier.BALANCED) -> BaseChatModel:
        """Get the chat model instance for the requested tier."""
        # Direct hit
        if tier in self._instances:
            return self._instances[tier]

        # Failover to BALANCED
        if ModelTier.BALANCED in self._instances:
            return self._instances[ModelTier.BALANCED]

        # Absolute fallback to first available
        if self._instances:
            return next(iter(self._instances.values()))

        raise RuntimeError("No LLM instances available in router.")

    def list_tiers(self) -> dict[str, str]:
        """Expose current routing map for UI or logging."""
        return {
            tier.value: str(getattr(inst, "model", getattr(inst, "model_name", "unknown")))
            for tier, inst in self._instances.items()
        }
