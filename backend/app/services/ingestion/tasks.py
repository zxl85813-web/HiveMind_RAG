"""
Celery Task Definitions for V3 Swarm Ingestion.

Distributed workers will pick up tasks from here and trigger the Native Langgraph Swarm.
"""

import asyncio
from typing import Any

from celery import shared_task
from loguru import logger


# Lazy imports for the heavy swarm mechanisms
class SwarmRunner:
    @staticmethod
    async def process_document(document_id: str, trace_id: str, kb_id: str) -> dict[str, Any]:
        """Async core for processing a document using the V3 Swarm."""
        from app.services.ingestion.swarm.orchestrator import IngestionOrchestrator

        logger.info(f"[Worker] Invoking Swarm orchestrator for doc_id: {document_id} [trace: {trace_id}]")

        orchestrator = IngestionOrchestrator(trace_id=trace_id, kb_id=kb_id)
        result = await orchestrator.run(document_id)

        return {
            "status": "success" if result.get("audit_verdict") == "PASS" else "flagged",
            "confidence": result.get("confidence_score", 0.0),
            "verdict": result.get("audit_verdict"),
            "raw_text": result.get("raw_text", ""),
            "sections": result.get("sections", []),
        }


@shared_task(
    name="app.services.ingestion.tasks.process_document_chunk", bind=True, max_retries=3, default_retry_delay=30
)
def process_document_chunk(self, task_payload: dict):
    """
    Worker Entrypoint. Receives highly shredded task fragments.
    Calls LangGraph explicitly within a safe loop.
    """
    document_id = task_payload.get("document_id")
    kb_id = task_payload.get("kb_id")
    trace_id = task_payload.get("trace_id", "unknown")

    logger.info(f"[Celery] Received sharded document task: {document_id}")

    try:
        # We must bridge sync Celery with Async LangGraph
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    try:
        # Run Swarm
        result = loop.run_until_complete(SwarmRunner.process_document(document_id, trace_id, kb_id))

        # Async DB update
        async def update_obs():
            from sqlmodel import select

            from app.core.database import async_session_factory
            from app.models.observability import FileTrace, HITLTask, TraceStatus
            from app.services.ingestion.swarm.governance import SwarmCircuitBreaker

            async with async_session_factory() as session:
                # 1. Update Trace Status
                stmt = select(FileTrace).where(FileTrace.id == trace_id)
                res = await session.execute(stmt)
                trace = res.scalars().first()
                if trace:
                    if result.get("status") == "flagged" or result.get("confidence", 1.0) < 0.8:
                        trace.status = TraceStatus.PENDING_REVIEW
                        # 2. Create HITL Task
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
                        # 3. Record Success (Governance)
                        SwarmCircuitBreaker(kb_id=kb_id).record_success()

                    # Store result summary
                    trace.result_data = {"raw_text": result.get("raw_text"), "sections": result.get("sections")}
                    trace.kb_id = kb_id
                    trace.doc_id = document_id

                    await session.commit()

        loop.run_until_complete(update_obs())
        return result
    except Exception as exc:
        logger.error(f"[Circuit Breaker] Task {document_id} failed abruptly: {exc}")

        # Record failure for the KB (Governance)
        from app.services.ingestion.swarm.governance import SwarmCircuitBreaker

        SwarmCircuitBreaker(kb_id=kb_id).record_failure()

        # Retry with exponential backoff on transient errors
        raise self.retry(exc=exc)
