"""
Shared Memory Manager — collective memory for the Agent Swarm.

Memory Layers:
1. Working Memory (short-term)  — current conversation context, in-progress reasoning
2. Episodic Memory (mid-term)   — recent interactions, conversation summaries
3. Semantic Memory (long-term)  — extracted knowledge, learned patterns, user preferences
4. Shared TODO List             — collective task queue for the swarm

Storage Backends:
- Working Memory  → in-memory / Redis
- Episodic Memory → PostgreSQL + Vector Store
- Semantic Memory → Vector Store (persistent)
- TODO List       → PostgreSQL
"""

from datetime import datetime
from enum import Enum
from typing import Any

from loguru import logger
from pydantic import BaseModel

# ==========================================
#  Shared TODO List
# ==========================================


class TodoPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TodoStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    WAITING_USER = "waiting_user"  # Needs user input
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TodoItem(BaseModel):
    """An item in the swarm's shared TODO list."""

    id: str
    title: str
    description: str = ""
    priority: TodoPriority = TodoPriority.MEDIUM
    status: TodoStatus = TodoStatus.PENDING
    created_by: str = ""  # Agent name or "user"
    assigned_to: str = ""  # Agent name
    source_conversation_id: str = ""
    created_at: datetime = datetime.utcnow()
    due_at: datetime | None = None
    completed_at: datetime | None = None


# ==========================================
#  Reflection Log
# ==========================================


class ReflectionType(str, Enum):
    SELF_EVAL = "self_evaluation"  # Quality assessment of own output
    ERROR_CORRECTION = "error_correction"  # Detected and corrected an error
    KNOWLEDGE_GAP = "knowledge_gap"  # Identified missing knowledge
    USER_INTERVENTION = "user_intervention"  # Requesting user help
    PERIODIC_REVIEW = "periodic_review"  # Scheduled memory review


class ReflectionEntry(BaseModel):
    """A record of an agent's self-reflection."""

    id: str
    type: ReflectionType
    agent_name: str
    summary: str
    details: dict[str, Any] = {}
    confidence_score: float = 0.0  # 0.0 - 1.0
    action_taken: str = ""
    created_at: datetime = datetime.utcnow()


# ==========================================
#  Memory Manager
# ==========================================


class SharedMemoryManager:
    """
    Manages the collective memory of the Agent Swarm.

    This is the central knowledge repository that all agents
    can read from and write to, enabling coherent collaboration.
    """

    def __init__(self) -> None:
        self._working_memory: dict[str, Any] = {}
        self._todos: list[TodoItem] = []
        self._reflections: list[ReflectionEntry] = []
        logger.info("🧠 SharedMemoryManager initialized")

    # --- Working Memory ---

    async def set_working(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Store a value in working memory (short-term, session-scoped)."""
        # TODO: Use Redis in production
        self._working_memory[key] = value

    async def get_working(self, key: str) -> Any | None:
        """Retrieve from working memory."""
        return self._working_memory.get(key)

    # --- Episodic Memory ---

    async def store_episode(self, conversation_id: str, summary: str, metadata: dict) -> None:
        """Store a conversation episode summary for future retrieval."""
        # TODO: Implement
        # - Generate embedding of the summary
        # - Store in vector database with metadata
        # - Store summary in PostgreSQL
        pass

    async def recall_episodes(self, query: str, limit: int = 5) -> list[dict]:
        """Recall relevant past episodes based on semantic similarity."""
        # TODO: Implement vector similarity search
        return []

    # --- Semantic Memory ---

    async def learn(self, knowledge: str, source: str, category: str = "general") -> None:
        """
        Store a piece of learned knowledge in long-term memory.
        Called when agents extract useful patterns or facts.
        """
        # TODO: Implement
        pass

    async def recall_knowledge(self, query: str, category: str | None = None, limit: int = 10) -> list[dict]:
        """Recall relevant knowledge from long-term memory."""
        # TODO: Implement
        return []

    # --- Shared TODO ---

    async def add_todo(self, item: TodoItem) -> None:
        """Add a new TODO item to the swarm's shared list."""
        self._todos.append(item)
        logger.info(f"📝 TODO added: {item.title} (by {item.created_by})")
        # TODO: Push notification via WebSocket

    async def update_todo(self, todo_id: str, **updates: Any) -> None:
        """Update a TODO item's status or fields."""
        # TODO: Implement
        pass

    async def get_todos(self, status: TodoStatus | None = None) -> list[TodoItem]:
        """Get TODO items, optionally filtered by status."""
        if status:
            return [t for t in self._todos if t.status == status]
        return self._todos

    # --- Reflection ---

    async def add_reflection(self, entry: ReflectionEntry) -> None:
        """Record a self-reflection from an agent."""
        self._reflections.append(entry)
        logger.info(f"🪞 Reflection: [{entry.type}] by {entry.agent_name} - {entry.summary}")
        # TODO: If confidence is low, trigger user intervention notification

    async def get_reflections(self, limit: int = 20) -> list[ReflectionEntry]:
        """Get recent reflection entries."""
        return self._reflections[-limit:]

    # --- Memory Decay ---

    async def decay_old_memories(self) -> None:
        """
        Periodic task: decay or archive old working memories.
        Long-term semantic memory is preserved.
        """
        # TODO: Implement memory decay strategy
        pass
