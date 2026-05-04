"""
LLM Factory for LangChain integration.
Ensures ChatOpenAI instances use the correct provider and API key from .env.
"""
from langchain_openai import ChatOpenAI
from app.agents.llm_router import LLMRouter, ModelTier

_router = LLMRouter()

def get_chat_model(temperature: float = 0.7, model: str = None, json_mode: bool = False) -> ChatOpenAI:
    """
    Returns a ChatOpenAI instance configured with HiveMind settings using LLMRouter.
    """
    # For now, we return the balanced tier, but we can extend this to take a tier
    model_instance = _router.get_model(ModelTier.BALANCED)
    
    # If a specific model is requested, we might need a custom instance 
    # but for most nodes, the balanced tier is what we want.
    
    return model_instance
