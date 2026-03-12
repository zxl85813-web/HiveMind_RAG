"""
Knowledge Base management endpoints.
"""

import os
import uuid
from collections.abc import Sequence
from typing import Any

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.auth.permissions import Permission, require_permission
from app.common.response import ApiResponse
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.vector_store import get_vector_store
from app.models.chat import User
from app.models.knowledge import Document, KnowledgeBase, KnowledgeBaseDocumentLink
from app.models.security import KnowledgeBasePermission
from app.schemas.knowledge import DocumentResponse, KBPermissionInput, KnowledgeBaseCreate
from app.schemas.knowledge_protocol import KBStatus
from app.services.indexing import index_document_task
from app.services.knowledge.kb_service import KnowledgeService
from app.services.rag_gateway import RAGGateway

router = APIRouter()


@router.post(
    "",
    response_model=ApiResponse[KnowledgeBase],
    dependencies=[Depends(require_permission(Permission.KB_CREATE))],
)
async def create_knowledge_base(
    kb_in: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db),
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
        chunking_strategy=kb_in.chunking_strategy,
    )
    kb = await service.create_kb(kb)
    return ApiResponse.ok(data=kb)


@router.get(
    "",
    response_model=ApiResponse[Sequence[KnowledgeBase]],
    dependencies=[Depends(require_permission(Permission.KB_VIEW))],
)
async def list_knowledge_bases(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all knowledge bases owned by user."""
    service = KnowledgeService(db)
    kbs = await service.list_kbs(current_user)
    return ApiResponse.ok(data=kbs)


# ----------------------------------------------------------------------------
# RAG Search
# ----------------------------------------------------------------------------


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    search_type: str = "hybrid"  # vector, bm25, hybrid


class SearchResponse(BaseModel):
    results: list[dict[str, Any]]
    context_log: list[str]


@router.post(
    "/{kb_id}/search",
    response_model=ApiResponse[SearchResponse],
    dependencies=[Depends(require_permission(Permission.KB_VIEW))],
)
async def search_knowledge_base(kb_id: str, request: SearchRequest, current_user: User = Depends(get_current_user)):
    """
    Search a specific knowledge base using the Retrieval Pipeline.
    This replaces the raw vector store search, incorporating query rewrite and reranking.
    """
    from app.core.database import async_session_factory

    async with async_session_factory() as session:
        kb = await session.get(KnowledgeBase, kb_id)
        if not kb:
            raise NotFoundError(resource="Knowledge Base", id=kb_id)

        service = KnowledgeService(session)
        if not await service.check_kb_access(kb_id, current_user, level="read"):
            raise ForbiddenError(message="Not authorized to search this knowledge base", deny_reason="kb_acl_denied")

    gateway = RAGGateway()

    knowledge_res = await gateway.retrieve(
        query=request.query, kb_ids=[kb_id], top_k=request.top_k, strategy=request.search_type
    )

    return ApiResponse.ok(data=knowledge_res)


@router.get(
    "/{kb_id}/health",
    response_model=ApiResponse[KBStatus],
    dependencies=[Depends(require_permission(Permission.KB_VIEW))],
)
async def get_kb_health(kb_id: str, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get the health status and circuit breaker state of a KB."""
    gateway = RAGGateway()
    # Mocking score calculation for now
    is_tripped = gateway._is_circuit_open(kb_id)

    return ApiResponse.ok(
        data=KBStatus(kb_id=kb_id, is_healthy=not is_tripped, score_avg=0.95, circuit_tripped=is_tripped)
    )


@router.get(
    "/{kb_id}",
    response_model=ApiResponse[KnowledgeBase],
    dependencies=[Depends(require_permission(Permission.KB_VIEW))],
)
async def get_knowledge_base(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get knowledge base details."""
    service = KnowledgeService(db)
    kb = await service.get_kb(kb_id)
    if not await service.check_kb_access(kb_id, current_user, level="read"):
        raise ForbiddenError(message="Not authorized to view this knowledge base", deny_reason="kb_acl_denied")
    return ApiResponse.ok(data=kb)


@router.get(
    "/{kb_id}/permissions",
    response_model=ApiResponse[Sequence[KnowledgeBasePermission]],
    dependencies=[Depends(require_permission(Permission.SYSTEM_CONFIG))],
)
async def get_knowledge_base_permissions(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all permissions for a knowledge base."""
    service = KnowledgeService(db)
    if not await service.check_kb_access(kb_id, current_user, level="manage"):
        raise HTTPException(status_code=403, detail="Not authorized to manage this knowledge base")

    from sqlmodel import select

    stmt = select(KnowledgeBasePermission).where(KnowledgeBasePermission.kb_id == kb_id)
    res = await db.execute(stmt)
    return ApiResponse.ok(data=res.scalars().all())


@router.post(
    "/{kb_id}/permissions",
    response_model=ApiResponse[KnowledgeBasePermission],
    dependencies=[Depends(require_permission(Permission.SYSTEM_CONFIG))],
)
async def add_knowledge_base_permission(
    kb_id: str,
    perm_in: KBPermissionInput,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new permission rule to a knowledge base."""
    service = KnowledgeService(db)
    if not await service.check_kb_access(kb_id, current_user, level="manage"):
        raise HTTPException(status_code=403, detail="Not authorized to manage this knowledge base")

    # Either user, role or department must be specified
    if not perm_in.user_id and not perm_in.role_id and not perm_in.department_id:
        raise ForbiddenError(message="Must specify user_id, role_id, or department_id", deny_reason="validation_error")

    perm = KnowledgeBasePermission(
        kb_id=kb_id,
        user_id=perm_in.user_id,
        role_id=perm_in.role_id,
        department_id=perm_in.department_id,
        can_read=perm_in.can_read,
        can_write=perm_in.can_write,
        can_manage=perm_in.can_manage,
    )
    db.add(perm)
    await db.commit()
    await db.refresh(perm)
    return ApiResponse.ok(data=perm)


@router.delete("/{kb_id}/permissions/{perm_id}")
async def delete_knowledge_base_permission(
    kb_id: str,
    perm_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a permission rule from a knowledge base."""
    service = KnowledgeService(db)
    if not await service.check_kb_access(kb_id, current_user, level="manage"):
        raise HTTPException(status_code=403, detail="Not authorized to manage this knowledge base")

    perm = await db.get(KnowledgeBasePermission, perm_id)
    if not perm or perm.kb_id != kb_id:
        raise NotFoundError(resource="Permission", resource_id=perm_id)

    # Prevent owner from removing themselves
    kb = await db.get(KnowledgeBase, kb_id)
    if perm.user_id == kb.owner_id:
        raise ForbiddenError(message="Cannot remove owner's permission", deny_reason="rbac_denied")

    await db.delete(perm)
    await db.commit()
    return ApiResponse.ok(data={"status": "success", "message": "Permission removed"})


@router.post(
    "/documents",
    response_model=ApiResponse[DocumentResponse],
    dependencies=[Depends(require_permission(Permission.KB_UPLOAD))],
)
async def upload_document_global(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a document to the global library (not linked to any KB yet)."""
    # 1. Save file to local storage (TODO: Use MinIO/S3 via StorageBackend)
    upload_dir = "uploads"  # Should be configured in settings
    os.makedirs(upload_dir, exist_ok=True)

    # Generate unique filename to avoid collision
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    file_path = os.path.join(upload_dir, unique_filename)

    # Write file by chunks to avoid OOM
    file_size = 0
    async with aiofiles.open(file_path, "wb") as out_file:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            await out_file.write(chunk)
            file_size += len(chunk)

    # 2. Extract metadata
    file_type = file.filename.split(".")[-1].lower() if "." in file.filename else "unknown"

    # 3. Create Document record
    doc = Document(
        filename=file.filename,
        file_type=file_type,
        file_size=file_size,
        storage_path=file_path,
        status="pending",
        # owner_id=current_user.id # TODO: Add owner to schema
    )

    service = KnowledgeService(db)
    doc = await service.create_document(doc)
    return ApiResponse.ok(data=doc)


@router.post(
    "/{kb_id}/documents/{doc_id}",
    response_model=ApiResponse[KnowledgeBaseDocumentLink],
    dependencies=[Depends(require_permission(Permission.KB_UPLOAD))],
)
async def link_document(
    kb_id: str,
    doc_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Link an existing document to a knowledge base and start indexing."""
    service = KnowledgeService(db)
    # Check ownership
    await service.get_kb(kb_id)
    if not await service.check_kb_access(kb_id, current_user, level="write"):
        raise ForbiddenError(message="Not authorized to modify this knowledge base", deny_reason="kb_acl_denied")

    link = await service.link_document_to_kb(kb_id, doc_id)

    # Trigger background indexing
    background_tasks.add_task(index_document_task, kb_id, doc_id)

    return ApiResponse.ok(data=link)


@router.get(
    "/{kb_id}/documents",
    response_model=ApiResponse[Sequence[Document]],
    dependencies=[Depends(require_permission(Permission.KB_VIEW))],
)
async def list_documents_in_kb(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List documents in a knowledge base."""
    service = KnowledgeService(db)
    await service.get_kb(kb_id)
    # Access control
    if not await service.check_kb_access(kb_id, current_user, level="read"):
        raise ForbiddenError(message="Not authorized to view documents in this KB", deny_reason="kb_acl_denied")

    docs = await service.list_documents_in_kb(kb_id)
    return ApiResponse.ok(data=docs)


@router.delete("/{kb_id}/documents/{doc_id}", dependencies=[Depends(require_permission(Permission.KB_UPLOAD))])
async def unlink_document(
    kb_id: str,
    doc_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unlink a document from a knowledge base."""
    service = KnowledgeService(db)
    kb = await service.get_kb(kb_id)
    if not await service.check_kb_access(kb_id, current_user, level="write"):
        raise ForbiddenError(message="Not authorized to modify this knowledge base", deny_reason="kb_acl_denied")

    await service.unlink_document(kb_id, doc_id)

    # Clean up vector store
    store = get_vector_store()
    try:
        await store.delete_documents(kb.vector_collection, {"doc_id": doc_id})
    except Exception as e:
        import loguru

        loguru.logger.error(f"Failed to delete docs from vector store for {doc_id}: {e}")

    return ApiResponse.ok(data={"status": "success", "message": "Document unlinked"})


@router.get("/{kb_id}/graph", dependencies=[Depends(require_permission(Permission.KB_VIEW))])
async def get_knowledge_graph(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the knowledge graph subset for this KB."""
    from app.core.graph_store import get_graph_store

    service = KnowledgeService(db)
    await service.get_kb(kb_id)
    if not await service.check_kb_access(kb_id, current_user, level="read"):
        raise ForbiddenError(message="Not authorized to view graph for this KB", deny_reason="kb_acl_denied")

    store = get_graph_store()
    if not store.driver:
        return ApiResponse.ok(data={"nodes": [], "links": []})

    cypher = """
    MATCH (n {kb_id: $kb_id})
    OPTIONAL MATCH (n)-[r]->(m {kb_id: $kb_id})
    RETURN collect(DISTINCT n) as nodes, collect(DISTINCT r) as links
    """
    results = store.query(cypher, {"kb_id": kb_id})

    nodes = []
    links = []

    if results:
        # Format for react-force-graph
        for n in results[0].get("nodes", []):
            if n:
                nodes.append({"id": n.get("id"), "name": n.get("name") or n.get("id"), "label": "Entity", "val": 10})

        for r in results[0].get("links", []):
            if r:
                links.append(
                    {
                        "source": (
                            r[0].element_id if hasattr(r[0], "element_id") else r[0].id if hasattr(r[0], "id") else r[0]
                        ),
                        "target": (
                            r[2].element_id if hasattr(r[2], "element_id") else r[2].id if hasattr(r[2], "id") else r[2]
                        ),
                        "type": r[1].type if hasattr(r[1], "type") else "RELATED",
                    }
                )

    return ApiResponse.ok(data={"nodes": nodes, "links": links})


@router.get("/documents/{doc_id}/preview", dependencies=[Depends(require_permission(Permission.KB_VIEW))])
async def get_document_preview(
    doc_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the parsed text content of a document for preview."""
    from sqlmodel import desc, select

    from app.auth.permissions import has_document_permission
    from app.models.observability import FileTrace

    # 0. Check document access (ARM-P0-1)
    if not await has_document_permission(db, current_user, doc_id, required_level="read"):
        raise ForbiddenError(message="Not authorized to preview this document", deny_reason="doc_acl_denied")

    # 1. Get latest trace for this doc_id
    stmt = select(FileTrace).where(FileTrace.doc_id == doc_id).order_by(desc(FileTrace.created_at))
    res = await db.execute(stmt)
    trace = res.scalars().first()

    if not trace:
        raise NotFoundError(resource="FileTrace", resource_id=doc_id)

    # 2. Extract preview text from result_data
    result = trace.result_data or {}
    text = result.get("raw_text", "No raw text extracted by Swarm.")

    return ApiResponse.ok(data={"text": text, "trace_id": trace.id, "status": trace.status, "kb_id": trace.kb_id})
