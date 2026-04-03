import json
from loguru import logger
from redis import Redis
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.observability import AgentSpan

from app.core.celery_app import celery_app

@celery_app.task
def flush_trace_buffer():
    """
    Consumer task for trace_span_buffer in Redis.
    Pops spans and bulk-inserts them into PostgreSQL.
    """
    redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    
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
