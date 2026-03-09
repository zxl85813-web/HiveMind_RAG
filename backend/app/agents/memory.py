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

from collections.abc import Sequence
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy import desc, select

from app.core.database import async_session_factory
from app.models.agents import (
    ReflectionEntry,
    TodoItem,
    TodoStatus,
)


class SharedMemoryManager:
    """
    Manages the collective memory of the Agent Swarm.

    This is the central knowledge repository that all agents
    can read from and write to, enabling coherent collaboration.
    """

    def __init__(self) -> None:
        self._working_memory: dict[str, Any] = {}
        logger.info("🧠 SharedMemoryManager initialized")

    # --- Working Memory (Session-scoped) ---

    async def set_working(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Store a value in working memory (short-term)."""
        # TODO: Implement TTL with Redis
        self._working_memory[key] = value

    async def get_working(self, key: str) -> Any | None:
        """Retrieve from working memory."""
        return self._working_memory.get(key)

    # --- Shared TODO List (Persistent) ---

    async def add_todo(self, item: TodoItem) -> TodoItem:
        """Add a new TODO item to the swarm's shared list."""
        async with async_session_factory() as session:
            session.add(item)
            await session.commit()
            await session.refresh(item)
            logger.info(f"📝 TODO recorded in DB: {item.title} (by {item.created_by})")
            return item

    async def update_todo(self, todo_id: str, **updates: Any) -> TodoItem | None:
        """Update a TODO item's status or fields."""
        async with async_session_factory() as session:
            todo = await session.get(TodoItem, todo_id)
            if not todo:
                return None

            for key, value in updates.items():
                if hasattr(todo, key):
                    setattr(todo, key, value)

            if updates.get("status") == TodoStatus.COMPLETED:
                todo.completed_at = datetime.utcnow()

            session.add(todo)
            await session.commit()
            await session.refresh(todo)
            return todo

    async def get_todos(self, status: TodoStatus | None = None, limit: int = 50) -> Sequence[TodoItem]:
        """Get TODO items from database."""
        async with async_session_factory() as session:
            # Using session.exec for SQLModel
            statement = select(TodoItem).order_by(desc(TodoItem.created_at))
            if status:
                statement = statement.where(TodoItem.status == status)
            statement = statement.limit(limit)

            results = await session.execute(statement)
            return results.scalars().all()

    # --- Reflection Log (Persistent) ---

    async def add_reflection(self, entry: ReflectionEntry) -> ReflectionEntry:
        """Record a self-reflection from an agent to the database."""
        async with async_session_factory() as session:
            session.add(entry)
            await session.commit()
            await session.refresh(entry)
            logger.info(f"🪞 Reflection logged in DB: [{entry.type}] by {entry.agent_name}")
            return entry

    async def get_reflections(self, limit: int = 20) -> Sequence[ReflectionEntry]:
        """Get recent reflection entries from database."""
        async with async_session_factory() as session:
            statement = select(ReflectionEntry).order_by(desc(ReflectionEntry.created_at)).limit(limit)
            results = await session.execute(statement)
            return results.scalars().all()

    # --- Future Memory Layers (Episodic/Semantic) ---

    async def store_episode(self, conversation_id: str, summary: str, metadata: dict) -> None:
        """Placeholder for Episodic Memory (Vector-based interaction logs)."""
        pass

    async def recall_episodes(self, query: str, limit: int = 5) -> list[dict]:
        """Placeholder for recalling past interaction episodes."""
        return []

    async def learn(self, knowledge: str, source: str, category: str = "general") -> None:
        """Placeholder for extracted knowledge (Semantic Memory)."""
        pass

    async def recall_knowledge(self, query: str, category: str | None = None, limit: int = 10) -> list[dict]:
        """Placeholder for recalling long-term semantic knowledge."""
        return []

    async def decay_old_memories(self) -> None:
        """Placeholder for memory decay/summarization strategy."""
        pass
