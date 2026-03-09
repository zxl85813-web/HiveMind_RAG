"""
Celery configuration for the Swarm workers (V3 Ingestion).
Uses Redis as both the message broker and backend.
"""

from celery import Celery

from app.core.config import settings

# Initialize Celery app
celery_app = Celery(
    "hivemind_swarm", broker=settings.REDIS_URL, backend=settings.REDIS_URL, include=["app.services.ingestion.tasks"]
)

celery_app.conf.update(
    # Optimize for high-throughput micro-tasks
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Pre-fetching & worker concurrency tuning for IO-bound LangGraph workloads
    worker_prefetch_multiplier=4,
    worker_concurrency=8,  # Scale out depending on deployment
    # Timeouts for circuit breaking
    task_soft_time_limit=300,  # 5 minutes max per swarm task
    task_time_limit=360,  # Hard limit
    # Route specifics
    task_routes={
        "app.services.ingestion.tasks.process_document_chunk": {"queue": "ingestion_queue"},
        "app.services.ingestion.tasks.review_data_fallback": {"queue": "hitl_queue"},
    },
)
