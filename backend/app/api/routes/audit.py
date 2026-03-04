from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api import deps
from app.common.response import ApiResponse
from app.schemas.audit import DocumentReviewRead, DocumentReviewUpdate
from app.services.audit_service import AuditService

router = APIRouter()

@router.get("/queue", response_model=ApiResponse[List[DocumentReviewRead]])
async def get_review_queue(
    db: AsyncSession = Depends(deps.get_db),
    # current_user = Depends(deps.get_current_admin) # TODO: Restricted to admins/reviewers
):
    """Get the queue of documents pending manual review."""
    reviews = await AuditService.get_pending_reviews(db)
    return ApiResponse.ok(data=reviews)

@router.get("/document/{document_id}", response_model=ApiResponse[List[DocumentReviewRead]])
async def get_document_reviews(
    document_id: str,
    db: AsyncSession = Depends(deps.get_db)
):
    """Get all review history for a specific document."""
    reviews = await AuditService.get_document_reviews(db, document_id)
    return ApiResponse.ok(data=reviews)

@router.post("/{review_id}/approve", response_model=ApiResponse[DocumentReviewRead])
async def approve_review(
    review_id: str,
    background_tasks: BackgroundTasks,
    comment: str = "Approved by admin",
    db: AsyncSession = Depends(deps.get_db),
):
    """Manually approve a document review and trigger re-indexing."""
    review = await AuditService.update_review_status(
        db, review_id, status="approved", comment=comment
    )
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found")
    
    # Find all knowledge bases where this document is pending review
    from app.models.knowledge import KnowledgeBaseDocumentLink
    from app.services.indexing import index_document_task
    from sqlmodel import select
    
    statement = select(KnowledgeBaseDocumentLink).where(
        KnowledgeBaseDocumentLink.document_id == review.document_id,
        KnowledgeBaseDocumentLink.status == "pending_review"
    )
    result = await db.execute(statement)
    links = result.scalars().all()
    
    for link in links:
        background_tasks.add_task(index_document_task, link.knowledge_base_id, link.document_id)
        
    return ApiResponse.ok(data=review)

@router.post("/{review_id}/reject", response_model=ApiResponse[DocumentReviewRead])
async def reject_review(
    review_id: str,
    comment: str = "Rejected by admin",
    db: AsyncSession = Depends(deps.get_db),
):
    """Manually reject a document review."""
    review = await AuditService.update_review_status(
        db, review_id, status="rejected", comment=comment
    )
    if not review:
        raise HTTPException(status_code=404, detail="Review record not found")
    return ApiResponse.ok(data=review)

@router.put("/{review_id}", response_model=ApiResponse[DocumentReviewRead])
async def update_review(
    review_id: str,
    update_data: DocumentReviewUpdate,
    db: AsyncSession = Depends(deps.get_db)
):
    """Update review status or comment."""
    review = await AuditService.update_review_status(
        db, 
        review_id, 
        status=update_data.status, 
        comment=update_data.reviewer_comment
    )
    return ApiResponse.ok(data=review)
