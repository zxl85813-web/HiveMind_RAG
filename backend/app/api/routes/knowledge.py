"""
Knowledge Base management endpoints.
"""

import os
import uuid
from collections.abc import Sequence
from typing import Any

import aiofiles  # 保留：StorageService 内部降级到本地存储时仍需要
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.auth.permissions import Permission, require_permission
from app.common.response import ApiResponse
from app.core.exceptions import ForbiddenError, NotFoundError
from app.core.vector_store import get_vector_store
from app.models.chat import User
from app.sdk.core import settings
from app.models.knowledge import Document, KnowledgeBase, KnowledgeBaseDocumentLink
from app.models.security import KnowledgeBasePermission
from app.schemas.knowledge import DocumentResponse, KBPermissionInput, KnowledgeBaseCreate
from app.schemas.knowledge_protocol import KBStatus
from app.services.indexing import index_document_task
from app.services.knowledge.kb_service import KnowledgeService
from app.services.rag_gateway import RAGGateway
from app.services.rate_limit_governance import rate_limit_governance_center
from app.services.write_event_bus import fire_and_forget_write_event

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


@router.get("/governance/report", response_model=ApiResponse[dict[str, Any]])
async def get_knowledge_health_report():
    """获取知识库健康度与新鲜度报告。"""
    from app.services.knowledge.freshness_service import knowledge_freshness_service
    report = await knowledge_freshness_service.get_freshness_report()
    return ApiResponse.ok(data=report)


