"""
Observability Models for V3 Swarm Architecture.

Replaces Langfuse with a lightweight, extreme-throughput PostgreSQL tracing system.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlmodel import JSON, Field, SQLModel


class TraceStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PENDING_REVIEW = "pending_review"  # HITL condition
    REJECTED = "rejected"
    APPROVED = "approved"


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

    # Context
    kb_id: str | None = Field(default=None, index=True)
    doc_id: str | None = Field(default=None, index=True)

    # Final consolidated output for the file (e.g. extracted text or full markdown)
    result_data: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})


class SpanType(StrEnum):
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


class RAGQueryTrace(SQLModel, table=True):
    """
    Records every RAG retrieval request for observability:
    - Retrieval quality monitoring (hit rate, latency, empty result rate)
    - Usage analysis (hot queries, cold documents)
    """

    __tablename__ = "obs_rag_query_traces"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)

    # Request context
    query: str = Field(index=True)
    kb_ids: list[str] = Field(default_factory=list, sa_type=JSON)
    retrieval_strategy: str = Field(default="hybrid")
    user_id: str | None = Field(default=None, index=True)

    # Results
    total_found: int = Field(default=0)
    returned_count: int = Field(default=0)
    has_results: bool = Field(default=False, index=True)

    # Performance
    latency_ms: float = Field(default=0.0)
    is_error: bool = Field(default=False, index=True)

    # Retrieved document IDs (for cold-document analysis)
    retrieved_doc_ids: list[str] = Field(default_factory=list, sa_type=JSON)

    # Per-step trace log from RetrievalContext.trace_log
    step_traces: list[str] = Field(default_factory=list, sa_type=JSON)

    # Phase 1: Predictive Prefetching & Latency Governance
    prefetch_hit: bool = Field(default=False, index=True)
    intent_predicted: str | None = Field(default=None, index=True)
    time_budget_used: int | None = Field(default=None)

    # 🔒 Integrity Chain (TASK-GOV-002: Audit Immutability)
    p_hash: str | None = Field(default=None, index=True)  # Previous record's integrity hash
    h_integrity: str | None = Field(default=None, index=True)  # SHA-256(p_hash + current_data)

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class SwarmTrace(SQLModel, table=True):
    """
    High-level trace for a multi-agent Swarm request (M4.1.4).
    Synchronizes across multiple specialized workers.
    """

    __tablename__ = "obs_swarm_traces"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str | None = Field(default=None, index=True)
    query: str

    # Triage decision data
    triage_reasoning: str | None = Field(default=None)
    status: TraceStatus = Field(default=TraceStatus.PENDING, index=True)

    total_tokens: int = Field(default=0)
    latency_ms: float = Field(default=0.0)

    # --- GOV-EXP-001: A/B Execution Metrics ---
    execution_variant: str | None = Field(default=None, index=True)
    think_time_ms: float = Field(default=0.0)    # 网路往返 + LLM 生成耗时
    tool_time_ms: float = Field(default=0.0)     # 实际代码/工具执行耗时
    num_llm_calls: int = Field(default=0)        # 为此请求调用的 LLM 次数

    # Quality feedback from Reflection
    quality_score: float | None = Field(default=None)

    details: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class SwarmSpan(SQLModel, table=True):
    """
    Single task execution entry by a specialized agent in a Swarm.
    """

    __tablename__ = "obs_swarm_spans"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    swarm_trace_id: str = Field(foreign_key="obs_swarm_traces.id", index=True)

    agent_name: str = Field(index=True)
    status: TraceStatus = Field(default=TraceStatus.PENDING)

    # Payload
    instruction: str
    output: str | None = Field(default=None)

    # Performance
    tokens: int = Field(default=0)
    latency_ms: float = Field(default=0.0)

    details: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class HITLTask(SQLModel, table=True):
    """
    Queue for Human-in-the-Loop review of ambiguous or low-confidence data.
    """

    __tablename__ = "obs_hitl_tasks"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    trace_id: str = Field(foreign_key="obs_file_traces.id", index=True)

    # Snapshot of the extraction for user to verify
    extracted_data: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    reason: str = Field(default="low_confidence")

    # Reviewer info
    reviewed_by: str | None = Field(default=None, index=True)
    reviewer_comment: str | None = None
    final_verdict: str | None = None  # APPROVED, RETRY, REJECTED

    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: datetime | None = None


class BaselineMetric(SQLModel, table=True):
    """
    Phase 0: Baseline Performance Metrics Repository.
    Captured from the frontend to measure pre-architecture-redesign performance.
    """

    __tablename__ = "obs_baseline_metrics"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    metric_name: str = Field(index=True)
    value: float
    session_id: str | None = Field(default=None, index=True)
    user_id: str | None = Field(default=None, index=True)
    context: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)


class LLMMetric(SQLModel, table=True):
    """
    M7.1: Model Health & Performance Metrics for ClawRouter.
    Tracks real-time latency, error rates, and costs per model/provider.
    """
    __tablename__ = "obs_llm_metrics"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    model_name: str = Field(index=True)
    provider: str = Field(index=True)

    latency_ms: float = Field(default=0.0)
    tokens_input: int = Field(default=0)
    tokens_output: int = Field(default=0)
    cost: float = Field(default=0.0)

    is_error: bool = Field(default=False, index=True)
    error_type: str | None = Field(default=None)

    # Context (e.g. user priority, routing reason)
    context: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
