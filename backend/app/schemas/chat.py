"""
Chat API request/response schemas.
"""

from datetime import datetime

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Request body for chat completions."""

    message: str
    conversation_id: str | None = None
    knowledge_base_ids: list[str] = []
    model: str | None = None  # Override default model
    stream: bool = True


class ChatMessage(BaseModel):
    """A single message in a conversation."""

    id: str
    role: str  # user | assistant | system
    content: str
    created_at: datetime
    metadata: dict | None = None  # sources, agent trace, etc.


class ConversationResponse(BaseModel):
    """Conversation with messages."""

    id: str
    title: str
    messages: list[ChatMessage] = []
    created_at: datetime
    updated_at: datetime


class ConversationListItem(BaseModel):
    """Conversation summary for list view."""

    id: str
    title: str
    last_message_preview: str = ""
    created_at: datetime
    updated_at: datetime