@router.post("/governance/purge", response_model=ApiResponse[dict[str, Any]])
async def purge_expired_knowledge():
    """清理所有已过期的知识文档，防止 RAG 污染。"""
    from app.services.knowledge.lifecycle import knowledge_lifecycle_service
    result = await knowledge_lifecycle_service.purge_expired_documents()
    return ApiResponse.ok(data=result)


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
    request: Request,
    file: UploadFile = File(...),
    folder_path: str | None = None,   # 可选：前端传入原始文件夹路径，如 "技术文档/2024"
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传单个文件到全局文档库（尚未关联到任何 KB）。"""
    decision = rate_limit_governance_center.check(
        route=str(request.url.path),
        user_id=current_user.id,
        api_key=request.headers.get("x-api-key"),
    )
    if not bool(decision["allowed"]):
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Rate limit exceeded",
                "reason_code": decision["reason_code"],
                "dimension": decision["dimension"],
            },
            headers={"Retry-After": str(int(decision["retry_after_sec"]))},
        )

    from app.services.storage_service import StorageService

    # 1. 流式读取文件内容（1MB 分块，防 OOM）
    chunks = []
    while chunk := await file.read(1024 * 1024):
        chunks.append(chunk)
    file_content = b"".join(chunks)

    content_type = file.content_type or "application/octet-stream"
    file_type = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "unknown"

    # 2. 上传到 S3（或本地降级）
    storage_path, file_size, content_hash = await StorageService.upload_file(
        file_content=file_content,
        filename=file.filename,
        content_type=content_type,
        folder_path=folder_path,
    )

    # 3. 创建 Document 记录
    doc = Document(
        filename=file.filename,
        file_type=file_type,
        file_size=file_size,
        storage_path=storage_path,
        file_path=storage_path,   # 保持同步，供索引管道使用
        folder_path=folder_path,
        content_hash=content_hash,
        status="pending",
    )
    service = KnowledgeService(db)
    doc = await service.create_document(doc)
    fire_and_forget_write_event(
        event_type="document_uploaded",
        kb_id="global",
        doc_id=doc.id,
        payload={"filename": doc.filename, "file_type": doc.file_type, "folder_path": folder_path},
    )
    return ApiResponse.ok(data=doc)


class BatchUploadItem(BaseModel):
    """批量上传中单个文件的元数据（配合 multipart 使用）。"""
    folder_path: str | None = None   # 该文件所在的原始文件夹路径


class BatchUploadResult(BaseModel):
    total: int
    succeeded: int
    failed: int
    documents: list[dict]   # [{doc_id, filename, folder_path, status}]


@router.post(
    "/documents/batch",
    response_model=ApiResponse[BatchUploadResult],
    dependencies=[Depends(require_permission(Permission.KB_UPLOAD))],
)
async def upload_documents_batch(
    request: Request,
    files: list[UploadFile] = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    批量上传文件（支持文件夹结构）。

    前端使用方式：
      - 用 FormData 一次提交多个文件
      - 每个文件的 folder_path 通过同名字段传入，例如：
          files[0] = File(...)
          folder_paths[0] = "技术文档/2024"
      - 前端应控制每批 10-20 个文件，避免单次请求过大

    后端处理：
      - 并发上传到 S3（asyncio.gather）
      - 批量创建 Document 记录
      - 返回每个文件的处理结果
    """
    decision = rate_limit_governance_center.check(
        route=str(request.url.path),
        user_id=current_user.id,
        api_key=request.headers.get("x-api-key"),
    )
    if not bool(decision["allowed"]):
        raise HTTPException(
            status_code=429,
            detail={"message": "Rate limit exceeded", "reason_code": decision["reason_code"]},
            headers={"Retry-After": str(int(decision["retry_after_sec"]))},
        )

    # 从 form data 中提取 folder_paths（与 files 一一对应）
    form = await request.form()
    folder_paths: list[str | None] = []
    for i in range(len(files)):
        fp = form.get(f"folder_paths[{i}]") or form.get("folder_path")
        folder_paths.append(str(fp) if fp else None)

    from app.services.storage_service import StorageService
    import asyncio

    async def _upload_one(file: UploadFile, folder_path: str | None) -> dict:
        try:
            chunks = []
            while chunk := await file.read(1024 * 1024):
                chunks.append(chunk)
            content = b"".join(chunks)

            content_type = file.content_type or "application/octet-stream"
            file_type = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "unknown"

            storage_path, file_size, content_hash = await StorageService.upload_file(
                file_content=content,
                filename=file.filename,
                content_type=content_type,
                folder_path=folder_path,
            )
            return {
                "filename": file.filename,
                "folder_path": folder_path,
                "storage_path": storage_path,
                "file_path": storage_path,
                "file_type": file_type,
                "file_size": file_size,
                "content_hash": content_hash,
                "error": None,
            }
        except Exception as e:
            return {
                "filename": file.filename,
                "folder_path": folder_path,
                "error": str(e),
            }

    # 并发上传（最多 10 个并发，防止 S3 限流）
    semaphore = asyncio.Semaphore(10)

    async def _upload_with_sem(file, fp):
        async with semaphore:
            return await _upload_one(file, fp)

    upload_results = await asyncio.gather(
        *[_upload_with_sem(f, fp) for f, fp in zip(files, folder_paths)],
        return_exceptions=False,
    )

    # 批量创建 Document 记录
    service = KnowledgeService(db)
    documents = []
    succeeded = 0
    failed = 0

    for result in upload_results:
        if result.get("error"):
            failed += 1
            documents.append({
                "filename": result["filename"],
                "folder_path": result.get("folder_path"),
                "status": "failed",
                "error": result["error"],
            })
            continue

        try:
            doc = Document(
                filename=result["filename"],
                file_type=result["file_type"],
                file_size=result["file_size"],
                storage_path=result["storage_path"],
                file_path=result["file_path"],
                folder_path=result["folder_path"],
                content_hash=result["content_hash"],
                status="pending",
            )
            doc = await service.create_document(doc)
            succeeded += 1
            documents.append({
                "doc_id": doc.id,
                "filename": doc.filename,
                "folder_path": doc.folder_path,
                "status": "pending",
            })
        except Exception as e:
            failed += 1
            documents.append({
                "filename": result["filename"],
                "folder_path": result.get("folder_path"),
                "status": "failed",
                "error": str(e),
            })

    return ApiResponse.ok(data=BatchUploadResult(
        total=len(files),
        succeeded=succeeded,
        failed=failed,
        documents=documents,
    ))


