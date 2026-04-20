"""
Database models for Agent Shared Memory (TODOs, Reflections).
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlmodel import JSON, Field, SQLModel


class TodoPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TodoStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_USER = "waiting_user"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TodoItem(SQLModel, table=True):
    __tablename__ = "swarm_todos"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    title: str = Field(index=True)
    description: str = ""
    priority: TodoPriority = Field(default=TodoPriority.MEDIUM)
    status: TodoStatus = Field(default=TodoStatus.PENDING, index=True)
    created_by: str = ""  # Agent name or "user"
    assigned_to: str = Field(default="", index=True)  # Agent name
    source_conversation_id: str | None = Field(default=None, foreign_key="conversations.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    due_at: datetime | None = None
    completed_at: datetime | None = None


class ReflectionType(StrEnum):
    SELF_EVAL = "self_evaluation"
    ERROR_CORRECTION = "error_correction"
    KNOWLEDGE_GAP = "knowledge_gap"
    USER_INTERVENTION = "user_intervention"
    PERIODIC_REVIEW = "periodic_review"


class ReflectionSignalType(StrEnum):
    GAP = "gap"
    ISSUE = "issue"
    INSIGHT = "insight"


class ReflectionEntry(SQLModel, table=True):
    __tablename__ = "swarm_reflections"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    type: ReflectionType = Field(index=True)
    signal_type: str = Field(default=ReflectionSignalType.INSIGHT, index=True)
    agent_name: str = Field(index=True)
    topic: str = Field(default="", index=True)
    match_key: str = Field(default="", index=True)
    tags: list[str] = Field(default_factory=list, sa_type=JSON)
    source_task_id: str = Field(default="", index=True)
    summary: str
    details: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    confidence_score: float = 0.0
    action_taken: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SwarmEpisode(SQLModel, table=True):
    """
    [M4.1.2] Episodic Memory: Records of past swarm interactions/summaries.
    """
    __tablename__ = "swarm_episodes"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    conversation_id: str = Field(index=True)
    summary: str
    details: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    tokens_used: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SwarmKnowledge(SQLModel, table=True):
    """
    [M4.1.3] Semantic Memory: Extracted knowledge or learned patterns.
    """
    __tablename__ = "swarm_knowledge"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    knowledge: str
    source: str = ""
    category: str = Field(default="general", index=True)
    details: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    embedding_id: str | None = Field(default=None, index=True)
