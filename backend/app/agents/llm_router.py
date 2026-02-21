"""
Multi-LLM Router — intelligent model selection and failover.

Routes requests to the most appropriate LLM based on:
- Task type (reasoning, chat, code, summarization, embedding)
- Cost constraints
- Latency requirements
- Model availability

Supports fallback chains for reliability.
"""

from enum import Enum
from typing import Any

from langchain_core.language_models import BaseChatModel
from loguru import logger
from pydantic import BaseModel


class TaskType(str, Enum):
    """Classification of tasks for routing purposes."""

    CHAT = "chat"  # General conversation
    REASONING = "reasoning"  # Complex analysis, planning
    CODE = "code"  # Code generation
    SUMMARIZATION = "summarization"  # Text summarization
    EXTRACTION = "extraction"  # Information extraction
    ROUTING = "routing"  # Agent routing decisions (fast + cheap)
    EMBEDDING = "embedding"  # Text embedding (separate model type)


class ModelProvider(str, Enum):
    OPENAI = "openai"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"
    ZHIPU = "zhipu"
    OLLAMA = "ollama"
    VLLM = "vllm"


class ModelConfig(BaseModel):
    """Configuration for a single LLM model."""

    provider: ModelProvider
    model_name: str
    display_name: str
    supported_tasks: list[TaskType]
    base_url: str | None = None
    api_key_env: str = ""
    max_tokens: int = 4096
    temperature: float = 0.7
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0
    priority: int = 0  # Higher = preferred


class LLMRouter:
    """
    Intelligent LLM router with fallback support.

    Usage:
        router = LLMRouter()
        llm = router.get_model(TaskType.REASONING)
        response = await llm.ainvoke(messages)
    """

    def __init__(self) -> None:
        self._models: dict[str, ModelConfig] = {}
        self._instances: dict[str, BaseChatModel] = {}
        self._fallback_chains: dict[TaskType, list[str]] = {}
        logger.info("🔀 LLMRouter initialized")

    def register_model(self, config: ModelConfig) -> None:
        """Register a model configuration."""
        key = f"{config.provider}:{config.model_name}"
        self._models[key] = config
        logger.info(f"Model registered: {config.display_name} ({key})")

    def get_model(self, task_type: TaskType, preferred_model: str | None = None) -> BaseChatModel:
        """
        Get the best model for a given task type.

        Args:
            task_type: The type of task to route
            preferred_model: Optional specific model override

        Returns:
            A LangChain chat model instance
        """
        # TODO: Implement model selection logic
        # 1. If preferred_model specified, use it
        # 2. Otherwise, find best model for task_type based on priority
        # 3. Instantiate BaseChatModel (lazy, cached)
        # 4. Return with fallback wrapper
        raise NotImplementedError("LLM routing not yet implemented")

    def _create_instance(self, config: ModelConfig) -> BaseChatModel:
        """Create a LangChain model instance from configuration."""
        # TODO: Implement for each provider
        # match config.provider:
        #     case ModelProvider.OPENAI:
        #         from langchain_openai import ChatOpenAI
        #         return ChatOpenAI(model=config.model_name, ...)
        #     case ModelProvider.DEEPSEEK:
        #         return ChatOpenAI(base_url=config.base_url, ...)
        #     case ModelProvider.OLLAMA:
        #         from langchain_ollama import ChatOllama
        #         return ChatOllama(model=config.model_name)
        raise NotImplementedError()

    def list_available_models(self) -> list[ModelConfig]:
        """List all registered model configurations."""
        return list(self._models.values())

    def get_usage_stats(self) -> dict[str, Any]:
        """Get usage statistics per model."""
        # TODO: Implement token counting, cost tracking
        return {}
