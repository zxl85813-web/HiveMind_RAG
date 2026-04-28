"""
Celery Task Definitions for V3 Swarm Ingestion.

限速说明：
  - rate_limit 由 celery_app.conf.task_annotations 统一管理（默认 10/m）
  - 可通过 update_ingestion_rate_limit() 运行时热更新
  - 重试采用指数退避：第 1 次 30s，第 2 次 60s，第 3 次 120s
"""

import asyncio
from typing import Any

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from app.core.logging import get_trace_logger
from app.core.config import settings

logger = get_trace_logger("ingestion.tasks")


# Lazy imports for the heavy swarm mechanisms
class SwarmRunner:
    @staticmethod
    async def process_document(
        document_id: str,
        trace_id: str,
        kb_id: str,
        doc_id: str | None = None,
        folder_path: str | None = None,
    ) -> dict[str, Any]:
        """Async core for processing a document using the V3 Swarm.

        Args:
            document_id: file_path（S3 key 或本地路径），供 Parser 读取
            trace_id:    可观测性追踪 ID
            kb_id:       知识库 ID
            doc_id:      数据库 Document.id，用于图谱节点（缺省时降级为 document_id）
            folder_path: 原始文件夹路径，写入图谱保留目录结构
        """
        from app.services.ingestion.swarm.orchestrator import IngestionOrchestrator

        logger.info(f"[Worker] Invoking Swarm orchestrator for doc_id: {doc_id or document_id} [trace: {trace_id}]")

        orchestrator = IngestionOrchestrator(trace_id=trace_id, kb_id=kb_id)
        result = await orchestrator.run(
            file_path=document_id,
            doc_id=doc_id,
            folder_path=folder_path,
        )

        return {
            "status": "success" if result.get("audit_verdict") == "PASS" else "flagged",
            "confidence": result.get("confidence_score", 0.0),
            "verdict": result.get("audit_verdict"),
            "raw_text": result.get("raw_text", ""),
            "sections": result.get("sections", []),
        }