@router.post(
    "/documents/presign",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_permission(Permission.KB_UPLOAD))],
)
async def get_presigned_upload_url(
    filename: str,
    folder_path: str | None = None,
    content_type: str = "application/octet-stream",
    current_user: User = Depends(get_current_user),
):
    """
    获取 S3 预签名上传 URL（用于大文件直传，绕过后端）。

    前端流程：
      1. 调用此接口获取 presigned POST URL + fields
      2. 前端直接 POST 到 S3（不经过后端）
      3. 上传完成后调用 POST /documents/confirm 通知后端创建记录
    """
    from app.services.storage_service import StorageService

    result = StorageService.generate_presigned_upload_url(
        filename=filename,
        folder_path=folder_path,
        content_type=content_type,
    )
    if not result:
        raise HTTPException(status_code=503, detail="S3 未配置，无法生成预签名 URL")

    return ApiResponse.ok(data=result)


class PresignConfirmRequest(BaseModel):
    s3_key: str
    filename: str
    file_size: int
    file_type: str
    folder_path: str | None = None
    content_hash: str | None = None


@router.post(
    "/documents/confirm",
    response_model=ApiResponse[DocumentResponse],
    dependencies=[Depends(require_permission(Permission.KB_UPLOAD))],
)
async def confirm_presigned_upload(
    body: PresignConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    确认预签名直传完成，在数据库中创建 Document 记录。
    配合 /documents/presign 使用（大文件直传场景）。
    """
    service = KnowledgeService(db)
    doc = Document(
        filename=body.filename,
        file_type=body.file_type,
        file_size=body.file_size,
        storage_path=body.s3_key,
        file_path=body.s3_key,
        folder_path=body.folder_path,
        content_hash=body.content_hash,
        status="pending",
    )
    doc = await service.create_document(doc)
    fire_and_forget_write_event(
        event_type="document_uploaded",
        kb_id="global",
        doc_id=doc.id,
        payload={"filename": doc.filename, "s3_key": body.s3_key, "folder_path": body.folder_path},
    )
    return ApiResponse.ok(data=doc)


# ── Multipart Upload（断点续传）────────────────────────────────────────────────

class MultipartInitRequest(BaseModel):
    filename: str
    folder_path: str | None = None
    content_type: str = "application/octet-stream"
    file_size: int  # 字节数，用于前端计算分片数量


class MultipartPartUrlRequest(BaseModel):
    s3_key: str
    upload_id: str
    part_number: int   # 1-based
    expires_in: int = 3600


class MultipartCompleteRequest(BaseModel):
    s3_key: str
    upload_id: str
    filename: str
    file_size: int
    file_type: str
    folder_path: str | None = None
    parts: list[dict]  # [{"PartNumber": 1, "ETag": "..."}, ...]


class MultipartAbortRequest(BaseModel):
    s3_key: str
    upload_id: str


@router.post(
    "/documents/multipart/init",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_permission(Permission.KB_UPLOAD))],
)
async def init_multipart_upload(
    body: MultipartInitRequest,
    current_user: User = Depends(get_current_user),
):
    """
    初始化 S3 Multipart Upload（断点续传第一步）。

    前端流程：
      1. 调用此接口获取 upload_id + s3_key
      2. 将 {upload_id, s3_key, filename, completed_parts: []} 存入 localStorage
      3. 逐片调用 /multipart/part-url 获取预签名 URL，直接 PUT 到 S3
      4. 所有分片完成后调用 /multipart/complete 合并

    分片大小建议：5MB（S3 最小分片限制），最后一片可以更小。
    """
    from app.services.storage_service import StorageService

    result = StorageService.create_multipart_upload(
        filename=body.filename,
        folder_path=body.folder_path,
        content_type=body.content_type,
    )
    if not result:
        raise HTTPException(status_code=503, detail="S3 未配置或初始化失败")

    # 计算建议的分片数量（5MB/片）
    chunk_size = 5 * 1024 * 1024
    total_parts = max(1, (body.file_size + chunk_size - 1) // chunk_size)

    return ApiResponse.ok(data={
        **result,
        "chunk_size": chunk_size,
        "total_parts": total_parts,
    })


@router.post(
    "/documents/multipart/part-url",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_permission(Permission.KB_UPLOAD))],
)
async def get_part_presigned_url(
    body: MultipartPartUrlRequest,
    current_user: User = Depends(get_current_user),
):
    """
    为指定分片生成预签名 PUT URL。
    前端直接 PUT 分片数据到该 URL，响应头中的 ETag 需要保存用于 complete 步骤。
    """
    from app.services.storage_service import StorageService

    if not (1 <= body.part_number <= 10000):
        raise HTTPException(status_code=400, detail="part_number 必须在 1~10000 之间")

    url = StorageService.generate_presigned_part_url(
        s3_key=body.s3_key,
        upload_id=body.upload_id,
        part_number=body.part_number,
        expires_in=body.expires_in,
    )
    if not url:
        raise HTTPException(status_code=503, detail="S3 未配置或生成预签名 URL 失败")

    return ApiResponse.ok(data={"url": url, "part_number": body.part_number})


@router.post(
    "/documents/multipart/list-parts",
    response_model=ApiResponse[list],
    dependencies=[Depends(require_permission(Permission.KB_UPLOAD))],
)
async def list_multipart_parts(
    body: MultipartPartUrlRequest,
    current_user: User = Depends(get_current_user),
):
    """
    查询已上传的分片列表（断点续传恢复时调用）。
    前端用此接口确认哪些分片已成功上传，跳过重传。
    """
    from app.services.storage_service import StorageService

    parts = StorageService.list_uploaded_parts(
        s3_key=body.s3_key,
        upload_id=body.upload_id,
    )
    return ApiResponse.ok(data=parts)


@router.post(
    "/documents/multipart/complete",
    response_model=ApiResponse[DocumentResponse],
    dependencies=[Depends(require_permission(Permission.KB_UPLOAD))],
)
async def complete_multipart_upload(
    body: MultipartCompleteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    合并所有分片，完成 Multipart Upload，并在数据库中创建 Document 记录。
    """
    from app.services.storage_service import StorageService

    result = StorageService.complete_multipart_upload(
        s3_key=body.s3_key,
        upload_id=body.upload_id,
        parts=body.parts,
    )
    if not result:
        raise HTTPException(status_code=500, detail="Multipart 合并失败，请重试")

    service = KnowledgeService(db)
    doc = Document(
        filename=body.filename,
        file_type=body.file_type,
        file_size=body.file_size,
        storage_path=body.s3_key,
        file_path=body.s3_key,
        folder_path=body.folder_path,
        content_hash=result.get("etag"),
        status="pending",
    )
    doc = await service.create_document(doc)
    fire_and_forget_write_event(
        event_type="document_uploaded",
        kb_id="global",
        doc_id=doc.id,
        payload={"filename": doc.filename, "s3_key": body.s3_key, "multipart": True},
    )
    return ApiResponse.ok(data=doc)


@router.post(
    "/documents/multipart/abort",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_permission(Permission.KB_UPLOAD))],
)
async def abort_multipart_upload(
    body: MultipartAbortRequest,
    current_user: User = Depends(get_current_user),
):
    """
    中止 Multipart Upload，清理 S3 临时分片（避免产生存储费用）。
    用户取消上传时调用。
    """
    from app.services.storage_service import StorageService

    ok = StorageService.abort_multipart_upload(
        s3_key=body.s3_key,
        upload_id=body.upload_id,
    )
    return ApiResponse.ok(data={"aborted": ok})
    response_model=ApiResponse[KnowledgeBaseDocumentLink],
    dependencies=[Depends(require_permission(Permission.KB_UPLOAD))],
)
async def link_document(
    kb_id: str,
    doc_id: str,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Link an existing document to a knowledge base and start indexing."""
    decision = rate_limit_governance_center.check(
        route=str(request.url.path),
        user_id=current_user.id,
        api_key=request.headers.get("x-api-key"),
    )
    if not bool(decision["allowed"]):
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Rate limit exceeded",
                "reason_code": decision["reason_code"],
                "dimension": decision["dimension"],
            },
            headers={"Retry-After": str(int(decision["retry_after_sec"]))},
        )

    service = KnowledgeService(db)
    # Check ownership
    await service.get_kb(kb_id)
    if not await service.check_kb_access(kb_id, current_user, level="write"):
        raise ForbiddenError(message="Not authorized to modify this knowledge base", deny_reason="kb_acl_denied")

    link = await service.link_document_to_kb(kb_id, doc_id)

    # Trigger background indexing
    background_tasks.add_task(index_document_task, kb_id, doc_id)
    # Write-side async notification for split read service cache/index sync
    background_tasks.add_task(
        fire_and_forget_write_event,
        event_type="document_linked",
        kb_id=kb_id,
        doc_id=doc_id,
        payload={"action": "index_requested"},
    )

    return ApiResponse.ok(data=link)


@router.get(
    "/batches/{batch_id}/progress",
    dependencies=[Depends(require_permission(Permission.KB_VIEW))],
)
async def stream_batch_progress(
    batch_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    实时推送文档批次处理进度（Server-Sent Events）。

    前端使用方式：
      const es = new EventSource(`/api/v1/knowledge/batches/${batchId}/progress`, {
        headers: { Authorization: `Bearer ${token}` }
      })

      es.addEventListener('progress',  e => updateUI(JSON.parse(e.data)))
      es.addEventListener('file_done', e => markFileDone(JSON.parse(e.data)))
      es.addEventListener('file_failed', e => markFileFailed(JSON.parse(e.data)))
      es.addEventListener('batch_done', e => { showComplete(JSON.parse(e.data)); es.close() })
      es.addEventListener('close', () => es.close())

    事件类型：
      progress     — 进度更新（total/completed/failed/percent）
      file_done    — 单个文件处理完成
      file_failed  — 单个文件处理失败
      batch_done   — 整批完成
      close        — 流结束信号
    """
    from app.services.ingestion.progress_service import stream_batch_progress as _stream

    return StreamingResponse(
        _stream(batch_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )


@router.get(
    "/batches/{batch_id}/progress/snapshot",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_permission(Permission.KB_VIEW))],
)
async def get_batch_progress_snapshot(
    batch_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    获取批次进度快照（轮询备用方案，不需要 SSE 时使用）。
    返回当前 total/completed/failed/percent/status。
    """
    from app.services.ingestion.progress_service import _get_batch_snapshot
    snapshot = await _get_batch_snapshot(batch_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Batch {batch_id} not found")
    return ApiResponse.ok(data=snapshot)


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
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unlink a document from a knowledge base."""
    decision = rate_limit_governance_center.check(
        route=str(request.url.path),
        user_id=current_user.id,
        api_key=request.headers.get("x-api-key"),
    )
    if not bool(decision["allowed"]):
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Rate limit exceeded",
                "reason_code": decision["reason_code"],
                "dimension": decision["dimension"],
            },
            headers={"Retry-After": str(int(decision["retry_after_sec"]))},
        )

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

    background_tasks.add_task(
        fire_and_forget_write_event,
        event_type="document_unlinked",
        kb_id=kb_id,
        doc_id=doc_id,
        payload={"action": "vector_cleanup"},
    )

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
    results = await store.execute_query(cypher, {"kb_id": kb_id})

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
