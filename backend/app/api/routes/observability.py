"""
Observability API — RAG 全链路追踪 + 检索质量监控 + 知识库使用分析.

Endpoints:
  GET /observability/traces              — 最近 RAG 查询追踪列表
  GET /observability/retrieval-quality   — 命中率 / 延迟 / 空结果率
  GET /observability/hot-queries         — 热门查询 Top-N
  GET /observability/cold-documents/{kb_id} — 冷门文档 Bottom-N
"""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import desc, select

from app.api.deps import get_current_user, get_db
from app.auth.permissions import Permission, require_permission
from app.common.response import ApiResponse
from app.models.chat import User
from app.models.observability import RAGQueryTrace
from app.services.observability_service import (
    get_cold_documents,
    get_hot_queries,
    get_retrieval_quality,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Raw trace log
# ---------------------------------------------------------------------------


@router.get(
    "/traces",
    response_model=ApiResponse[list[dict[str, Any]]],
    dependencies=[Depends(require_permission(Permission.SYSTEM_CONFIG))],
    summary="最近 RAG 查询追踪",
)
async def list_rag_traces(
    kb_id: str | None = Query(default=None, description="按 KB 过滤"),
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回最近 RAG 查询的全链路 Trace 记录，包含每次检索的步骤日志。"""
    stmt = select(RAGQueryTrace).order_by(desc(RAGQueryTrace.created_at)).limit(limit)
    result = await db.execute(stmt)
    traces = result.scalars().all()

    if kb_id:
        traces = [t for t in traces if kb_id in (t.kb_ids or [])]

    data = [
        {
            "id": t.id,
            "query": t.query,
            "kb_ids": t.kb_ids,
            "retrieval_strategy": t.retrieval_strategy,
            "total_found": t.total_found,
            "returned_count": t.returned_count,
            "has_results": t.has_results,
            "latency_ms": t.latency_ms,
            "is_error": t.is_error,
            "retrieved_doc_ids": t.retrieved_doc_ids,
            "step_traces": t.step_traces,
            "created_at": t.created_at.isoformat(),
        }
        for t in traces
    ]
    return ApiResponse.ok(data=data)


# ---------------------------------------------------------------------------
# Retrieval quality metrics
# ---------------------------------------------------------------------------


@router.get(
    "/retrieval-quality",
    response_model=ApiResponse[dict[str, Any]],
    dependencies=[Depends(require_permission(Permission.KB_VIEW))],
    summary="检索质量监控（命中率 / 延迟 / 空结果率）",
)
async def get_retrieval_quality_stats(
    kb_id: str | None = Query(default=None, description="按 KB 过滤；不填则聚合全局"),
    days: int = Query(default=7, ge=1, le=90, description="统计时间窗口（天）"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    返回指定时间窗口内的检索质量指标：

    - **hit_rate**: 有效命中率（返回 ≥1 条结果的查询占比）
    - **empty_result_rate**: 空结果率（返回 0 条的非错误查询）
    - **avg_latency_ms**: 平均检索延迟（毫秒）
    - **error_rate**: 检索异常率
    - **total_queries**: 总查询次数
    """
    stats = await get_retrieval_quality(db, kb_id=kb_id, days=days)
    return ApiResponse.ok(data=stats)


# ---------------------------------------------------------------------------
# Hot queries
# ---------------------------------------------------------------------------


@router.get(
    "/hot-queries",
    response_model=ApiResponse[list[dict[str, Any]]],
    dependencies=[Depends(require_permission(Permission.KB_VIEW))],
    summary="热门查询 Top-N",
)
async def get_hot_queries_stats(
    kb_id: str | None = Query(default=None, description="按 KB 过滤"),
    limit: int = Query(default=20, ge=1, le=100),
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """返回使用最频繁的查询列表，用于理解用户意图分布与知识库内容覆盖度。"""
    result = await get_hot_queries(db, kb_id=kb_id, limit=limit, days=days)
    return ApiResponse.ok(data=result)


# ---------------------------------------------------------------------------
# Cold documents
# ---------------------------------------------------------------------------


@router.get(
    "/cold-documents/{kb_id}",
    response_model=ApiResponse[list[dict[str, Any]]],
    dependencies=[Depends(require_permission(Permission.KB_VIEW))],
    summary="冷门文档 Bottom-N",
)
async def get_cold_documents_stats(
    kb_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    返回在指定时间窗口内被检索次数最少的文档列表。
    可用于：识别过期文档 / 冗余内容 / 索引质量问题。
    """
    result = await get_cold_documents(db, kb_id=kb_id, limit=limit, days=days)
    return ApiResponse.ok(data=result)
