"""
P2 — 记忆衰减定时任务 (Memory Decay Periodic Task).

每日由 Celery Beat 调度，对 Tier-1 InMemoryAbstractIndex 执行：
  1. apply_decay  — 对全量热度乘以衰减系数 (default: 0.95)
  2. evict_cold   — 移除热度低于阈值的冷数据条目

Tasks are intentionally sync (Celery default) to avoid asyncio bridge overhead.
"""

from loguru import logger

from app.core.celery_app import celery_app


@celery_app.task(name="app.services.memory.tasks.decay_memory", bind=True, max_retries=2)
def decay_memory(self, decay_rate: float = 0.95, eviction_threshold: float = 0.05) -> dict:
    """
    P2: 每日记忆热度衰减 + 冷数据驱逐任务。

    Args:
        decay_rate: 衰减系数 (0.0-1.0)。每天乘以该系数，越小遗忘越快。
        eviction_threshold: 低于此热度值的条目将被彻底删除。

    Returns:
        dict: 执行摘要，包含衰减并驱逐的条目数量。
    """
    try:
        from app.services.memory.tier.abstract_index import abstract_index

        stats_before = abstract_index.get_stats()
        below = abstract_index.apply_decay(decay_rate=decay_rate)
        evicted = abstract_index.evict_cold(threshold=eviction_threshold)
        stats_after = abstract_index.get_stats()

        result = {
            "status": "success",
            "decay_rate": decay_rate,
            "entries_before": stats_before["total_entries"],
            "entries_after": stats_after["total_entries"],
            "evicted": evicted,
            "below_threshold_before_eviction": below,
            "avg_temperature_after": stats_after["avg_temperature"],
        }
        logger.info(f"✅ [MemoryDecay] Task completed: {result}")
        return result

    except Exception as exc:
        logger.error(f"❌ [MemoryDecay] Task failed: {exc}")
        raise self.retry(exc=exc, countdown=60)
