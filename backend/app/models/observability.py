"""
Observability Models for V3 Swarm Architecture.

Replaces Langfuse with a lightweight, extreme-throughput PostgreSQL tracing system.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlmodel import Field, SQLModel, JSON


class TraceStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PENDING_REVIEW = "pending_review"  # HITL condition


class IngestionBatch(SQLModel, table=True):
    """
    Represents a massive batch job (e.g. 100k files).
    """
    __tablename__ = "obs_ingestion_batches"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    description: str = Field(default="")
    total_files: int = Field(default=0)
    completed_files: int = Field(default=0)
    failed_files: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class FileTrace(SQLModel, table=True):
    """
    Represents the trace of a single file going through the Swarm.
    """
    __tablename__ = "obs_file_traces"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)  # trace_id
    batch_id: str | None = Field(default=None, index=True)
    file_path: str = Field(index=True)
    status: TraceStatus = Field(default=TraceStatus.PENDING, index=True)
    
    total_tokens: int = Field(default=0)
    latency_ms: float = Field(default=0.0)
    error_message: str | None = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})


class SpanType(str, Enum):
    LLM_CALL = "llm_call"
    TOOL_INVOKE = "tool_invoke"
    ROUTER = "router"
    AGENT_NODE = "agent_node"


class AgentSpan(SQLModel, table=True):
    """
    Represents a specific action taken by an Agent within a FileTrace.
    """
    __tablename__ = "obs_agent_spans"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)  # span_id
    trace_id: str = Field(foreign_key="obs_file_traces.id", index=True)
    
    agent_name: str = Field(index=True)  # e.g., CodeAgentNode, CriticNode
    action_type: SpanType = Field(index=True)
    
    # We only store the absolute minimum payload to avoid DB bloat:
    # {"prompt_summary": "...", "tool_args": {...}, "output_summary": "..."}
    payload: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    
    tokens: int = Field(default=0)
    latency_ms: float = Field(default=0.0)
    is_error: bool = Field(default=False)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
