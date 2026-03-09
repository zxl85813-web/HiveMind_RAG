"""
Pydantic schemas for Tags & Categories.
"""

from datetime import datetime

from pydantic import BaseModel


class TagCategoryBase(BaseModel):
    name: str
    description: str | None = None


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
    category_id: int | None = None


class TagCreate(TagBase):
    pass


class TagRead(TagBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class TagWithCategory(TagRead):
    category: TagCategoryRead | None = None


class DocumentTagAttach(BaseModel):
    tag_id: int


class DocumentTagResponse(BaseModel):
    document_id: str
    tag_id: int
    tag: TagRead
