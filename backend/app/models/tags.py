"""
Tags & Categories Models — For document organization and filtering.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .knowledge import Document


class TagCategory(SQLModel, table=True):
    """Category for grouping tags (e.g., 'Document Type', 'Department')."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    tags: list["Tag"] = Relationship(
        back_populates="category", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class DocumentTagLink(SQLModel, table=True):
    """Many-to-Many link between Document and Tag."""

    document_id: str = Field(foreign_key="documents.id", primary_key=True)
    tag_id: int = Field(foreign_key="tag.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    tag: "Tag" = Relationship(back_populates="doc_links")
    document: "Document" = Relationship(back_populates="tag_links")


class Tag(SQLModel, table=True):
    """Individual tag that can be attached to documents."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    color: str = Field(default="#64748b")  # Default slate-500
    category_id: int | None = Field(default=None, foreign_key="tagcategory.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    category: TagCategory | None = Relationship(back_populates="tags")
    documents: list["Document"] = Relationship(back_populates="tags", link_model=DocumentTagLink, sa_relationship_kwargs={"overlaps": "doc_links,tag,document"})
    doc_links: list[DocumentTagLink] = Relationship(back_populates="tag", sa_relationship_kwargs={"overlaps": "documents,tag,document"})
