"""
Database models for Agent Shared Memory (TODOs, Reflections).
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlmodel import Field, SQLModel, JSON


class TodoPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TodoStatus(str, Enum):
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
    status: TodoStatus = Field(default=TodoStatus.PENDING)
    created_by: str = ""  # Agent name or "user"
    assigned_to: str = ""  # Agent name
    source_conversation_id: str | None = Field(default=None, foreign_key="conversations.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    due_at: datetime | None = None
    completed_at: datetime | None = None


class ReflectionType(str, Enum):
    SELF_EVAL = "self_evaluation"
    ERROR_CORRECTION = "error_correction"
    KNOWLEDGE_GAP = "knowledge_gap"
    USER_INTERVENTION = "user_intervention"
    PERIODIC_REVIEW = "periodic_review"


class ReflectionEntry(SQLModel, table=True):
    __tablename__ = "swarm_reflections"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    type: ReflectionType = Field(index=True)
    agent_name: str = Field(index=True)
    summary: str
    details: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    confidence_score: float = 0.0
    action_taken: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
