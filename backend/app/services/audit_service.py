from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from loguru import logger

from app.models.security import DocumentReview
from app.services.security.audit import AuditEngine

class AuditService:
    """Service for managing document quality audits (M2.3)."""

    @staticmethod
    async def run_audit(db: AsyncSession, doc_id: str, resource_data: dict) -> DocumentReview:
        """Runs the automatic audit or returns existing manual approval."""
        from app.models.knowledge import Document
        
        text = resource_data.get("raw_text", "")
        
        # 1. Check for existing manual approval
        statement = select(DocumentReview).where(
            DocumentReview.document_id == doc_id,
            DocumentReview.status == "approved"
        )
        result = await db.execute(statement)
        existing = result.scalars().first()
        if existing:
            logger.info(f"⏭️ Skipping audit for Doc {doc_id}: already approved.")
            return existing

        logger.info(f"🔍 Running quality audit for Doc {doc_id}")
        stats = AuditEngine.audit_text(resource_data)
        content_hash = stats.get("content_hash")
        
        # 2. Store hash in Document if not exists
        doc = await db.get(Document, doc_id)
        if doc and not doc.content_hash:
            doc.content_hash = content_hash
            db.add(doc)
            
        # 3. Content Deduplication Check (M2.1D)
        if content_hash:
            dup_stmt = select(Document).where(
                Document.content_hash == content_hash,
                Document.id != doc_id
            )
            dup_res = await db.execute(dup_stmt)
            existing_doc = dup_res.scalars().first()
            if existing_doc:
                logger.warning(f"🔴 Duplicate content detected for Doc {doc_id}. Matches {existing_doc.id}")
                stats["status"] = "rejected"
                stats["message"] = f"Rejected: Strict Duplicate of document {existing_doc.filename} ({existing_doc.id})"
        
        # 4. M2.3.6: Knowledge Overlap Check (Async LLM Probing)
        overlap_score = 0.0
        if stats["status"] != "rejected" and len(text) > 300:
            try:
                from app.services.security.overlap import KnowledgeOverlapEngine
                overlap_res = await KnowledgeOverlapEngine.check_overlap(text)
                overlap_score = overlap_res.overlap_score
                
                # If content is already known by LLM (e.g. >80% overlap), 
                # we might want to flag it for review even if quality is good.
                if overlap_res.is_known and stats["status"] == "approved":
                    logger.info(f"🟡 Doc {doc_id} is marked as PENDING due to high LLM knowledge overlap.")
                    stats["status"] = "pending"
                    stats["message"] = f"High knowledge overlap ({overlap_score:.2f}). Redundant data?"
            except Exception as e:
                logger.error(f"Overlap check failed: {e}")

        review = DocumentReview(
            document_id=doc_id,
            review_type="auto",
            status=stats["status"],
            quality_score=stats["quality_score"],
            content_length_ok=stats["content_length_ok"],
            duplicate_ratio=stats["duplicate_ratio"],
            garble_ratio=stats["garble_ratio"],
            blank_ratio=stats["blank_ratio"],
            overlap_score=overlap_score,
            reviewer_comment=stats.get("message", "")
        )
        
        db.add(review)
        await db.commit()
        await db.refresh(review)
        
        logger.info(f"✅ Audit complete for Doc {doc_id}: Score={review.quality_score}, Overlap={review.overlap_score}, Status={review.status}")
        return review

    @staticmethod
    async def get_review(db: AsyncSession, review_id: str) -> Optional[DocumentReview]:
        """Fetch a specific review record."""
        return await db.get(DocumentReview, review_id)

    @staticmethod
    async def get_document_reviews(db: AsyncSession, doc_id: str) -> List[DocumentReview]:
        """Get all review records for a specific document."""
        statement = select(DocumentReview).where(DocumentReview.document_id == doc_id)
        result = await db.execute(statement)
        return result.scalars().all()

    @staticmethod
    async def get_pending_reviews(db: AsyncSession) -> List[DocumentReview]:
        """Get the queue of reviews waiting for manual intervention."""
        statement = select(DocumentReview).where(DocumentReview.status == "pending")
        result = await db.execute(statement)
        return result.scalars().all()

    @staticmethod
    async def update_review_status(
        db: AsyncSession, 
        review_id: str, 
        status: str, 
        comment: str = "", 
        reviewer_id: str = None
    ) -> Optional[DocumentReview]:
        """Manually update the status of a review."""
        review = await db.get(DocumentReview, review_id)
        if review:
            review.status = status
            review.reviewer_comment = comment
            if reviewer_id:
                review.reviewer_id = reviewer_id
            review.review_type = "manual"
            await db.commit()
            await db.refresh(review)
        return review
