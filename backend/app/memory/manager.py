"""
Shared Memory Manager — collective memory for the Agent Swarm (v2.0).

Memory Layers:
1. Working Memory (short-term)  — current conversation context, in-progress reasoning
2. Episodic Memory (mid-term)   — recent interactions, conversation summaries
3. Semantic Memory (long-term)  — extracted knowledge, learned patterns, user preferences
4. Shared TODO List             — collective task queue for the swarm

Memory Classification (v2.0, 借鉴 Claude Code 四分类法):
- user      — 用户角色、偏好、知识水平
- feedback  — 用户对工作方式的纠正和确认
- project   — 项目进展、决策、截止日期
- reference — 外部系统指针

设计原则:
- 不存储可从代码/文档推导的信息 (避免记忆膨胀)
- 记忆写入时附带 why 和 how_to_apply (不只是 what)
- 记忆有过期机制, 使用前需验证当前状态

Storage Backends:
- Working Memory  → in-memory / Redis
- Episodic Memory → PostgreSQL + Vector Store
- Semantic Memory → Vector Store (persistent)
- TODO List       → PostgreSQL
"""

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from loguru import logger
from pydantic import BaseModel, Field


# ==========================================
#  Memory Classification (v2.0)
# ==========================================


class MemoryType(StrEnum):
    """
    四分类法 (借鉴 Claude Code memdir/memoryTypes.ts):
    只存储不可从当前项目状态推导的信息。
    """
    USER = "user"          # 用户角色、偏好、知识水平
    FEEDBACK = "feedback"  # 用户对工作方式的纠正和确认
    PROJECT = "project"    # 项目进展、决策、截止日期
    REFERENCE = "reference"  # 外部系统指针


class MemoryEntry(BaseModel):
    """
    A classified memory entry with structured metadata.

    设计原则:
    - name + description 用于未来会话的相关性判断
    - why + how_to_apply 让记忆可操作, 不只是存储事实
    - expires_at 防止记忆无限膨胀
    """
    id: str
    type: MemoryType
    name: str = Field(description="Short title for the memory")
    description: str = Field(description="One-line description — used to decide relevance in future conversations")
    content: str = Field(description="The actual memory content")
    why: str = Field(default="", description="Why this was recorded — the reason or incident behind it")
    how_to_apply: str = Field(default="", description="When/where this memory should influence behavior")
    source: str = Field(default="", description="Who/what created this: 'user', 'agent:rag', 'system'")
    conversation_id: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    is_verified: bool = True  # False if memory needs re-verification


# ==========================================
#  What NOT to save (enforced in store_memory)
# ==========================================

MEMORY_EXCLUSION_PATTERNS = [
    "code pattern",
    "architecture",
    "file structure",
    "git history",
    "recent changes",
    "debugging solution",
    "fix recipe",
]

# ==========================================
#  Shared TODO List
# ==========================================


class TodoPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TodoStatus(StrEnum):
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


class ReflectionType(StrEnum):
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
    Manages the collective memory of the Agent Swarm (v2.0).

    This is the central knowledge repository that all agents
    can read from and write to, enabling coherent collaboration.

    v2.0 新增:
    - 四分类记忆 (user/feedback/project/reference)
    - 记忆过期和验证机制
    - 记忆排除规则 (不存储可推导的信息)
    - 格式化记忆上下文 (用于 Prompt 注入)
    """

    def __init__(self) -> None:
        self._working_memory: dict[str, Any] = {}
        self._todos: list[TodoItem] = []
        self._reflections: list[ReflectionEntry] = []
        self._memories: list[MemoryEntry] = []  # v2.0: classified memories
        logger.info("🧠 SharedMemoryManager v2.0 initialized")

    # --- Classified Memory (v2.0) ---

    async def store_memory(self, entry: MemoryEntry) -> bool:
        """
        Store a classified memory entry.

        Returns False if the memory was rejected (matches exclusion patterns
        or duplicates an existing memory).
        """
        # Check exclusion patterns
        content_lower = entry.content.lower()
        for pattern in MEMORY_EXCLUSION_PATTERNS:
            if pattern in content_lower:
                logger.info(f"🚫 Memory rejected (matches exclusion '{pattern}'): {entry.name}")
                return False

        # Check for duplicates (same type + similar name)
        for existing in self._memories:
            if existing.type == entry.type and existing.name == entry.name:
                # Update instead of duplicate
                existing.content = entry.content
                existing.why = entry.why or existing.why
                existing.how_to_apply = entry.how_to_apply or existing.how_to_apply
                existing.updated_at = datetime.utcnow()
                logger.info(f"🔄 Memory updated: [{entry.type}] {entry.name}")
                return True

        self._memories.append(entry)
        logger.info(f"💾 Memory stored: [{entry.type}] {entry.name}")
        return True

    async def recall_memories(
        self,
        query: str = "",
        memory_type: MemoryType | None = None,
        limit: int = 10,
        include_expired: bool = False,
    ) -> list[MemoryEntry]:
        """
        Recall relevant memories, optionally filtered by type.

        Expired memories are excluded by default.
        """
        now = datetime.utcnow()
        results = []

        for mem in self._memories:
            # Filter by type
            if memory_type and mem.type != memory_type:
                continue
            # Filter expired
            if not include_expired and mem.expires_at and mem.expires_at < now:
                continue
            # Simple keyword match (TODO: replace with vector similarity)
            if query and query.lower() not in (mem.content + mem.name + mem.description).lower():
                continue
            results.append(mem)

        # Sort by recency
        results.sort(key=lambda m: m.updated_at, reverse=True)
        return results[:limit]

    async def format_memory_context(self, query: str = "", limit: int = 10) -> str:
        """
        Format recalled memories into a string suitable for Prompt injection.

        Groups memories by type for clarity.
        """
        memories = await self.recall_memories(query=query, limit=limit)
        if not memories:
            return ""

        sections: dict[str, list[str]] = {}
        for mem in memories:
            type_label = {
                MemoryType.USER: "User Preferences",
                MemoryType.FEEDBACK: "Past Feedback",
                MemoryType.PROJECT: "Project Context",
                MemoryType.REFERENCE: "External References",
            }.get(mem.type, "Other")

            if type_label not in sections:
                sections[type_label] = []

            entry = f"- **{mem.name}**: {mem.content}"
            if mem.why:
                entry += f" (Why: {mem.why})"
            if mem.how_to_apply:
                entry += f" → {mem.how_to_apply}"
            if not mem.is_verified:
                entry += " ⚠️ [unverified — may be outdated]"
            sections[type_label].append(entry)

        lines = []
        for section_name, entries in sections.items():
            lines.append(f"### {section_name}")
            lines.extend(entries)
            lines.append("")

        return "\n".join(lines)

    async def invalidate_stale_memories(self, max_age_days: int = 30) -> int:
        """
        Mark memories older than max_age_days as unverified.
        Returns the number of memories marked.
        """
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        count = 0
        for mem in self._memories:
            if mem.is_verified and mem.updated_at < cutoff:
                mem.is_verified = False
                count += 1
        if count:
            logger.info(f"⏰ Marked {count} memories as unverified (older than {max_age_days} days)")
        return count

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
