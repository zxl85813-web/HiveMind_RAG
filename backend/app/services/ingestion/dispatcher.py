"""
Task Sharding Dispatcher (V3 Architecture).

Replaces the legacy, blocking `IngestionExecutor`.
Breaks large batches of files into isolated fragment tasks
and dumps them into Celery/Redis for extreme parallel scaling.
"""

import uuid

from loguru import logger

from app.core.celery_app import celery_app
from app.models.observability import FileTrace, IngestionBatch, TraceStatus
from app.services.ingestion.swarm.governance import SwarmCircuitBreaker


class IngestionDispatcher:
    """
    Shards massive ingest tasks and routes them to Celery.
    Maintains initial tracing records in DB (via FileTrace and IngestionBatch).
    """

    def __init__(self, db_session):
        self.db = db_session

    async def dispatch_batch(self, file_paths: list[str], kb_id: str, description: str = "") -> str:
        """
        Takes raw inputs, creates an IngestionBatch, FileTraces, and shreds
        the workload onto Celery messaging workers immediately without blocking.
        """
        batch_id = str(uuid.uuid4())

        logger.info(f"🚀 [Dispatcher] Creating new massive batch: {batch_id} with {len(file_paths)} tasks.")

        # 0. Check Circuit Breaker before sharding (Governance)
        cb = SwarmCircuitBreaker(kb_id=kb_id)
        if not cb.is_available():
            logger.error(f"🔴 [Dispatcher] Swarm Circuit OPEN for KB {kb_id}. Skipping ingestion.")
            raise Exception(f"Swarm ingestion for KB {kb_id} is temporarily disabled due to high failure rates.")

        # 1. Create overarching batch observability record

        batch_record = IngestionBatch(id=batch_id, description=description, total_files=len(file_paths))
        self.db.add(batch_record)

        # 2. Shred tasks (Sharding) -> 1 File = 1 FileTrace = 1 Celery Task
        tasks_enqueued = 0
        for path in file_paths:
            # Create a localized trace block
            trace_id = str(uuid.uuid4())
            file_trace = FileTrace(id=trace_id, batch_id=batch_id, file_path=path, status=TraceStatus.PENDING)
            self.db.add(file_trace)

            # Send shredded task to message broker (Redis/Celery)
            payload = {
                "trace_id": trace_id,
                "document_id": path,  # Map as document_id temporarily
                "kb_id": kb_id,
            }

            # celery_app.send_task puts the workload onto Redis, instantly unblocking API server
            celery_app.send_task(
                "app.services.ingestion.tasks.process_document_chunk", args=[payload], queue="ingestion_queue"
            )
            tasks_enqueued += 1

        await self.db.commit()
        logger.info(f"✅ [Dispatcher] Successfully shattered {tasks_enqueued} task segments onto Redis cluster!")

        return batch_id

    async def get_batch_progress(self, batch_id: str) -> dict:
        """Lightweight check on sharded task progress."""

        # Pull overarching batch record
        batch = await self.db.get(IngestionBatch, batch_id)
        if not batch:
            return {"status": "Not Found"}

        # Optional: You can derive success via counting traces, but usually
        # completed tasks increment IngestionBatch.completed_files directly
        # via a background observer hook.
        return {
            "batch_id": batch.id,
            "total_files": batch.total_files,
            "completed_files": batch.completed_files,
            "failed_files": batch.failed_files,
            "status": "completed" if batch.completed_files + batch.failed_files == batch.total_files else "processing",
        }
