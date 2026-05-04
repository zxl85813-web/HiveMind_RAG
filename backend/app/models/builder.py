"""
Database models for the Agent Builder Assistant (REQ-014).
Includes Agent Configuration, Builder Sessions (Phase 0 interview state),
Eval Harnesses (EDD), and Sandbox Sessions.
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from sqlmodel import Field, SQLModel, JSON

class AgentStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"

class AgentConfig(SQLModel, table=True):
    """
    Persisted configuration for a dynamic Agent created via Builder Assistant.
    """
    __tablename__ = "builder_agent_configs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True)
    system_prompt: str = ""
    tools_config: list[str] = Field(default_factory=list, sa_type=JSON) # e.g., ["search_knowledge_base", "web_search"]
    kb_bindings: list[str] = Field(default_factory=list, sa_type=JSON)  # List of KB IDs
    status: AgentStatus = Field(default=AgentStatus.DRAFT, index=True)
    created_by: str = Field(index=True) # user_id

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BuilderPhase(str, Enum):
    INTERVIEW = "interview"
    SANDBOX = "sandbox"
    PUBLISHED = "published"

class BuilderSession(SQLModel, table=True):
    """
    State tracking for the 6-stage Builder Assistant interview process.
    """
    __tablename__ = "builder_sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(index=True)
    agent_id: Optional[str] = Field(default=None, foreign_key="builder_agent_configs.id", index=True)
    
    # State tracking
    confirmed_fields: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    discovered_context: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    research_insights: list[str] = Field(default_factory=list, sa_type=JSON)
    coverage_pct: float = 0.0
    interview_rounds: int = 0
    phase: BuilderPhase = Field(default=BuilderPhase.INTERVIEW, index=True)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EvalHarness(SQLModel, table=True):
    """
    Eval-Driven Development (EDD) Scaffolding generated from Golden Datasets.
    """
    __tablename__ = "builder_eval_harnesses"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    builder_session_id: str = Field(foreign_key="builder_sessions.id", index=True)
    
    # List of test cases. E.g., {"question": "...", "expected_tool": "...", "expected_answer": "..."}
    golden_dataset: list[dict[str, Any]] = Field(default_factory=list, sa_type=JSON)
    
    # LLM-as-a-judge criteria
    grading_rubric: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    
    # Cost budget for the run (hard cap)
    cost_budget_usd: float = Field(default=0.05)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class SandboxSession(SQLModel, table=True):
    """
    Deterministic test run of an Agent Config against an Eval Harness.
    """
    __tablename__ = "builder_sandbox_sessions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    builder_session_id: str = Field(foreign_key="builder_sessions.id", index=True)
    eval_harness_id: Optional[str] = Field(default=None, foreign_key="builder_eval_harnesses.id", index=True)
    agent_id: str = Field(foreign_key="builder_agent_configs.id", index=True)
    user_id: str = Field(index=True)
    
    input_payload: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    execution_dag: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    
    # Evaluation Metrics
    process_metrics: dict[str, Any] = Field(default_factory=dict, sa_type=JSON) # e.g. tool failures
    outcome_metrics: dict[str, Any] = Field(default_factory=dict, sa_type=JSON) # e.g. llm judge score
    
    # Cost tracking
    token_cost_usd: float = 0.0
    total_tokens: int = 0

    created_at: datetime = Field(default_factory=datetime.utcnow)
