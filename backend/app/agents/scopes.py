from loguru import logger
from app.agents.schemas import SwarmState

class ScopedStateView:
    """
    [M5.1.1] Scoped State Sharing.
    Defines and enforces which state fields are visible to specific agents.
    Prevents 'Context Pollution' and accidental data leaks.
    """

    # Default visibility for any agent
    DEFAULT_SCOPE = [
        "messages",
        "current_task",
        "original_query",
        "conversation_id",
        "user_id",
        "language",
        "pinned_messages",
    ]

    # Specialized visibility for core nodes
    AGENT_SCOPES = {
        "supervisor": DEFAULT_SCOPE + ["next_step", "agent_outputs", "uncertainty_level", "swarm_trace_id", "kb_ids"],
        "reflection": DEFAULT_SCOPE + ["agent_outputs", "reflection_count", "context_data"],
        "retrieval": DEFAULT_SCOPE + ["context_data", "kb_ids", "retrieval_variant"],
        "rag": DEFAULT_SCOPE + ["kb_ids", "retrieval_trace", "retrieved_docs", "context_data"],
        "sql": DEFAULT_SCOPE + ["current_task", "context_data"],
        "code": DEFAULT_SCOPE + ["current_task", "context_data", "reasoning_budget", "execution_variant"],
    }

    @classmethod
    def filter(cls, state: dict, agent_name: str) -> dict:
        """Filters the global state to a subset allowed for the specific agent."""
        # Normalize agent name (e.g. 'code_agent_1' -> 'code')
        base_name = agent_name.split("_")[0].lower()
        allowed_keys = cls.AGENT_SCOPES.get(base_name, cls.DEFAULT_SCOPE)

        filtered = {k: v for k, v in state.items() if k in allowed_keys}

        # Debug log for significant omissions
        omitted = set(state.keys()) - set(allowed_keys)
        if omitted:
            logger.trace(f"🛡️ [ScopedState] {agent_name} view filtered. Omitted {len(omitted)} keys.")

        return filtered
