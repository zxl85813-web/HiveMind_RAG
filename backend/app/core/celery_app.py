"""
Celery 配置 — HiveMind Swarm Workers

限速策略（防止 LLM API 配额耗尽）：
  ingestion_queue   : CELERY_INGESTION_RATE_LIMIT（默认 10/m）
  maintenance_queue : CELERY_MAINTENANCE_RATE_LIMIT（默认 2/m）

限速实现层次：
  1. Task 级 rate_limit（本文件 task_annotations）— Celery 内置令牌桶，worker 侧执行
  2. Worker prefetch_multiplier=1 — 防止单 worker 囤积大量任务
  3. worker_concurrency 可配置 — 控制并行度上限

Beat 调度：
  memory-decay-daily          每天 03:00 UTC 执行内存温度衰减
  observability-flush         每 10s 刷新 trace buffer
  llm-quota-daily-report      每天 08:00 UTC 输出 LLM 配额日报
"""

from celery import Celery
from celery.schedules import crontab
from celery.utils.log import get_task_logger

from app.core.config import settings

logger = get_task_logger(__name__)

# ── 初始化 ────────────────────────────────────────────────────────────────────

celery_app = Celery(
    "hivemind_swarm",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.services.ingestion.tasks",
        "app.services.memory.tasks",
        "app.services.observability.tasks",
    ],
)

# ── 核心配置 ──────────────────────────────────────────────────────────────────

celery_app.conf.update(
    # 序列化
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # ── Worker 并发控制 ──────────────────────────────────────────────────────
    # prefetch_multiplier=1：每次只预取 1 个任务
    #   - 防止大任务（LLM 调用）堆积在单个 worker，导致其他 worker 空闲
    #   - 配合 rate_limit 实现精确的令牌桶限速
    worker_prefetch_multiplier=settings.CELERY_WORKER_PREFETCH_MULTIPLIER,
    worker_concurrency=settings.CELERY_WORKER_CONCURRENCY,

    # ── 超时保护 ─────────────────────────────────────────────────────────────
    task_soft_time_limit=300,   # 5 分钟软超时：触发 SoftTimeLimitExceeded，任务可清理
    task_time_limit=360,        # 6 分钟硬超时：强制 kill

    # ── 任务路由 ─────────────────────────────────────────────────────────────
    task_routes={
        "app.services.ingestion.tasks.process_document_chunk": {"queue": "ingestion_queue"},
        "app.services.ingestion.tasks.review_data_fallback":   {"queue": "hitl_queue"},
        "app.services.memory.tasks.decay_memory":              {"queue": "maintenance_queue"},
        "app.services.observability.tasks.flush_trace_buffer": {"queue": "maintenance_queue"},
        "app.services.observability.tasks.llm_quota_daily_report": {"queue": "maintenance_queue"},
    },

    # ── 任务级限速（令牌桶，worker 侧执行）──────────────────────────────────
    # 格式: "N/s" | "N/m" | "N/h"
    # 这里作为默认值，task 装饰器上的 rate_limit 会覆盖此处
    task_annotations={
        "app.services.ingestion.tasks.process_document_chunk": {
            "rate_limit": settings.CELERY_INGESTION_RATE_LIMIT,
            # 重试配置：指数退避，最多 3 次
            "max_retries": settings.CELERY_MAX_RETRIES,
            "default_retry_delay": settings.CELERY_RETRY_BACKOFF_BASE,
        },
        "app.services.memory.tasks.decay_memory": {
            "rate_limit": settings.CELERY_MAINTENANCE_RATE_LIMIT,
        },
        "app.services.observability.tasks.flush_trace_buffer": {
            "rate_limit": "6/m",   # 每 10s 一次，限速 6/m 防止 Redis 压力
        },
        "app.services.observability.tasks.llm_quota_daily_report": {
            "rate_limit": "1/h",   # 日报任务，严格限速
        },
    },

    # ── Beat 定时调度 ─────────────────────────────────────────────────────────
    beat_schedule={
        # 内存温度衰减（每天凌晨低峰期执行）
        "memory-decay-daily": {
            "task": "app.services.memory.tasks.decay_memory",
            "schedule": crontab(
                hour=settings.CELERY_MEMORY_DECAY_HOUR,
                minute=settings.CELERY_MEMORY_DECAY_MINUTE,
            ),
            "kwargs": {"decay_rate": 0.95, "eviction_threshold": 0.05},
            "options": {"queue": "maintenance_queue"},
        },

        # 可观测性 trace buffer 刷新（高频，轻量）
        "observability-flush-trace-buffer": {
            "task": "app.services.observability.tasks.flush_trace_buffer",
            "schedule": settings.CELERY_OBS_FLUSH_INTERVAL,
            "options": {"queue": "maintenance_queue"},
        },

        # LLM 配额日报（每天 08:00 UTC，帮助发现配额超用风险）
        "llm-quota-daily-report": {
            "task": "app.services.observability.tasks.llm_quota_daily_report",
            "schedule": crontab(
                hour=settings.CELERY_LLM_QUOTA_REPORT_HOUR,
                minute=settings.CELERY_LLM_QUOTA_REPORT_MINUTE,
            ),
            "options": {"queue": "maintenance_queue"},
        },
    },
)

# ── 运行时限速热更新 ──────────────────────────────────────────────────────────

def update_ingestion_rate_limit(new_rate: str) -> None:
    """
    运行时动态调整 ingestion 任务限速，无需重启 worker。

    用法：
        from app.core.celery_app import update_ingestion_rate_limit
        update_ingestion_rate_limit("5/m")   # 降速，LLM 配额告急时
        update_ingestion_rate_limit("20/m")  # 提速，配额充足时

    原理：Celery 支持通过 control.rate_limit() 向所有 worker 广播新限速。
    """
    celery_app.control.rate_limit(
        "app.services.ingestion.tasks.process_document_chunk",
        new_rate,
    )
    logger.info(f"[RateLimit] ingestion_queue rate limit updated to {new_rate}")


def get_queue_stats() -> dict:
    """
    获取各队列的当前积压情况（用于监控告警）。
    需要 Redis 作为 broker。
    """
    try:
        from app.core.redis import get_redis_client
        r = get_redis_client()
        queues = ["ingestion_queue", "hitl_queue", "maintenance_queue"]
        return {q: r.llen(q) for q in queues if hasattr(r, "llen")}
    except Exception as e:
        logger.warning(f"[QueueStats] Failed to get queue stats: {e}")
        return {}
