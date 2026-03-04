"""
Tag & Category Endpoints.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user
from app.common.response import ApiResponse
from app.schemas.tags import (
    TagCreate, TagRead, TagCategoryCreate, TagCategoryRead, 
    TagWithCategory, DocumentTagAttach
)
from app.services.tag_service import TagService
from app.models.chat import User

router = APIRouter()


@router.get("/categories", response_model=ApiResponse[List[TagCategoryRead]])
async def list_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all tag categories."""
    categories = await TagService.get_categories(db)
    return ApiResponse.ok(data=categories)


@router.post("/categories", response_model=ApiResponse[TagCategoryRead])
async def create_category(
    category: TagCategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new tag category."""
    db_cat = await TagService.create_category(db, category)
    return ApiResponse.ok(data=db_cat)


@router.get("", response_model=ApiResponse[List[TagWithCategory]])
async def list_tags(
    category_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all tags."""
    tags = await TagService.get_tags(db, category_id)
    return ApiResponse.ok(data=tags)


@router.post("", response_model=ApiResponse[TagRead])
async def create_tag(
    tag: TagCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new tag."""
    db_tag = await TagService.create_tag(db, tag)
    return ApiResponse.ok(data=db_tag)


@router.delete("/{tag_id}", response_model=ApiResponse)
async def delete_tag(
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a tag."""
    success = await TagService.delete_tag(db, tag_id)
    if not success:
        return ApiResponse.error(message="Tag not found", code=404)
    return ApiResponse.ok(message="Tag deleted")


@router.post("/documents/{document_id}/attach", response_model=ApiResponse)
async def attach_tag(
    document_id: str,
    payload: DocumentTagAttach,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Attach a tag to a document."""
    await TagService.attach_tag_to_document(db, document_id, payload.tag_id)
    return ApiResponse.ok(message="Tag attached")


@router.delete("/documents/{document_id}/tags/{tag_id}", response_model=ApiResponse)
async def detach_tag(
    document_id: str,
    tag_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Detach a tag from a document."""
    await TagService.detach_tag_from_document(db, document_id, tag_id)
    return ApiResponse.ok(message="Tag detached")
