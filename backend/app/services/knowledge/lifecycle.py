
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from loguru import logger
from sqlmodel import select, col, delete

from app.core.database import async_session_factory
from app.models.knowledge import Document, KnowledgeBaseDocumentLink

class KnowledgeLifecycleService:
    """
    M6.2: Knowledge Lifecycle & Document Lifecycle Governance.
    Manages TTL, Auto-Archiving, and Incremental Cleanup.
    """

    async def purge_expired_documents(self) -> Dict[str, Any]:
        """
        Hard deletion of expired documents from all KBs.
        This is a 'Clean-up' operation to keep the RAG system healthy.
        """
        now = datetime.utcnow()
        async with async_session_factory() as session:
            # 1. Find Expired Docs
            stmt = select(Document).where(Document.expiry_date < now)
            res = await session.execute(stmt)
            expired_docs = res.scalars().all()
            
            if not expired_docs:
                return {"deleted_count": 0, "status": "all_fresh"}

            ids_to_del = [d.id for d in expired_docs]
            
            # 2. Delete Vector Embeddings (Cleanup trigger for Chroma/FAISS)
            # In a real system, this would trigger a background task for vector db cleanup
            logger.warning(f"🛡️ [Lifecycle] Purging {len(ids_to_del)} expired documents: {ids_to_del}")

            # 3. DB Cleanup
            # Delete links first
            link_stmt = delete(KnowledgeBaseDocumentLink).where(col(KnowledgeBaseDocumentLink.document_id).in_(ids_to_del))
            await session.execute(link_stmt)
            
            # Delete Docs
            doc_stmt = delete(Document).where(col(Document.id).in_(ids_to_del))
            await session.execute(doc_stmt)
            
            await session.commit()
            
            return {
                "deleted_count": len(ids_to_del),
                "deleted_ids": ids_to_del,
                "timestamp": now.isoformat()
            }

    async def auto_archive_stale(self, review_threshold_days: int = 90) -> int:
        """
        Soft archiving: Mark documents for manual review instead of deletion.
        """
        threshold = datetime.utcnow() - timedelta(days=review_threshold_days)
        async with async_session_factory() as session:
            # Documents not modified/reviewed for a long time
            stmt = select(Document).where(
                col(Document.updated_at) < threshold,
                Document.status != "archived"
            )
            stale_docs = (await session.execute(stmt)).scalars().all()
            
            for doc in stale_docs:
                doc.status = "stale"
                doc.next_review_at = datetime.utcnow() + timedelta(days=7) # Review in 7 days
                session.add(doc)
                
            await session.commit()
            return len(stale_docs)

knowledge_lifecycle_service = KnowledgeLifecycleService()
