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

    async def dispatch_batch(
        self,
        file_paths: list[str],
        kb_id: str,
        description: str = "",
        doc_ids: list[str] | None = None,
        folder_paths: list[str | None] | None = None,
    ) -> str:
        """
        Takes raw inputs, creates an IngestionBatch, FileTraces, and shreds
        the workload onto Celery messaging workers immediately without blocking.

        Args:
            file_paths:   S3 key 或本地路径列表，供 Parser 读取文件
            kb_id:        知识库 ID
            description:  批次描述
            doc_ids:      与 file_paths 一一对应的数据库 Document.id 列表
            folder_paths: 与 file_paths 一一对应的原始文件夹路径列表
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
        for i, path in enumerate(file_paths):
            trace_id = str(uuid.uuid4())
            file_trace = FileTrace(id=trace_id, batch_id=batch_id, file_path=path, status=TraceStatus.PENDING)
            self.db.add(file_trace)

            payload = {
                "trace_id": trace_id,
                "document_id": path,
                "kb_id": kb_id,
                # 图谱对齐：传递 doc_id 和 folder_path
                "doc_id": doc_ids[i] if doc_ids and i < len(doc_ids) else None,
                "folder_path": folder_paths[i] if folder_paths and i < len(folder_paths) else None,
            }

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
