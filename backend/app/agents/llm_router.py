"""
Multi-LLM Router — intelligent model selection, cost optimization, and failover.
Integrated with HiveDispatcher (Intelligence Orchestrator).

Routes requests based on task complexity (Model Tiering) to save inference costs.
"""

from enum import StrEnum

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from loguru import logger

from app.core.algorithms.routing import Route, semantic_router
from app.core.config import settings


from app.agents.schemas import ModelTier


class LLMRouter:
    """
    Orchestrates multiple LLM instances to balance quality and cost.
    Uses SemanticRouter to auto-route prompts to the correct tier.
    """

    def __init__(self) -> None:
        self._instances: dict[ModelTier, BaseChatModel] = {}
        self._setup_default_routes()
        self._register_semantic_routes()
        logger.info("🐝 HiveDispatcher Integration: Router Mode active")

    def _register_semantic_routes(self) -> None:
        """Register the 4-tier semantic routes based on HiveDispatcher rules."""
        semantic_router.add_route(Route(
            name=ModelTier.SIMPLE.value,
            utterances=[
                "Hello, how are you?",
                "Translate this to French",
                "What is the capital of France?",
                "What time is it?",
                "Give me a quick fact about the moon",
                "Hi there",
            ]
        ))
        semantic_router.add_route(Route(
            name=ModelTier.MEDIUM.value,
            utterances=[
                "Summarize this document",
                "Explain the history of the industrial revolution",
                "Extract the names and dates from this email",
                "Write a short blog post about AI",
                "Compare these two products"
            ]
        ))
        semantic_router.add_route(Route(
            name=ModelTier.COMPLEX.value,
            utterances=[
                "Write a Python script to scrape a website",
                "Help me debug this React component",
                "Analyze this financial data and tell me the trends",
                "Design a system architecture for a high-traffic app",
                "What is wrong with this SQL query?"
            ]
        ))
        semantic_router.add_route(Route(
            name=ModelTier.REASONING.value,
            utterances=[
                "Solve this complex mathematical physics problem",
                "Prove this mathematical theorem",
                "Use formal logic to deduce the answer",
                "Think step by step to solve this logic puzzle",
                "Write a mathematical proof for P vs NP"
            ]
        ))

    def _setup_default_routes(self) -> None:
        """Initialize models for each tier from settings."""
        try:
            global_provider = settings.LLM_PROVIDER

            # --- SIMPLE Tier ---
            try:
                p = settings.SIMPLE_PROVIDER or global_provider
                self._instances[ModelTier.SIMPLE] = self._create_llm(
                    model=settings.DEFAULT_SIMPLE_MODEL, provider=p, temperature=0.3
                )
            except Exception as e:
                logger.error(f"❌ Failed to load SIMPLE tier: {e}")

            # --- MEDIUM Tier ---
            try:
                p = settings.MEDIUM_PROVIDER or global_provider
                self._instances[ModelTier.MEDIUM] = self._create_llm(
                    model=settings.DEFAULT_MEDIUM_MODEL, provider=p, temperature=0.6
                )
            except Exception as e:
                logger.error(f"❌ Failed to load MEDIUM tier: {e}")

            # --- COMPLEX Tier ---
            try:
                p = settings.COMPLEX_PROVIDER or global_provider
                self._instances[ModelTier.COMPLEX] = self._create_llm(
                    model=settings.DEFAULT_COMPLEX_MODEL, provider=p, temperature=0.7
                )
            except Exception as e:
                logger.error(f"❌ Failed to load COMPLEX tier: {e}")

            # --- REASONING Tier ---
            try:
                p = settings.REASONING_PROVIDER or global_provider
                self._instances[ModelTier.REASONING] = self._create_llm(
                    model=settings.DEFAULT_REASONING_MODEL, provider=p, temperature=0.8
                )
            except Exception as e:
                logger.error(f"❌ Failed to load REASONING tier: {e}")

        except Exception as e:
            logger.error(f"Critical failure in LLMRouter setup: {e}")

    def _create_llm(self, model: str, provider: str, temperature: float = 0.7) -> BaseChatModel:
        """Internal factory for LangChain model instances."""
        p = provider.lower()
        config = {"model": model, "temperature": temperature}

        if p == "ark":
            config["api_key"] = settings.ARK_API_KEY
            config["base_url"] = settings.ARK_BASE_URL
        elif p == "openai":
            config["api_key"] = settings.OPENAI_API_KEY
            config["base_url"] = settings.OPENAI_BASE_URL
        else:
            config["api_key"] = settings.LLM_API_KEY or settings.OPENAI_API_KEY
            config["base_url"] = settings.LLM_BASE_URL or settings.OPENAI_BASE_URL

        return ChatOpenAI(**config)

    async def auto_route(self, prompt: str) -> BaseChatModel:
        """
        Dynamically routes the prompt based on semantic footprint.
        """
        decision = await semantic_router.route(prompt, routes=[], threshold=0.15)

        target_tier = ModelTier(decision.target_node) if decision.target_node in [t.value for t in ModelTier] else ModelTier.MEDIUM
        logger.debug(f"🐝 [HiveDispatcher] Routed to {target_tier.name} (confidence={decision.confidence:.2f})")

        return self.get_model(target_tier)

    def get_model(self, tier: ModelTier = ModelTier.MEDIUM) -> BaseChatModel:
        """Get the chat model instance for the requested tier."""
        if tier in self._instances:
            return self._instances[tier]
        return next(iter(self._instances.values()))
