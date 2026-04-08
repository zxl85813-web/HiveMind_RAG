"""
Episodic Memory Service — 跨会话情节记忆的写入与召回。

写入触发时机（双触发点）:
  1. 会话结束时 (ChatService.end_conversation) — 主动触发
  2. _compact_messages 生成摘要时 — 被动消费

召回触发时机:
  1. get_context(query) — 与三层记忆并列注入
  2. context-migration skill 触发时

参见: docs/design/multi_tier_memory.md
"""

import asyncio
import json
from datetime import datetime
from typing import Any

import chromadb
from loguru import logger
from pydantic import BaseModel

from app.core.database import async_session_factory
from app.core.llm import get_llm_service
from app.models.episodic import EpisodicMemory

# ── 摘要生成提示词模板 ─────────────────────────────────────────
_EPISODE_SUMMARY_PROMPT = """
You are a session memory distiller. Analyze the following conversation and extract:
1. A concise summary (max 150 words) capturing what was accomplished
2. Key decisions made (list of strings, max 5)
3. Main topics covered (keywords, max 8)
4. The user's core intent in one sentence

Return ONLY valid JSON:
{{
    "summary": "...",
    "key_decisions": ["decision1", "decision2"],
    "topics": ["topic1", "topic2"],
    "user_intent": "..."
}}

CONVERSATION:
{dialogue}
"""


class EpisodeDistillResult(BaseModel):
    summary: str
    key_decisions: list[str]
    topics: list[str]
    user_intent: str


