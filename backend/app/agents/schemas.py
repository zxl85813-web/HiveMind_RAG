from typing import Annotated, Any, Literal, TypedDict
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, Field
from enum import StrEnum

class ModelTier(StrEnum):
    """Classification of models by capability and cost."""
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    REASONING = "reasoning"

# --- State ---

class SwarmState(TypedDict):
    """
    State stored in LangGraph across the swarm.
    """
    messages: Annotated[list[BaseMessage], lambda a, b: a + b]
    current_task: str
    next_step: str
    agent_outputs: dict[str, Any]
    uncertainty_level: float
    reflection_count: int
    original_query: str
    conversation_id: str
    user_id: str
    auth_context: dict[str, Any]
    force_reasoning_tier: bool
    language: str
    
    # Context
    kb_ids: list[str]
    retrieved_docs: list[dict[str, Any]]
    retrieval_trace: list[str]
    context_data: str
    
    # Observability
    swarm_trace_id: str
    thought_log: str
    
    # Metadata
    execution_variant: str
    reasoning_budget: int
    pinned_messages: list[str]

# --- Structured Outputs ---

class AgentDefinition(BaseModel):
    name: str
    description: str
    model_hint: str | None = None
    tools: list[str] = Field(default_factory=list)

class RoutingDecision(BaseModel):
    """Supervisor's decision on how to route the request."""
    next_agent: str = Field(description="The name of the next agent to invoke, or 'FINISH'")
    uncertainty: float = Field(description="Confidence score (0.0 = confident, 1.0 = uncertain)")
    reasoning: str = Field(description="Reason for this routing decision")
    task_refinement: str = Field(description="Refined description of the task for the agent")
    planned_steps: list[str] = Field(default_factory=list, description="Optional sub-tasks")
    parallel_agents: list[str] = Field(default_factory=list, description="Optional parallel agents")

class ReflectionResult(BaseModel):
    """Reflection node's quality assessment."""
    quality_score: float = Field(description="0.0-1.0 quality assessment")
    issues: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    verdict: str = Field(description="APPROVE | REVISE | ESCALATE")
    trigger_reasoning_tier: bool = Field(default=False)
