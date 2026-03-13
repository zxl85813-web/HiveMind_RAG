"""
Indexing Service — Handles background parsing and vectorization using the Pipeline Engine.

所属模块: services
依赖模块: core.vector_store, batch.ingestion.executor, models.knowledge
注册位置: REGISTRY.md > Services > IndexingService
"""

from loguru import logger

from app.core.database import async_session_factory
from app.models.knowledge import Document, KnowledgeBase, KnowledgeBaseDocumentLink


async def index_document_task(kb_id: str, doc_id: str):
    """
    Background task to parse and index a document using the Flexible Pipeline Engine.
    """
    logger.info(f"🚀 [Pipeline] Starting task: Doc {doc_id} -> KB {kb_id}")

    async with async_session_factory() as session:
        # 1. Initialization
        link = await session.get(KnowledgeBaseDocumentLink, (kb_id, doc_id))
        if not link:
            logger.error(f"Link not found for KB {kb_id}, Doc {doc_id}")
            return

        doc = await session.get(Document, doc_id)
        kb = await session.get(KnowledgeBase, kb_id)
        if not doc or not kb:
            logger.error(f"Document {doc_id} or KB {kb_id} not found")
            link.status = "failed"
            session.add(link)
            await session.commit()
            return

        try:
            # 2. V3 Dispatcher (Extreme Parallelism & Swarm Orchestration)
            logger.info(f"🧠 [V3 Refactor] Dispatching Doc {doc_id} to Native Swarm...")

            from app.services.ingestion.dispatcher import IngestionDispatcher

            # Use a separate AsyncSession for the dispatcher to avoid session conflicts
            async with async_session_factory() as async_db:
                dispatcher = IngestionDispatcher(async_db)
                batch_id = await dispatcher.dispatch_batch(
                    file_paths=[doc.file_path], kb_id=kb_id, description=f"Automatic indexing for {doc.filename}"
                )

            # Update legacy link status
            link.status = "processing"
            link.error_message = f"V3 Swarm Batch: {batch_id}"
            session.add(link)
            await session.commit()

        except Exception as e:
            logger.exception(f"💥 Critical Error during V3 Swarm Dispatch for Doc {doc_id}")
            link.status = "failed"
            link.error_message = str(e)
            session.add(link)
            await session.commit()
