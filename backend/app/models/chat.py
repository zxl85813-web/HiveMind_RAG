"""
Database models for Users, Conversations, Messages.
"""

import uuid
from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

from app.models.tenant import DEFAULT_TENANT_ID


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenant_id: str = Field(
        default=DEFAULT_TENANT_ID, foreign_key="tenants.id", index=True
    )
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    role: str = Field(default="user")  # user | admin
    department_id: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    conversations: list["Conversation"] = Relationship(back_populates="user")


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenant_id: str = Field(
        default=DEFAULT_TENANT_ID, foreign_key="tenants.id", index=True
    )
    title: str = Field(default="New Conversation")
    user_id: str = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    user: User | None = Relationship(back_populates="conversations")
    messages: list["Message"] = Relationship(back_populates="conversation")


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    conversation_id: str = Field(foreign_key="conversations.id", index=True)
    role: str  # user | assistant | system
    content: str
    # P2: Performance & Cost Tracking
    prompt_tokens: int | None = Field(default=0)
    completion_tokens: int | None = Field(default=0)
    total_tokens: int | None = Field(default=0)
    latency_ms: float | None = Field(default=0.0)
    is_cached: bool = Field(default=False)
    # Trace data for custom observability (JSON string)
    trace_data: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)

    conversation: Conversation | None = Relationship(back_populates="messages")
