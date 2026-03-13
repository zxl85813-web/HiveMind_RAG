from uuid import UUID
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum

class FeedbackStatus(str, Enum):
    PENDING = "pending"
    RESOLVED = "resolved"
    REJECTED = "rejected"

class FeedbackBase(BaseModel):
    content: str = Field(..., description="反馈内容")
    rating: int = Field(..., ge=1, le=5, description="评分 1-5")
    image_url: Optional[str] = Field(None, description="可选图片链接")

class FeedbackCreateRequest(FeedbackBase):
    pass

class FeedbackUpdateRequest(BaseModel):
    status: FeedbackStatus

class FeedbackResponse(FeedbackBase):
    id: UUID
    status: FeedbackStatus
    created_at: datetime
    updated_at: datetime
    created_by: UUID

    class Config:
        from_attributes = True
