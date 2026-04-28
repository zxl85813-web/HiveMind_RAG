import json
from loguru import logger
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.observability import AgentSpan
from app.core.redis import get_redis_client

from app.core.celery_app import celery_app

@celery_app.task
def flush_trace_buffer():
    """
    Consumer task for trace_span_buffer in Redis.
    Pops spans and bulk-inserts them into PostgreSQL.
    """
    redis_client = get_redis_client()
    
    # Attempt to pop up to 100 items at once for bulk insertion
    spans_to_insert = []
    
    # Use LPOP to non-blockingly drain the buffer (or a limited number of items)
    # We use a loop to grab a batch
    for _ in range(100):
        raw = redis_client.rpop("trace_span_buffer")
        if not raw:
            break
        try:
            span_data = json.loads(raw)
            # Ensure trace_id is present (Agent Architecture Gate)
            if "trace_id" in span_data:
                spans_to_insert.append(AgentSpan(**span_data))
        except Exception as e:
            logger.error(f"Failed to parse trace span from Redis: {e}")

    if not spans_to_insert:
        return 0

    db: Session = SessionLocal()
    try:
        db.bulk_save_objects(spans_to_insert)
        db.commit()
        logger.info(f"🛰️ [Observability] Flushed {len(spans_to_insert)} spans to database.")
        return len(spans_to_insert)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to commit trace spans to database: {e}")
        # P3: Re-queue failed items? For now, we log and drop to avoid loop issues
        return 0
    finally:
        db.close()


@celery_app.task(
    name="app.services.observability.tasks.llm_quota_daily_report",
    rate_limit="1/h",
    ignore_result=True,
)
def llm_quota_daily_report():
    """
    LLM 配额日报任务（每天 08:00 UTC 由 Beat 触发）。

    统计过去 24 小时的 LLM 调用情况：
      - 各模型调用次数 / Token 消耗 / 费用估算
      - ingestion_queue 积压量
      - 如果消耗超过 BUDGET_DAILY_LIMIT_USD 的 80%，输出告警日志

    输出到日志，可通过 Grafana / ELK 采集告警。
    """
    import asyncio
    from datetime import datetime, timedelta, UTC

    async def _report():
        from sqlmodel import select, func
        from app.core.database import async_session_factory
        from app.models.observability import LLMMetric
        from app.core.celery_app import get_queue_stats

        since = datetime.now(UTC) - timedelta(hours=24)

        async with async_session_factory() as session:
            # 按模型聚合
            stmt = (
                select(
                    LLMMetric.model_name,
                    func.count(LLMMetric.id).label("calls"),
                    func.sum(LLMMetric.tokens_input + LLMMetric.tokens_output).label("total_tokens"),
                    func.sum(LLMMetric.cost).label("total_cost"),
                    func.avg(LLMMetric.latency_ms).label("avg_latency_ms"),
                    func.sum(LLMMetric.is_error.cast(int)).label("errors"),
                )
                .where(LLMMetric.created_at >= since)
                .group_by(LLMMetric.model_name)
            )
            res = await session.execute(stmt)
            rows = res.all()

        total_cost = sum(r.total_cost or 0 for r in rows)
        total_calls = sum(r.calls or 0 for r in rows)
        total_errors = sum(r.errors or 0 for r in rows)

        # 队列积压
        queue_stats = get_queue_stats()

        # 输出日报
        logger.info(
            f"📊 [LLM Quota Daily Report] "
            f"calls={total_calls}, cost=${total_cost:.4f}, "
            f"errors={total_errors}, queues={queue_stats}"
        )
        for r in rows:
            logger.info(
                f"  └─ {r.model_name}: calls={r.calls}, "
                f"tokens={r.total_tokens}, cost=${r.total_cost:.4f}, "
                f"avg_latency={r.avg_latency_ms:.0f}ms, errors={r.errors}"
            )

        # 配额告警
        daily_limit = settings.BUDGET_DAILY_LIMIT_USD
        alert_threshold = settings.BUDGET_ALERT_THRESHOLD
        if total_cost >= daily_limit * alert_threshold:
            logger.warning(
                f"⚠️ [LLM Quota Alert] Daily cost ${total_cost:.4f} "
                f"exceeds {alert_threshold*100:.0f}% of limit ${daily_limit:.2f}. "
                f"Consider reducing CELERY_INGESTION_RATE_LIMIT."
            )

        # ingestion 队列积压告警
        ingestion_backlog = queue_stats.get("ingestion_queue", 0)
        if ingestion_backlog > 100:
            logger.warning(
                f"⚠️ [Queue Alert] ingestion_queue backlog={ingestion_backlog}. "
                f"Consider increasing CELERY_WORKER_CONCURRENCY or reducing batch size."
            )

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    loop.run_until_complete(_report())
