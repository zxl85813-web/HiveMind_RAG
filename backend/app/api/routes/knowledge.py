"""
Knowledge Base management endpoints.
"""
from typing import Sequence
import shutil
import os
import uuid
import aiofiles
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlmodel import Session
from app.api.deps import get_db, get_current_user
from app.models.knowledge import KnowledgeBase, Document, KnowledgeBaseDocumentLink
from app.schemas.knowledge import KnowledgeBaseCreate, KnowledgeBaseUpdate, DocumentCreate, DocumentResponse
from app.services.knowledge_base import KnowledgeService
from app.services.indexing import index_document_task
from app.models.chat import User
from app.core.config import settings
from app.common.response import ApiResponse

router = APIRouter()
mock_user_id = "mock-user-001"


@router.post("/", response_model=KnowledgeBase)
async def create_knowledge_base(
    kb_in: KnowledgeBaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new knowledge base."""
    service = KnowledgeService(db)
    # Generate unique collection name if not provided
    collection_name = kb_in.vector_collection
    if collection_name == "default_collection":
        collection_name = f"kb_{uuid.uuid4().hex[:8]}"
        
    kb = KnowledgeBase(
        name=kb_in.name,
        description=kb_in.description,
        owner_id=current_user.id,
        embedding_model=kb_in.embedding_model,
        vector_collection=collection_name,
        is_public=kb_in.is_public,
    )
    kb = service.create_kb(kb)
    return ApiResponse.ok(data=kb)


@router.get("/", response_model=Sequence[KnowledgeBase])
async def list_knowledge_bases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all knowledge bases owned by user."""
    service = KnowledgeService(db)
    kbs = service.list_kbs(mock_user_id)
    return ApiResponse.ok(data=kbs)


@router.get("/{kb_id}", response_model=KnowledgeBase)
async def get_knowledge_base(
    kb_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get knowledge base details."""
    service = KnowledgeService(db)
    kb = service.get_kb(kb_id)
    if kb.owner_id != current_user.id and not kb.is_public:
        raise HTTPException(status_code=403, detail="Not authorized")
    return ApiResponse.ok(data=kb)


@router.post("/documents", response_model=DocumentResponse)
async def upload_document_global(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a document to the global library (not linked to any KB yet)."""
    # 1. Save file to local storage (TODO: Use MinIO/S3 via StorageBackend)
    upload_dir = "uploads"  # Should be configured in settings
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename to avoid collision
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(upload_dir, unique_filename)
    
    # Write file
    async with aiofiles.open(file_path, 'wb') as out_file:
        content = await file.read() # Read into memory (careful with large files)
        await out_file.write(content)
        
    # 2. Extract metadata
    file_size = len(content)
    file_type = file.filename.split('.')[-1].lower() if '.' in file.filename else 'unknown'
    
    # 3. Create Document record
    doc = Document(
        filename=file.filename,
        file_type=file_type,
        file_size=file_size,
        storage_path=file_path,
        status="pending"
        # owner_id=current_user.id # TODO: Add owner to schema
    )
    
    service = KnowledgeService(db)
    return service.create_document(doc)


@router.post("/{kb_id}/documents/{doc_id}", response_model=KnowledgeBaseDocumentLink)
async def link_document(
    kb_id: str,
    doc_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Link an existing document to a knowledge base and start indexing."""
    service = KnowledgeService(db)
    # Check ownership
    kb = service.get_kb(kb_id)
    if kb.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    link = service.link_document_to_kb(kb_id, doc_id)
    
    # Trigger background indexing
    background_tasks.add_task(index_document_task, kb_id, doc_id)
    
    return link


@router.get("/{kb_id}/documents", response_model=Sequence[Document])
async def list_documents_in_kb(
    kb_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List documents in a knowledge base."""
    service = KnowledgeService(db)
    kb = service.get_kb(kb_id)
    # Access control
    if kb.owner_id != current_user.id and not kb.is_public:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    return service.list_documents_in_kb(kb_id)


@router.delete("/{kb_id}/documents/{doc_id}")
async def unlink_document(
    kb_id: str,
    doc_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unlink a document from a knowledge base."""
    service = KnowledgeService(db)
    kb = service.get_kb(kb_id)
    if kb.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    service.unlink_document(kb_id, doc_id)
    return {"status": "success", "message": "Document unlinked"}
