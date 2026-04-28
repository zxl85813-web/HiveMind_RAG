
from typing import Any, List, Optional
import asyncio
from loguru import logger
from app.core.llm import get_llm_service
from app.services.memory.episodic_service import episodic_memory_service

# [Fix-11] 并发蒸馏任务上限：防止高并发时后台任务堆积耗尽 LLM 配额
_CONSOLIDATION_SEMAPHORE = asyncio.Semaphore(10)

# [Fix-11] 低价值对话跳过蒸馏的阈值：消息数 < 此值时不蒸馏
_MIN_MESSAGES_FOR_CONSOLIDATION = 3


class MemoryConsolidator:
    """
    后台认知巩固器 (Phase 4).
    负责在会话结束后异步地提炼、去重和增强记忆。
    [Fix-11] 添加并发信号量控制 + 低价值对话过滤。
    """
    
    def __init__(self):
        self._swarm = None

    def _get_swarm(self):
        if self._swarm is None:
            try:
                from app.api.routes.agents import get_swarm
                self._swarm = get_swarm()
            except ImportError:
                logger.warning("Could not import get_swarm, reflection logic might be limited.")
        return self._swarm
    
    async def consolidate_session(
        self,
        user_id: str,
        conversation_id: str,
        messages: List[dict],
        _run_sync: bool = False,
    ):
        """
        核心合并逻辑：分析新会话，提取 Semantic 断言，并与现有 Episodic Memory 进行去重。

        [Fix-11] 两层保护：
        1. 消息数过少（< _MIN_MESSAGES_FOR_CONSOLIDATION）的低价值对话直接跳过
        2. 信号量限制最多 10 个并发蒸馏任务，防止 LLM 配额耗尽
        """
        # 低价值对话过滤：单轮简单问答不值得蒸馏
        if len(messages) < _MIN_MESSAGES_FOR_CONSOLIDATION:
            logger.debug(
                f"[Consolidator] Skipping consolidation for {conversation_id}: "
                f"only {len(messages)} messages (threshold={_MIN_MESSAGES_FOR_CONSOLIDATION})"
            )
            return

        # 信号量：如果当前已有 10 个蒸馏任务在跑，直接放弃本次（非阻塞）
        if _CONSOLIDATION_SEMAPHORE.locked() and _CONSOLIDATION_SEMAPHORE._value == 0:
            logger.warning(
                f"[Consolidator] Semaphore full, skipping consolidation for {conversation_id}"
            )
            return

        async with _CONSOLIDATION_SEMAPHORE:
            logger.info(
                f"🧠 [Consolidator] Starting consolidation for session: {conversation_id} "
                f"with {len(messages)} messages"
            )
            try:
                episode = await episodic_memory_service.store_episode(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    messages=messages,
                )

                if not episode:
                    logger.warning(
                        f"⚠️ [Consolidator] store_episode returned None (likely due to low value filter)."
                    )
                    return

                if _run_sync:
                    await episodic_memory_service._vectorize_episode(episode)

                await self._deduplicate_knowledge(user_id, episode)
                logger.info(f"✅ [Consolidator] Consolidation complete for {conversation_id}")
            except Exception as e:
                logger.error(f"❌ [Consolidator] Failed to consolidate session {conversation_id}: {e}")

    async def _deduplicate_knowledge(self, user_id: str, new_episode: Any):
        """
        简单的语义去重器示范：
        寻找与新 Episode 主题重合度高的旧记录，并进行降权或合并。
        """
        # 召回类似记录
        # 我们使用 recall_episodes 但针对 new_episode 的 intent/summary 进行查询
        query = f"{new_episode.user_intent} {' '.join(new_episode.topics)}"
        related = await episodic_memory_service.recall_episodes(
            user_id=user_id,
            query=query,
            limit=3
        )
        
        # 过滤掉自己
        related = [r for r in related if r.id != new_episode.id]
        
        if not related:
            return
            
        logger.info(f"🔍 [Consolidator] Found {len(related)} related previous episodes, performing deduplication...")
        
        # 实际上可以通过 LLM 判断是否冲突。如果冲突，旧的 "temperature" 降权。
        # 这里演示一个简单的逻辑：如果主题高度相似，旧记忆的 temperature 乘以 0.5 (加速遗忘)
        # 这就是我们在设计中提到的 "Semantic Deduplication & Intelligent Forgetting"
        
        from app.core.database import async_session_factory
        from sqlmodel import select
        from app.models.episodic import EpisodicMemory

        async with async_session_factory() as session:
            for old_ep in related:
                # 语义冲突检测（伪代码）
                # can call LLM: "Does New Episode override the facts in Old Episode?"
                stmt = select(EpisodicMemory).where(EpisodicMemory.id == old_ep.id)
                db_ep = (await session.execute(stmt)).scalar_one_or_none()
                if db_ep:
                    db_ep.temperature *= 0.8  # 适度降权旧记忆
                    db_ep.log_metadata = db_ep.extra or {}
                    db_ep.extra["deduplication_source"] = new_episode.id
                    session.add(db_ep)
            await session.commit()

consolidator = MemoryConsolidator()
