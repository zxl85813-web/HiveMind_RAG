"""
BuilderChatService handles the execution of the BuilderGraph
and provides an interface for the API routes.
"""
from typing import Any
from langchain_core.messages import HumanMessage, AIMessage

from .graph import build_builder_graph
from .state import BuilderState

class BuilderChatService:
    def __init__(self):
        self.graph = build_builder_graph()

    async def process_message(self, session_id: str, user_id: str, user_input: str, current_state: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Process a user message through the Builder Graph.
        If `current_state` is provided, we resume from it.
        """
        # 1. Initialize state
        if not current_state:
            state: BuilderState = {
                "session_id": session_id,
                "user_id": user_id,
                "messages": [],
                "confirmed_fields": {},
                "missing_dimensions": [],
                "coverage_pct": 0.0,
                "discovered_context": {},
                "research_insights": [],
                "added_features_count": 0,
                "scope_warning": None,
                "golden_dataset": [],
                "generated_config": None,
                "interview_round": 0,
                "next_step": "continue"
            }
        else:
            # We assume current_state is a dict conforming to BuilderState
            state = current_state  # type: ignore

        # 2. Append the new message
        if user_input:
            # Add user message
            state["messages"] = list(state.get("messages", [])) + [HumanMessage(content=user_input)]

        # 3. Invoke graph
        # In a real app we'd use checkpointer, but here we just pass the state
        final_state = await self.graph.ainvoke(state)

        # 4. Return the new state so the router can save it
        return final_state