@shared_task(
    name="app.services.ingestion.tasks.process_document_chunk",
    bind=True,
    # rate_limit 由 celery_app.conf.task_annotations 统一管理
    # 此处设置兜底值，task_annotations 会覆盖它
    rate_limit=settings.CELERY_INGESTION_RATE_LIMIT,
    max_retries=settings.CELERY_MAX_RETRIES,
    # 指数退避：countdown = base * 2^(retries-1)
    # 第 1 次: 30s, 第 2 次: 60s, 第 3 次: 120s
    default_retry_delay=settings.CELERY_RETRY_BACKOFF_BASE,
    # 软超时触发 SoftTimeLimitExceeded，任务可以做清理
    soft_time_limit=300,
    time_limit=360,
    # 任务结果保留 1 小时（用于进度查询）
    result_expires=3600,
    # 忽略结果（不写 Redis backend），减少 Redis 压力
    # 注意：如果需要 AsyncResult 查询，改为 False
    ignore_result=False,
    # 任务 ack 在执行完成后（而非取出时），防止 worker crash 导致任务丢失
    acks_late=True,
    # worker 崩溃时重新入队
    reject_on_worker_lost=True,
)
def process_document_chunk(self, task_payload: dict):
    """
    Worker Entrypoint. Receives highly shredded task fragments.
    Calls LangGraph explicitly within a safe loop.

    限速：由 task_annotations 中的 rate_limit 控制（默认 10/m）。
    重试：指数退避，第 N 次等待 base * 2^(N-1) 秒。
    """
    document_id = task_payload.get("document_id")
    kb_id = task_payload.get("kb_id")
    trace_id = task_payload.get("trace_id", "unknown")
    doc_id = task_payload.get("doc_id")
    folder_path = task_payload.get("folder_path")

    logger.info(
        f"[Celery] Task received: {document_id} (doc_id={doc_id}, "
        f"retry={self.request.retries}/{settings.CELERY_MAX_RETRIES})"
    )

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(
            SwarmRunner.process_document(
                document_id=document_id,
                trace_id=trace_id,
                kb_id=kb_id,
                doc_id=doc_id,
                folder_path=folder_path,
            )
        )

        # Async DB update
        async def update_obs():
            from sqlmodel import select

            from app.core.database import async_session_factory
            from app.models.observability import FileTrace, HITLTask, TraceStatus
            from app.services.ingestion.swarm.governance import SwarmCircuitBreaker
            from app.services.ingestion.progress_service import publish_progress

            async with async_session_factory() as session:
                # 1. Update Trace Status
                stmt = select(FileTrace).where(FileTrace.id == trace_id)
                res = await session.execute(stmt)
                trace = res.scalars().first()
                if trace:
                    is_flagged = (
                        result.get("status") == "flagged"
                        or result.get("confidence", 1.0) < 0.8
                    )
                    if is_flagged:
                        trace.status = TraceStatus.PENDING_REVIEW
                        hitl = HITLTask(
                            trace_id=trace_id,
                            extracted_data={
                                "verdict": result.get("verdict"),
                                "raw_text": result.get("raw_text"),
                                "sections": result.get("sections"),
                            },
                            reason="low_confidence" if result.get("confidence", 1.0) < 0.8 else "flagged_by_swarm",
                        )
                        session.add(hitl)
                        logger.warning(f"🚩 [HITL] Document {document_id} flagged for review.")
                    else:
                        trace.status = TraceStatus.SUCCESS
                        SwarmCircuitBreaker(kb_id=kb_id).record_success()

                    trace.result_data = {"raw_text": result.get("raw_text"), "sections": result.get("sections")}
                    trace.kb_id = kb_id
                    trace.doc_id = document_id
                    await session.commit()

                    # 2. 统计批次进度并发布 SSE 事件
                    if trace.batch_id:
                        from sqlmodel import func
                        from app.models.observability import IngestionBatch

                        batch = await session.get(IngestionBatch, trace.batch_id)
                        if batch:
                            # 实时统计（不依赖 batch.completed_files 计数器，避免并发竞争）
                            count_stmt = (
                                select(FileTrace.status, func.count(FileTrace.id).label("cnt"))
                                .where(FileTrace.batch_id == trace.batch_id)
                                .group_by(FileTrace.status)
                            )
                            count_res = await session.execute(count_stmt)
                            counts = {row.status: row.cnt for row in count_res}

                            done = counts.get(TraceStatus.SUCCESS, 0)
                            failed_cnt = (
                                counts.get(TraceStatus.FAILED, 0)
                                + counts.get(TraceStatus.PENDING_REVIEW, 0)
                            )
                            event_type = "file_failed" if is_flagged else "file_done"

                            # 同步发布（Celery 是同步上下文）
                            publish_progress(
                                batch_id=trace.batch_id,
                                event=event_type,
                                total=batch.total_files,
                                completed=done,
                                failed=failed_cnt,
                                doc_id=doc_id,
                                filename=document_id.split("/")[-1] if document_id else None,
                                folder_path=folder_path,
                            )

                            # 如果全部完成，发布 batch_done
                            if done + failed_cnt >= batch.total_files:
                                publish_progress(
                                    batch_id=trace.batch_id,
                                    event="batch_done",
                                    total=batch.total_files,
                                    completed=done,
                                    failed=failed_cnt,
                                    message=f"批次处理完成：{done} 成功，{failed_cnt} 失败",
                                )

        loop.run_until_complete(update_obs())
        return result
    except SoftTimeLimitExceeded:
        # 软超时：任务运行超过 5 分钟，记录失败并不重试（避免无限占用 worker）
        logger.error(f"[Timeout] Task {document_id} exceeded soft time limit, marking as failed")
        from app.services.ingestion.swarm.governance import SwarmCircuitBreaker
        SwarmCircuitBreaker(kb_id=kb_id).record_failure()
        # 不 raise self.retry，直接返回失败状态
        return {"status": "timeout", "document_id": document_id}
    except Exception as exc:
        logger.error(f"[Celery] Task {document_id} failed: {exc} (retry {self.request.retries})")

        # 记录熔断器失败
        from app.services.ingestion.swarm.governance import SwarmCircuitBreaker
        SwarmCircuitBreaker(kb_id=kb_id).record_failure()

        # 指数退避重试：base * 2^(retries) 秒
        # retries=0 → 30s, retries=1 → 60s, retries=2 → 120s
        backoff = settings.CELERY_RETRY_BACKOFF_BASE * (2 ** self.request.retries)
        logger.warning(
            f"[Celery] Retrying {document_id} in {backoff}s "
            f"({self.request.retries + 1}/{settings.CELERY_MAX_RETRIES})"
        )
        raise self.retry(exc=exc, countdown=backoff)
