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
    client_events: list[dict] = []  # UI interaction logs (button clicks, navigation, etc.)
    prompt_variant: str = "default"  # Prompt A/B selector
    retrieval_variant: str = "default"  # Retrieval chain A/B selector
    resume_index: int | None = None  # 🛰️ [HMER Phase 3]: Resume from specific chunk index
    is_prefetch: bool = False  # 🆕 [Phase 4.1]: If true, warm up retrieval/cache but don't generate text


class AIAction(BaseModel):
    """AI suggested action button."""

    type: str  # navigate | open_modal | execute | suggest | show_data
    label: str
    target: str
    icon: str | None = None
    params: dict | None = None
    variant: str = "default"  # primary | default | link


class ChatMessage(BaseModel):
    """A single message in a conversation."""

    id: str
    role: str  # user | assistant | system
    content: str
    created_at: datetime
    metadata: dict | None = None  # sources, agent trace, etc.
    actions: list[AIAction] | None = None

    # P2: Performance Metrics
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    is_cached: bool = False
    trace_data: str | None = None


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
