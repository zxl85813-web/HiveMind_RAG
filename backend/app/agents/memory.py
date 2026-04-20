"""
Shared Memory Manager — collective memory for the Agent Swarm.

Memory Layers:
1. Working Memory (short-term)  — current conversation context, in-progress reasoning
2. Episodic Memory (mid-term)   — recent interactions, conversation summaries
3. Semantic Memory (long-term)  — extracted knowledge, learned patterns, user preferences
4. Shared TODO List             — collective task queue for the swarm
5. Classified Memory (v2.0)     — user/feedback/project/reference 四分类

Storage Backends:
- Working Memory  → in-memory / Redis
- Episodic Memory → PostgreSQL + Vector Store
- Semantic Memory → Vector Store (persistent)
- TODO List       → PostgreSQL
- Classified Mem  → in-memory (TODO: migrate to PostgreSQL)
"""

import re
from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy import desc, select

from app.core.database import async_session_factory
from app.memory.manager import MemoryEntry, MemoryType, MEMORY_EXCLUSION_PATTERNS
from app.models.agents import (
    ReflectionEntry,
    ReflectionSignalType,
    TodoItem,
    TodoStatus,
    SwarmEpisode,
    SwarmKnowledge,
)


class SharedMemoryManager:
    """
    Manages the collective memory of the Agent Swarm.

    This is the central knowledge repository that all agents
    can read from and write to, enabling coherent collaboration.
    """

    def __init__(self) -> None:
        self._working_memory: dict[str, Any] = {}
        self._classified_memories: list[MemoryEntry] = []  # v2.0: four-type classification
        logger.info("🧠 SharedMemoryManager v2.0 initialized")

    # --- Classified Memory (v2.0, 借鉴 Claude Code 四分类法) ---

    async def store_classified_memory(self, entry: MemoryEntry) -> bool:
        """
        Store a classified memory entry (user/feedback/project/reference).

        Returns False if the memory was rejected (matches exclusion patterns
        or duplicates an existing memory).
        """
        content_lower = entry.content.lower()
        for pattern in MEMORY_EXCLUSION_PATTERNS:
            if pattern in content_lower:
                logger.info(f"🚫 Memory rejected (matches exclusion '{pattern}'): {entry.name}")
                return False

        # Check for duplicates (same type + same name → update)
        for existing in self._classified_memories:
            if existing.type == entry.type and existing.name == entry.name:
                existing.content = entry.content
                existing.why = entry.why or existing.why
                existing.how_to_apply = entry.how_to_apply or existing.how_to_apply
                existing.updated_at = datetime.utcnow()
                logger.info(f"🔄 Memory updated: [{entry.type}] {entry.name}")
                return True

        self._classified_memories.append(entry)
        logger.info(f"💾 Memory stored: [{entry.type}] {entry.name}")
        return True

    async def recall_classified_memories(
        self,
        query: str = "",
        memory_type: MemoryType | None = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Recall classified memories, optionally filtered by type."""
        now = datetime.utcnow()
        results = []
        for mem in self._classified_memories:
            if memory_type and mem.type != memory_type:
                continue
            if mem.expires_at and mem.expires_at < now:
                continue
            if query and query.lower() not in (mem.content + mem.name + mem.description).lower():
                continue
            results.append(mem)
        results.sort(key=lambda m: m.updated_at, reverse=True)
        return results[:limit]

    async def format_memory_context(self, query: str = "", limit: int = 10) -> str:
        """Format classified memories into a string for Prompt injection."""
        memories = await self.recall_classified_memories(query=query, limit=limit)
        if not memories:
            return ""

        sections: dict[str, list[str]] = {}
        type_labels = {
            MemoryType.USER: "User Preferences",
            MemoryType.FEEDBACK: "Past Feedback",
            MemoryType.PROJECT: "Project Context",
            MemoryType.REFERENCE: "External References",
        }
        for mem in memories:
            label = type_labels.get(mem.type, "Other")
            if label not in sections:
                sections[label] = []
            entry = f"- **{mem.name}**: {mem.content}"
            if mem.why:
                entry += f" (Why: {mem.why})"
            if mem.how_to_apply:
                entry += f" → {mem.how_to_apply}"
            if not mem.is_verified:
                entry += " ⚠️ [unverified — may be outdated]"
            sections[label].append(entry)

        lines = []
        for section_name, entries in sections.items():
            lines.append(f"### {section_name}")
            lines.extend(entries)
            lines.append("")
        return "\n".join(lines)

    async def invalidate_stale_memories(self, max_age_days: int = 30) -> int:
        """Mark memories older than max_age_days as unverified."""
        cutoff = datetime.utcnow() - timedelta(days=max_age_days)
        count = 0
        for mem in self._classified_memories:
            if mem.is_verified and mem.updated_at < cutoff:
                mem.is_verified = False
                count += 1
        if count:
            logger.info(f"⏰ Marked {count} memories as unverified (older than {max_age_days} days)")
        return count

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
        try:
            async with async_session_factory() as session:
                session.add(item)
                await session.commit()
                await session.refresh(item)
                logger.info(f"📝 TODO recorded in DB: {item.title} (by {item.created_by})")
                return item
        except Exception as e:
            logger.warning(f"⚠️ Failed to save TODO to DB: {e}")
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
        try:
            async with async_session_factory() as session:
                session.add(entry)
                await session.commit()
                await session.refresh(entry)
                logger.info(f"🪞 Reflection logged in DB: [{entry.type}] by {entry.agent_name}")
                return entry
        except Exception as e:
            logger.warning(f"⚠️ Failed to save Reflection to DB: {e}")
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

    async def get_traces(self, limit: int = 5) -> dict[str, Any]:
        """[M4.1.4] Get high-level execution traces (nodes/links) for the swarm DAG."""
        from app.models.observability import SwarmSpan, SwarmTrace

        try:
            async with async_session_factory() as session:
                # 1. Get the latest N traces
                stmt = select(SwarmTrace).order_by(desc(SwarmTrace.created_at)).limit(limit)
                res = await session.execute(stmt)
                traces = res.scalars().all()

                nodes = []
                links = []

                for t in traces:
                    root_id = f"trace_{t.id}"
                    nodes.append({
                        "id": root_id,
                        "label": (t.query[:30] + "...") if t.query else "Swarm Request",
                        "agent": "supervisor",
                        "status": t.status.value if hasattr(t.status, "value") else str(t.status),
                        "details": t.details or {}
                    })

                    # 2. Get spans for each trace
                    span_stmt = select(SwarmSpan).where(SwarmSpan.swarm_trace_id == t.id)
                    span_res = await session.execute(span_stmt)
                    spans = span_res.scalars().all()

                    for s in spans:
                        span_node_id = f"span_{s.id}"
                        nodes.append({
                            "id": span_node_id,
                            "label": s.agent_name,
                            "agent": s.agent_name,
                            "status": s.status.value if hasattr(s.status, "value") else str(s.status),
                            "duration": f"{s.latency_ms:.0f}ms",
                            "details": {
                                "instruction": s.instruction,
                                "output": s.output,
                                **(s.details or {})
                            }
                        })
                        # Link span to its trace root
                        links.append({
                            "source": root_id,
                            "target": span_node_id,
                            "label": "dispatched"
                        })

                return {"nodes": nodes, "links": links}
        except Exception as e:
            logger.error(f"❌ Failed to fetch traces from DB: {e}")
            return {"nodes": [], "links": [], "error": str(e)}

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
                            f"{gap.agent_name} 与 {insight.agent_name}"
                            f" 进行 15 分钟 Pair Learning，围绕 {gap.match_key} 输出共享笔记"
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
    # Now implemented as persistent DB layers for Phase 4 completion.

    async def store_episode(self, conversation_id: str, summary: str, metadata: dict) -> None:
        """Record an interaction episode (mid-term episodic memory)."""
        try:
            async with async_session_factory() as session:
                episode = SwarmEpisode(
                    conversation_id=conversation_id,
                    summary=summary,
                    metadata=metadata,
                    tokens_used=metadata.get("tokens", 0)
                )
                session.add(episode)
                await session.commit()
                logger.debug(f"📼 Episode recorded for {conversation_id}")
        except Exception as e:
            logger.error(f"❌ Failed to store episode: {e}")

    async def recall_episodes(self, query: str, limit: int = 5) -> list[SwarmEpisode]:
        """Recall past interaction episodes by basic keyword search for now."""
        # TODO: Upgrade to vector search for episodic recall in Phase 6
        async with async_session_factory() as session:
            stmt = select(SwarmEpisode).where(
                SwarmEpisode.summary.contains(query)
            ).order_by(desc(SwarmEpisode.created_at)).limit(limit)
            res = await session.execute(stmt)
            return res.scalars().all()

    async def learn(self, knowledge: str, source: str, category: str = "general") -> None:
        """Extract and store semantic knowledge (long-term memory)."""
        try:
            async with async_session_factory() as session:
                entry = SwarmKnowledge(
                    knowledge=knowledge,
                    source=source,
                    category=category
                )
                session.add(entry)
                await session.commit()
                logger.info(f"💡 New knowledge internalized: {knowledge[:50]}...")
        except Exception as e:
            logger.error(f"❌ Failed to learn: {e}")

    async def recall_knowledge(self, query: str, category: str | None = None, limit: int = 10) -> list[SwarmKnowledge]:
        """Recall long-term semantic knowledge."""
        async with async_session_factory() as session:
            stmt = select(SwarmKnowledge).order_by(desc(SwarmKnowledge.created_at))
            if category:
                stmt = stmt.where(SwarmKnowledge.category == category)
            # Basic keyword filter for MVP
            stmt = stmt.where(SwarmKnowledge.knowledge.contains(query)).limit(limit)
            res = await session.execute(stmt)
            return res.scalars().all()

    async def decay_old_memories(self) -> None:
        """decay/summarization strategy - Placeholder for periodic cleanup."""
        logger.info("🍂 Running memory decay (summarization) - Stub for now")
        pass
