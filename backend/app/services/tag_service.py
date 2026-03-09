"""
Tag Service — Logic for managing tags and document categorizing.
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import delete, select

from app.core.exceptions import NotFoundError
from app.models.tags import DocumentTagLink, Tag, TagCategory
from app.schemas.tags import TagCategoryCreate, TagCreate


class TagService:
    """Service for handling Tag-related operations."""

    @staticmethod
    async def create_category(db: AsyncSession, category: TagCategoryCreate) -> TagCategory:
        """Create a new tag category."""
        db_category = TagCategory.model_validate(category)
        db.add(db_category)
        await db.commit()
        await db.refresh(db_category)
        return db_category

    @staticmethod
    async def get_categories(db: AsyncSession) -> list[TagCategory]:
        """List all tag categories."""
        statement = select(TagCategory)
        result = await db.execute(statement)
        return result.scalars().all()

    @staticmethod
    async def create_tag(db: AsyncSession, tag: TagCreate) -> Tag:
        """Create a new tag."""
        if tag.category_id:
            category = await db.get(TagCategory, tag.category_id)
            if not category:
                raise NotFoundError("TagCategory", tag.category_id)

        db_tag = Tag.model_validate(tag)
        db.add(db_tag)
        await db.commit()
        await db.refresh(db_tag)
        return db_tag

    @staticmethod
    async def get_tags(db: AsyncSession, category_id: int | None = None) -> list[Tag]:
        """List tags, optionally filtered by category."""
        statement = select(Tag)
        if category_id:
            statement = statement.where(Tag.category_id == category_id)
        result = await db.execute(statement)
        return result.scalars().all()

    @staticmethod
    async def delete_tag(db: AsyncSession, tag_id: int) -> bool:
        """Delete a tag."""
        tag = await db.get(Tag, tag_id)
        if not tag:
            return False
        await db.delete(tag)
        await db.commit()
        return True

    @staticmethod
    async def attach_tag_to_document(db: AsyncSession, document_id: str, tag_id: int) -> DocumentTagLink:
        """Link a tag to a document."""
        # Verify tag exists
        tag = await db.get(Tag, tag_id)
        if not tag:
            raise NotFoundError("Tag", tag_id)

        # check if already exists
        statement = select(DocumentTagLink).where(
            DocumentTagLink.document_id == document_id, DocumentTagLink.tag_id == tag_id
        )
        existing = (await db.execute(statement)).first()
        if existing:
            return existing[0]

        link = DocumentTagLink(document_id=document_id, tag_id=tag_id)
        db.add(link)
        await db.commit()
        await db.refresh(link)
        return link

    @staticmethod
    async def detach_tag_from_document(db: AsyncSession, document_id: str, tag_id: int) -> bool:
        """Remove a tag from a document."""
        statement = delete(DocumentTagLink).where(
            DocumentTagLink.document_id == document_id, DocumentTagLink.tag_id == tag_id
        )
        await db.execute(statement)
        await db.commit()
        return True

    @staticmethod
    async def get_document_tags(db: AsyncSession, document_id: str) -> list[Tag]:
        """Get all tags for a specific document."""
        statement = select(Tag).join(DocumentTagLink).where(DocumentTagLink.document_id == document_id)
        result = await db.execute(statement)
        return result.scalars().all()
