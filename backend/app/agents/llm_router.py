"""
Multi-LLM Router — intelligent model selection, cost optimization, and failover.

Routes requests based on task complexity (Model Tiering):
- REASONING (High Cost): Complex analysis, planning, multi-step deduction (e.g. o1, deepseek-r1)
- BALANCED (Mid Cost): Default agent logic, robust tool use (e.g. gpt-4o, deepseek-v3)
- FAST (Low Cost): Summarization, entity extraction, simple routing (e.g. gpt-4o-mini, qwen-plus)

Concept: Cost-Aware Swarm Orchestration.
High-end reasoning is only invoked for ambiguous or high-stakes reasoning phases.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from loguru import logger
from pydantic import BaseModel

from app.core.config import settings


# Mapping of provider name -> secret key used by SecretManager.
# Per-tenant override of any of these will short-circuit the global env key.
_PROVIDER_SECRET_KEYS: Dict[str, str] = {
    "siliconflow": "llm.siliconflow.api_key",
    "moonshot": "llm.kimi.api_key",
    "kimi": "llm.kimi.api_key",
    "openai": "llm.openai.api_key",
    "deepseek": "llm.deepseek.api_key",
}


def provider_secret_key(provider: str) -> str:
    """Return the canonical SecretManager key for the given provider name."""
    return _PROVIDER_SECRET_KEYS.get(provider.lower(), "llm.default.api_key")


def all_provider_secret_keys() -> list[str]:
    """Stable list of every provider key — used to pre-warm the secret cache per request."""
    # Dedup while preserving order
    seen: dict[str, None] = {}
    for v in _PROVIDER_SECRET_KEYS.values():
        seen.setdefault(v, None)
    return list(seen.keys())


class ModelTier(str, Enum):
    """Classification of models by capability and cost."""
    FAST = "fast"            # Simple reasoning, extremely cheap
    BALANCED = "balanced"    # Standard agent tool use & logic
    REASONING = "reasoning"  # Complex planning & error correction


class LLMRouter:
    """
    Orchestrates multiple LLM instances to balance quality and cost.
    Ensures that "simple tasks" use "cheap models" (FAST tier).
    """

    def __init__(self) -> None:
        self._instances: Dict[ModelTier, BaseChatModel] = {}
        # Per-tier creation spec — replayed when building tenant-overridden instances.
        self._tier_specs: Dict[ModelTier, Tuple[str, str, float]] = {}
        # Cache of per-tenant LLM instances keyed by (tenant_id, tier).
        # Bounded by tenant_count * tier_count, no eviction needed in practice.
        self._tenant_instances: Dict[Tuple[str, ModelTier], BaseChatModel] = {}
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
            self._tier_specs[ModelTier.REASONING] = (settings.DEFAULT_REASONING_MODEL, r_provider, 0.6)
            try:
                self._instances[ModelTier.REASONING] = self._create_llm(
                    model=settings.DEFAULT_REASONING_MODEL,
                    provider=r_provider,
                    temperature=0.6
                )
                logger.debug(f"✅ Loaded REASONING tier: {settings.DEFAULT_REASONING_MODEL} via {r_provider}")
            except Exception as e:
                logger.error(f"❌ Failed to load REASONING tier: {e}")

            # --- Balanced Tier ---
            b_provider = settings.BALANCED_PROVIDER or global_provider
            self._tier_specs[ModelTier.BALANCED] = (settings.LLM_MODEL, b_provider, 0.7)
            try:
                self._instances[ModelTier.BALANCED] = self._create_llm(
                    model=settings.LLM_MODEL, 
                    provider=b_provider,
                    temperature=0.7
                )
                logger.debug(f"✅ Loaded BALANCED tier: {settings.LLM_MODEL} via {b_provider}")
            except Exception as e:
                logger.error(f"❌ Failed to load BALANCED tier: {e}")

            # --- Fast Tier ---
            f_provider = settings.FAST_PROVIDER or global_provider
            self._tier_specs[ModelTier.FAST] = (settings.DEFAULT_CHAT_MODEL, f_provider, 0.3)
            try:
                self._instances[ModelTier.FAST] = self._create_llm(
                    model=settings.DEFAULT_CHAT_MODEL,
                    provider=f_provider,
                    temperature=0.3
                )
                logger.debug(f"✅ Loaded FAST tier: {settings.DEFAULT_CHAT_MODEL} via {f_provider}")
            except Exception as e:
                logger.error(f"❌ Failed to load FAST tier: {e}")

            if not self._instances:
                raise RuntimeError("No LLM tiers could be initialized. Check your .env credentials.")

        except Exception as e:
            logger.error(f"Critical failure in LLMRouter setup: {e}")

    def _create_llm(
        self,
        model: str,
        provider: str,
        temperature: float = 0.7,
        api_key_override: Optional[str] = None,
    ) -> BaseChatModel:
        """Internal factory for LangChain model instances.

        ``api_key_override`` (when set) wins over the global env key. This is
        how per-tenant secrets are injected: SecretManager-resolved value is
        passed in by ``_get_or_create_tenant_llm``.
        """
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
            config["base_url"] = settings.KIMI_API_BASE # Using the fixed setting name
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

        # Per-tenant override wins (already validated non-empty by caller).
        if api_key_override:
            config["api_key"] = api_key_override

        if not config.get("api_key"):
            raise ValueError(f"Missing API Key for provider '{p}'")

        # Attach the budget callback so every LLM call records token usage
        # against the active tenant (read from ContextVar inside the handler).
        try:
            from app.services.governance.token_accountant import BudgetCallbackHandler
            config["callbacks"] = [BudgetCallbackHandler()]
        except Exception as exc:  # noqa: BLE001
            logger.debug("Skipped attaching BudgetCallbackHandler: {}", exc)

        return ChatOpenAI(**config)

    def get_model(self, tier: ModelTier = ModelTier.BALANCED) -> BaseChatModel:
        """Get the chat model instance for the requested tier.

        Resolution order:
        1. If a tenant context is active AND that tenant has a SecretManager
           override for the tier's provider, return a per-tenant instance.
        2. Else fall back to the process-wide default instance.
        """
        # Per-tenant override path (sync, cache-only — pre-warmed by deps).
        try:
            from app.core.tenant_context import get_current_tenant
            from app.services.governance.secret_manager import get_secret_cached_only
            from app.models.tenant import DEFAULT_TENANT_ID

            tid = get_current_tenant()
            if tid and tid != DEFAULT_TENANT_ID and tier in self._tier_specs:
                _model, provider, _temp = self._tier_specs[tier]
                override = get_secret_cached_only(tid, provider_secret_key(provider))
                if override:
                    return self._get_or_create_tenant_llm(tid, tier, override)
        except Exception as exc:  # noqa: BLE001
            logger.debug("per-tenant LLM lookup skipped: {}", exc)

        # Direct hit
        if tier in self._instances:
            return self._instances[tier]
            
        # Failover to BALANCED
        if ModelTier.BALANCED in self._instances:
            return self._instances[ModelTier.BALANCED]
            
        # Absolute fallback to first available
        if self._instances:
            return list(self._instances.values())[0]
            
        raise RuntimeError("No LLM instances available in router.")

    def _get_or_create_tenant_llm(
        self,
        tenant_id: str,
        tier: ModelTier,
        api_key: str,
    ) -> BaseChatModel:
        """Build (and cache) a per-tenant LLM instance with overridden API key."""
        cache_key = (tenant_id, tier)
        cached = self._tenant_instances.get(cache_key)
        if cached is not None:
            return cached
        model, provider, temperature = self._tier_specs[tier]
        instance = self._create_llm(
            model=model,
            provider=provider,
            temperature=temperature,
            api_key_override=api_key,
        )
        self._tenant_instances[cache_key] = instance
        logger.info("🔑 LLMRouter: built per-tenant {} instance for tenant={}", tier.value, tenant_id)
        return instance

    def invalidate_tenant(self, tenant_id: str) -> None:
        """Drop cached per-tenant instances (call after secret PUT/DELETE)."""
        for k in [k for k in self._tenant_instances if k[0] == tenant_id]:
            self._tenant_instances.pop(k, None)

    def list_tiers(self) -> Dict[str, str]:
        """Expose current routing map for UI or logging."""
        return {tier.value: str(getattr(inst, 'model', getattr(inst, 'model_name', 'unknown'))) for tier, inst in self._instances.items()}
