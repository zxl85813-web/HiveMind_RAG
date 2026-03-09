from datetime import datetime

from pydantic import BaseModel


class DocumentReviewBase(BaseModel):
    document_id: str
    review_type: str
    status: str
    quality_score: float
    content_length_ok: bool
    duplicate_ratio: float
    garble_ratio: float
    blank_ratio: float
    overlap_score: float = 0.0
    reviewer_comment: str | None = None


class DocumentReviewUpdate(BaseModel):
    status: str  # approved | rejected | needs_revision
    reviewer_comment: str | None = ""


class DocumentReviewRead(DocumentReviewBase):
    id: str
    reviewer_id: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AuditStats(BaseModel):
    total_reviewed: int
    approved_count: int
    pending_count: int
    rejected_count: int
    avg_quality_score: float
