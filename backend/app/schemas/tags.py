"""
Pydantic schemas for Tags & Categories.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class TagCategoryBase(BaseModel):
    name: str
    description: Optional[str] = None


class TagCategoryCreate(TagCategoryBase):
    pass


class TagCategoryRead(TagCategoryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TagBase(BaseModel):
    name: str
    color: str = "#64748b"
    category_id: Optional[int] = None


class TagCreate(TagBase):
    pass


class TagRead(TagBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TagWithCategory(TagRead):
    category: Optional[TagCategoryRead] = None


class DocumentTagAttach(BaseModel):
    tag_id: int


class DocumentTagResponse(BaseModel):
    document_id: str
    tag_id: int
    tag: TagRead
