"""
Database models for Users, Conversations, Messages.
"""

import uuid
from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    role: str = Field(default="user")  # user | admin
    created_at: datetime = Field(default_factory=datetime.utcnow)

    conversations: list["Conversation"] = Relationship(back_populates="user")


class Conversation(SQLModel, table=True):
    __tablename__ = "conversations"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
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
    metadata_json: str | None = None  # JSON: model used, agent trace, sources, etc.

    # Feedback fields
    rating: int = Field(default=0)  # 0: None, 1: Like, -1: Dislike
    feedback_text: str | None = None  # User's reason for feedback

    created_at: datetime = Field(default_factory=datetime.utcnow)

    conversation: Conversation | None = Relationship(back_populates="messages")
