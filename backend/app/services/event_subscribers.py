"""
Event Subscribers — M9.3.1 / M9.3.2
====================================
为 WriteEventBus 和 Blackboard 添加后端订阅者，修复事件驱动断链。

订阅者:
  1. CacheInvalidationSubscriber — 知识库变更时清除相关 RAG 缓存
  2. GraphUpdateSubscriber       — 知识库变更时触发图谱增量索引
  3. BlackboardInsightSubscriber  — 将 telemetry insights 注入 Supervisor 上下文

启动方式:
  在 app.main 的 lifespan 中调用 start_event_subscribers()
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from loguru import logger

from app.core.config import settings

_EVENT_CHANNEL = "hivemind:kb_write_events"
_subscriber_task: asyncio.Task | None = None


# ── M9.3.1: WriteEventBus 后端订阅者 ─────────────────────────────────────────

async def _handle_kb_write_event(event: dict[str, Any]) -> None:
    """
    处理知识库写事件。

    event 结构:
      {
        "event_type": "document_uploaded" | "document_deleted" | "kb_updated" | ...,
        "kb_id": "...",
        "doc_id": "..." | null,
        "payload": {...},
        "timestamp": "..."
      }
    """
    event_type = event.get("event_type", "unknown")
    kb_id = event.get("kb_id", "")
    doc_id = event.get("doc_id")

    logger.info(f"[EventSubscriber] Received: {event_type} kb={kb_id} doc={doc_id}")

    # ── CacheInvalidationSubscriber ───────────────────────────────────────
    try:
        await _invalidate_rag_cache(kb_id, doc_id, event_type)
    except Exception as e:
        logger.warning(f"[CacheInvalidation] Failed: {e}")

    # ── GraphUpdateSubscriber ─────────────────────────────────────────────
    try:
        await _trigger_graph_update(kb_id, doc_id, event_type)
    except Exception as e:
        logger.warning(f"[GraphUpdate] Failed: {e}")


async def _invalidate_rag_cache(kb_id: str, doc_id: str | None, event_type: str) -> None:
    """
    M9.3.1a: 知识库变更时清除相关 RAG 缓存。

    策略:
      - document_uploaded / document_deleted → 清除该 kb_id 的检索缓存
      - kb_updated → 清除该 kb_id 的所有缓存
    """
    if event_type in ("document_uploaded", "document_deleted", "kb_updated", "document_updated"):
        try:
            from app.core.redis import get_redis_client

            redis = get_redis_client()
            # 清除该知识库的检索缓存（key 格式: rag_cache:{kb_id}:*）
            cache_pattern = f"rag_cache:{kb_id}:*"
            # 使用 SCAN 避免阻塞
            cursor = 0
            deleted = 0
            while True:
                cursor, keys = await redis.scan(cursor, match=cache_pattern, count=100)
                if keys:
                    await redis.delete(*keys)
                    deleted += len(keys)
                if cursor == 0:
                    break

            if deleted:
                logger.info(f"[CacheInvalidation] Cleared {deleted} cache entries for kb={kb_id}")
        except Exception as e:
            # Redis 不可用时静默降级
            logger.debug(f"[CacheInvalidation] Redis unavailable: {e}")


async def _trigger_graph_update(kb_id: str, doc_id: str | None, event_type: str) -> None:
    """
    M9.3.1b: 知识库变更时触发图谱增量索引。

    仅在文档上传/删除时触发，避免频繁索引。
    """
    if event_type not in ("document_uploaded", "document_deleted"):
        return

    try:
        from app.sdk.core.graph_store import get_graph_store

        store = get_graph_store()

        if event_type == "document_uploaded" and doc_id:
            # 在图谱中创建/更新文档节点
            await store.execute_query(
                "MERGE (d:Document {id: $doc_id}) "
                "SET d.kb_id = $kb_id, d.updated_at = timestamp()",
                {"doc_id": doc_id, "kb_id": kb_id},
            )
            logger.info(f"[GraphUpdate] Document node upserted: {doc_id}")

        elif event_type == "document_deleted" and doc_id:
            # 标记文档节点为已删除（不物理删除，保留审计链路）
            await store.execute_query(
                "MATCH (d:Document {id: $doc_id}) SET d.is_deleted = true, d.deleted_at = timestamp()",
                {"doc_id": doc_id},
            )
            logger.info(f"[GraphUpdate] Document node marked deleted: {doc_id}")

    except Exception as e:
        logger.debug(f"[GraphUpdate] Graph write skipped: {e}")


# ── M9.3.2: Blackboard Insight 订阅者 ────────────────────────────────────────

# 全局 insight 缓冲区，SupervisorAgent 可以读取
_latest_insights: list[dict[str, Any]] = []
_MAX_INSIGHTS = 20


def get_latest_insights() -> list[dict[str, Any]]:
    """供 SupervisorAgent 调用，获取最近的系统 insights。"""
    return list(_latest_insights)


def push_insight(insight: dict[str, Any]) -> None:
    """
    M9.3.2: 将 telemetry insight 推入缓冲区。

    由 Blackboard 或其他 telemetry 源调用。
    SupervisorAgent 在 _plan() 阶段可以读取这些 insights。
    """
    _latest_insights.append(insight)
    # 保持缓冲区大小
    while len(_latest_insights) > _MAX_INSIGHTS:
        _latest_insights.pop(0)


# ── Redis 订阅循环 ────────────────────────────────────────────────────────────

async def _redis_subscriber_loop() -> None:
    """
    后台任务：订阅 Redis 频道，分发事件到各订阅者。
    """
    try:
        import redis.asyncio as aioredis
    except ImportError:
        logger.warning("[EventSubscriber] redis.asyncio not available. Subscribers disabled.")
        return

    while True:
        try:
            client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            pubsub = client.pubsub()
            await pubsub.subscribe(_EVENT_CHANNEL)

            logger.info(f"[EventSubscriber] Subscribed to Redis channel: {_EVENT_CHANNEL}")

            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    event = json.loads(message["data"])
                    await _handle_kb_write_event(event)
                except json.JSONDecodeError:
                    logger.debug("[EventSubscriber] Invalid JSON in event")
                except Exception as e:
                    logger.warning(f"[EventSubscriber] Handler error: {e}")

        except Exception as e:
            logger.warning(f"[EventSubscriber] Redis connection lost: {e}. Reconnecting in 10s...")
            await asyncio.sleep(10)


async def start_event_subscribers() -> None:
    """
    启动事件订阅者后台任务。

    在 app.main 的 lifespan 中调用:
        await start_event_subscribers()
    """
    global _subscriber_task
    if _subscriber_task is not None:
        return

    _subscriber_task = asyncio.create_task(_redis_subscriber_loop())
    logger.info("[EventSubscriber] Background subscriber started.")


async def stop_event_subscribers() -> None:
    """停止事件订阅者。"""
    global _subscriber_task
    if _subscriber_task:
        _subscriber_task.cancel()
        _subscriber_task = None
        logger.info("[EventSubscriber] Background subscriber stopped.")
