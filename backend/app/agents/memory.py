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
import re
from typing import Any

from loguru import logger
from sqlalchemy import desc, select

from app.core.database import async_session_factory
from app.models.agents import (
    ReflectionEntry,
    ReflectionSignalType,
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

    async def get_reflections(
        self,
        limit: int = 20,
        signal_type: ReflectionSignalType | None = None,
        match_key: str | None = None,
    ) -> Sequence[ReflectionEntry]:
        """Get recent reflection entries from database with optional structured filters."""
        async with async_session_factory() as session:
            statement = select(ReflectionEntry).order_by(desc(ReflectionEntry.created_at)).limit(limit)
            if signal_type:
                statement = statement.where(ReflectionEntry.signal_type == signal_type)
            if match_key:
                statement = statement.where(ReflectionEntry.match_key == match_key)
            results = await session.execute(statement)
            return results.scalars().all()

    async def suggest_gap_matches(self, limit: int = 10) -> list[dict[str, Any]]:
        """Suggest GAP -> INSIGHT pairings by exact key first, then semantic overlap."""
        gaps = await self.get_reflections(limit=200, signal_type=ReflectionSignalType.GAP)
        insights = await self.get_reflections(limit=200, signal_type=ReflectionSignalType.INSIGHT)

        insight_map: dict[str, list[ReflectionEntry]] = {}
        for item in insights:
            if not item.match_key:
                continue
            insight_map.setdefault(item.match_key, []).append(item)

        pairs: list[dict[str, Any]] = []
        seen_pairs: set[tuple[str, str]] = set()

        # 1) High-confidence exact matching via structured key.
        for gap in gaps:
            if not gap.match_key:
                continue
            for insight in insight_map.get(gap.match_key, []):
                pair_id = (gap.id, insight.id)
                if pair_id in seen_pairs:
                    continue
                seen_pairs.add(pair_id)
                pairs.append(
                    {
                        "match_key": gap.match_key,
                        "gap_id": gap.id,
                        "gap_agent": gap.agent_name,
                        "gap_summary": gap.summary,
                        "insight_id": insight.id,
                        "insight_agent": insight.agent_name,
                        "insight_summary": insight.summary,
                        "score": 1.0,
                        "strategy": "exact_key",
                        "recommended_action": (
                            f"{gap.agent_name} 与 {insight.agent_name} 进行 15 分钟 Pair Learning，围绕 {gap.match_key} 输出共享笔记"
                        ),
                    }
                )
                if len(pairs) >= limit:
                    return pairs

        # 2) Semantic fallback by token overlap on topic/summary/tags.
        for gap in gaps:
            gap_tokens = self._reflection_tokens(gap)
            if not gap_tokens:
                continue

            scored: list[tuple[float, ReflectionEntry]] = []
            for insight in insights:
                pair_id = (gap.id, insight.id)
                if pair_id in seen_pairs:
                    continue
                score = self._jaccard_score(gap_tokens, self._reflection_tokens(insight))
                if score >= 0.2:
                    scored.append((score, insight))

            scored.sort(key=lambda x: x[0], reverse=True)
            for score, insight in scored[:2]:
                pair_id = (gap.id, insight.id)
                seen_pairs.add(pair_id)
                pairs.append(
                    {
                        "match_key": gap.match_key or "semantic",
                        "gap_id": gap.id,
                        "gap_agent": gap.agent_name,
                        "gap_summary": gap.summary,
                        "insight_id": insight.id,
                        "insight_agent": insight.agent_name,
                        "insight_summary": insight.summary,
                        "score": round(score, 4),
                        "strategy": "semantic_overlap",
                        "recommended_action": (
                            f"建议 {gap.agent_name} 向 {insight.agent_name} 发起配对学习，并将结论同步到 Issue/周报"
                        ),
                    }
                )
                if len(pairs) >= limit:
                    return pairs

        return pairs

    @staticmethod
    def _reflection_tokens(entry: ReflectionEntry) -> set[str]:
        text = " ".join(
            [
                entry.topic or "",
                entry.summary or "",
                " ".join(entry.tags or []),
                str(entry.details.get("raw_reflection_type", "")),
            ]
        ).lower()
        tokens = set(re.findall(r"[a-z0-9_\-\u4e00-\u9fff]+", text))
        stop_words = {
            "the",
            "and",
            "for",
            "with",
            "this",
            "that",
            "from",
            "have",
            "未",
            "已",
            "进行",
            "关于",
            "问题",
            "建议",
        }
        return {t for t in tokens if len(t) > 1 and t not in stop_words}

    @staticmethod
    def _jaccard_score(left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        inter = left & right
        union = left | right
        if not union:
            return 0.0
        return len(inter) / len(union)

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
