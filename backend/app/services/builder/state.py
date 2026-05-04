import operator
from typing import Annotated, Any, Sequence, TypedDict

from langchain_core.messages import BaseMessage


def add_messages(left: Sequence[BaseMessage], right: Sequence[BaseMessage]) -> Sequence[BaseMessage]:
    """Append new messages to the existing list."""
    return list(left) + list(right)


class BuilderState(TypedDict):
    """
    LangGraph State for the Agent Builder Assistant (6-stage interview).
    """
    session_id: str
    user_id: str
    
    # 1. Dialog History
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # 2. Extracted Requirements (Stage 1 & 4)
    # Target keys: core_role, target_user, boundary, tone, guardrails, fallback_strategy, success_metrics, tools
    confirmed_fields: dict[str, Any]
    missing_dimensions: list[str]
    coverage_pct: float
    
    # 3. Context & Discovery (Stage 2 & 3)
    discovered_context: dict[str, Any]  # e.g., matched skills, existing KBs, templates
    research_insights: list[str]
    
    # 4. Anti-Sycophancy Guardian (Scope Control)
    added_features_count: int
    scope_warning: str | None
    
    # 5. Eval Harness Co-creation (Stage 5)
    golden_dataset: list[dict[str, Any]]
    
    # 6. Final Outputs (Stage 6)
    generated_config: dict[str, Any] | None
    
    # Internal routing & flow control
    interview_round: int
    next_step: str  # e.g., 'continue', 'force_scope_review', 'generate'