class EpisodicMemoryService:
    """情节记忆服务 — 跨会话记忆的核心引擎。"""

    _chroma_collection = None

    @classmethod
    def _get_collection(cls):
        if cls._chroma_collection is None:
            # Use the same path as MemoryService for consistency
            client = chromadb.PersistentClient(path="./start_data/chroma_db")
            cls._chroma_collection = client.get_or_create_collection(
                name="episodic_episodes", metadata={"hnsw:space": "cosine"}
            )
        return cls._chroma_collection

    # ─────────────────────────────────────────────
    # 写入路径 (Write Path)
    # ─────────────────────────────────────────────

    async def store_episode(
        self,
        user_id: str,
        conversation_id: str,
        messages: list[Any],  # [{"role": "user"|"assistant", "content": "..."}]
        agent_names: list[str] | None = None,
        pre_computed_summary: str | None = None,
    ) -> EpisodicMemory | None:
        """
        将一次完整会话蒸馏为情节记忆并持久化。
        """
        if not messages:
            return None

        # 1. 过滤低价值会话（少于 3 轮消息）
        meaningful_messages = [m for m in messages if len(self._get_msg_field(m, "content")) > 20]
        if len(meaningful_messages) < 3:
            logger.debug(f"[EpisodicMemory] Skipping low-value session: {conversation_id}")
            return None

        # 2. 蒸馏会话（使用已有摘要或重新生成）
        if pre_computed_summary:
            distill = await self._parse_or_generate_distill(pre_computed_summary, messages)
        else:
            distill = await self._distill_conversation(messages)

        if not distill:
            logger.warning(f"❌ [EpisodicMemory] Distillation returned None for conv={conversation_id}")
            return None

        print(f"✅ [EpisodicMemory] Distilled successfully: {distill.topics}")

        # 3. 写入 PostgreSQL (Upsert by conversation_id)
        async with async_session_factory() as session:
            from sqlmodel import select

            stmt = select(EpisodicMemory).where(EpisodicMemory.conversation_id == conversation_id)
            episode = (await session.execute(stmt)).scalar_one_or_none()

            if episode:
                episode.summary = distill.summary
                episode.key_decisions = distill.key_decisions
                episode.topics = distill.topics
                episode.user_intent = distill.user_intent
                episode.message_count = len(messages)
                episode.topic_coverage = self._calc_topic_coverage(messages)
                episode.temperature = 1.0  # 重置温度
            else:
                episode = EpisodicMemory(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    agent_names=agent_names or [],
                    summary=distill.summary,
                    key_decisions=distill.key_decisions,
                    topics=distill.topics,
                    user_intent=distill.user_intent,
                    message_count=len(messages),
                    topic_coverage=self._calc_topic_coverage(messages),
                )
                session.add(episode)

            await session.commit()
            await session.refresh(episode)

        logger.info(
            f"📼 [EpisodicMemory] Stored episode {episode.id} "
            f"for user={user_id}, conv={conversation_id[:8]}..., "
            f"topics={episode.topics}"
        )

        # 4. 向量化写入 ChromaDB (Phase 4 强化: 改为 await 以确保测试/基线的一致性)
        await self._vectorize_episode(episode)

        return episode

    async def _vectorize_episode(self, episode: EpisodicMemory) -> None:
        """将情节摘要向量化并写入 ChromaDB。"""
        try:
            vector_text = f"{episode.summary}\nTopics: {', '.join(episode.topics)}\nIntent: {episode.user_intent}"

            collection = self._get_collection()
            loop = asyncio.get_event_loop()

            await loop.run_in_executor(
                None,
                lambda: collection.upsert(
                    documents=[vector_text],
                    metadatas=[
                        {
                            "user_id": episode.user_id,
                            "conversation_id": episode.conversation_id,
                            "episode_id": episode.id,
                            "created_at_ts": int(episode.created_at.timestamp()),
                            "topics": ",".join(episode.topics),
                        }
                    ],
                    ids=[f"ep_{episode.id}"],
                ),
            )

            # 更新 PostgreSQL 中的 chroma_doc_id
            async with async_session_factory() as session:
                from sqlmodel import select

                stmt = select(EpisodicMemory).where(EpisodicMemory.id == episode.id)
                db_ep = (await session.execute(stmt)).scalar_one_or_none()
                if db_ep:
                    db_ep.chroma_doc_id = f"ep_{episode.id}"
                    session.add(db_ep)
                    await session.commit()

            logger.info(f"🔢 [EpisodicMemory] Vectorized episode {episode.id}")
        except Exception as e:
            logger.warning(f"[EpisodicMemory] Vectorization failed for {episode.id}: {e}")

    def _get_msg_field(self, m: Any, field: str) -> str:
        """Helper to get field from dict or object."""
        if isinstance(m, dict):
            return str(m.get(field, ""))
        return str(getattr(m, field, ""))

    async def _distill_conversation(self, messages: list[Any]) -> EpisodeDistillResult | None:
        """使用 LLM 对对话进行总结和提炼。"""
        if not messages:
            return None

        # 构建对话片段 (最近 20 条，内容截断避免超 Token)
        dialogue_lines = []
        total_chars = 0
        for msg in messages[-20:]:
            role = "User" if self._get_msg_field(msg, "role") == "user" else "Assistant"
            content = self._get_msg_field(msg, "content")[:400]
            line = f"{role}: {content}"
            total_chars += len(line)
            if total_chars > 6000:
                break
            dialogue_lines.append(line)

        dialogue_text = "\n".join(dialogue_lines)

        try:
            llm = get_llm_service()
            prompt = _EPISODE_SUMMARY_PROMPT.format(dialogue=dialogue_text)
            resp = await llm.chat_complete([{"role": "user", "content": prompt}], json_mode=True)
            data = json.loads(resp)
            return EpisodeDistillResult(**data)
        except Exception as e:
            logger.warning(f"[EpisodicMemory] Distillation failed: {e}")
            return None

    async def _parse_or_generate_distill(self, existing_summary: str, messages: list[dict]) -> EpisodeDistillResult | None:
        """从已有摘要中提取结构化字段。"""
        try:
            llm = get_llm_service()
            prompt = f"""
Given this conversation summary, extract structured metadata.
Return ONLY valid JSON:
{{
    "summary": "{existing_summary[:500]}",
    "key_decisions": ["decision1"],
    "topics": ["topic1", "topic2"],
    "user_intent": "one sentence intent"
}}

The summary is already written. Just fill in key_decisions, topics, user_intent.
Summary: {existing_summary}
"""
            resp = await llm.chat_complete([{"role": "user", "content": prompt}], json_mode=True)
            data = json.loads(resp)
            return EpisodeDistillResult(**data)
        except Exception:
            # Fallback
            return EpisodeDistillResult(
                summary=existing_summary[:1000],
                key_decisions=[],
                topics=[],
                user_intent="(auto-extracted)"
            )

    @staticmethod
    def _calc_topic_coverage(messages: list[Any]) -> float:
        if not messages:
            return 0.0

        def get_content(m: Any) -> str:
            if isinstance(m, dict):
                return str(m.get("content", ""))
            return str(getattr(m, "content", ""))

        avg_len = sum(len(get_content(m)) for m in messages) / len(messages)
        coverage = min(1.0, avg_len / 500) * min(1.0, len(messages) / 15)
        return round(coverage, 3)

    # ─────────────────────────────────────────────
    # 读取路径 (Read Path)
    # ─────────────────────────────────────────────

    async def recall_episodes(
        self, user_id: str, query: str, limit: int = 3, min_temperature: float = 0.1
    ) -> list[EpisodicMemory]:
        """
        跨会话的情节记忆召回。
        """
        vector_ids, pg_results = await asyncio.gather(
            self._recall_by_vector(user_id, query, limit * 2),
            self._recall_by_topics(user_id, query, limit * 2, min_temperature),
        )

        seen_ids = {e.id for e in pg_results}
        merged: list[EpisodicMemory] = list(pg_results)

        if vector_ids:
            async with async_session_factory() as session:
                from sqlmodel import select

                stmt = select(EpisodicMemory).where(EpisodicMemory.id.in_(vector_ids))
                results = await session.execute(stmt)
                for episode in results.scalars().all():
                    if episode.id not in seen_ids and episode.temperature >= min_temperature:
                        merged.append(episode)
                        seen_ids.add(episode.id)

        merged.sort(key=lambda e: e.temperature * e.topic_coverage, reverse=True)
        result = merged[:limit]

        if result:
            asyncio.create_task(self._update_recall_stats([e.id for e in result]))

        return result

    async def _recall_by_vector(self, user_id: str, query: str, limit: int) -> list[str]:
        try:
            collection = self._get_collection()
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None, lambda: collection.query(query_texts=[query], n_results=limit, where={"user_id": user_id})
            )
            if results and results.get("metadatas") and results["metadatas"][0]:
                return [m.get("episode_id", "") for m in results["metadatas"][0] if m.get("episode_id")]
        except Exception as e:
            # [M5.1.4] Robust Fallback: Continue with SQL-based retrieval if environment is broken
            # Specifically handles the frequent 'onnxruntime' missing in diverse environments.
            logger.warning(f"[EpisodicMemory] Vector recall failed: {e}. Falling back to SQL/Topic search.")
        return []

    async def _recall_by_topics(self, user_id: str, query: str, limit: int, min_temperature: float) -> list[EpisodicMemory]:
        async with async_session_factory() as session:
            from sqlmodel import desc, select

            # 1. 粗排：取出最近的高质量候选
            stmt = (
                select(EpisodicMemory)
                .where(EpisodicMemory.user_id == user_id, EpisodicMemory.temperature >= min_temperature)
                .order_by(desc(EpisodicMemory.created_at))
                .limit(limit * 5)
            )
            results = await session.execute(stmt)
            candidates = list(results.scalars().all())

        if not candidates:
            return []

        # 2. 精排：使用同义词扩展进行关键词碰撞
        from app.services.memory.smart_grep_service import _expand_with_synonyms

        expanded_query_tokens = set(_expand_with_synonyms(query))
        scored = []

        for ep in candidates:
            # 计算主题重叠度 (支持同义词碰撞)
            score = 0
            for topic in ep.topics:
                topic_lower = topic.lower()
                if any(token in topic_lower or topic_lower in token for token in expanded_query_tokens):
                    score += 1

            scored.append((score, ep))

        # 按重合得分、主题覆盖率排序
        scored.sort(key=lambda x: (x[0], x[1].topic_coverage), reverse=True)
        return [ep for _, ep in scored[:limit]]


    async def _update_recall_stats(self, episode_ids: list[str]) -> None:
        async with async_session_factory() as session:
            for ep_id in episode_ids:
                from sqlmodel import select

                stmt = select(EpisodicMemory).where(EpisodicMemory.id == ep_id)
                ep = (await session.execute(stmt)).scalar_one_or_none()
                if ep:
                    ep.recall_count += 1
                    ep.last_recalled_at = datetime.utcnow()
                    ep.temperature = min(1.0, ep.temperature + 0.1)
                    session.add(ep)
            await session.commit()

    async def format_for_context(self, episodes: list[EpisodicMemory]) -> str:
        if not episodes:
            return ""

        lines = ["--- PAST SESSIONS (Episodic Memory) ---"]
        for ep in episodes:
            date_str = ep.created_at.strftime("%Y-%m-%d")
            topics_str = ", ".join(ep.topics[:5])
            lines.append(
                f"\n[Session: {date_str} | Topics: {topics_str}]\nIntent: {ep.user_intent}\nSummary: {ep.summary[:300]}"
            )
            if ep.key_decisions:
                lines.append(f"Key Decisions: {'; '.join(ep.key_decisions[:3])}")

        return "\n".join(lines)


episodic_memory_service = EpisodicMemoryService()
