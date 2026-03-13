"""
Observability Service — RAG 全链路追踪与检索质量分析.

Provides:
  - record_rag_trace:      fire-and-forget writer for each RAG query span
  - get_retrieval_quality: hit rate, avg latency, empty-result rate per KB
  - get_hot_queries:       most-frequent queries per KB
  - get_cold_documents:    documents least retrieved per KB
"""

from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.observability import RAGQueryTrace


# ---------------------------------------------------------------------------
# Write path
# ---------------------------------------------------------------------------


async def record_rag_trace(
    *,
    query: str,
    kb_ids: list[str],
    retrieval_strategy: str,
    total_found: int,
    returned_count: int,
    latency_ms: float,
    retrieved_doc_ids: list[str],
    step_traces: list[str],
    user_id: str | None = None,
    is_error: bool = False,
) -> None:
    """
    Persist a RAG query trace to PostgreSQL.
    Intended to be called as a background task (fire-and-forget).
    """
    from app.core.database import async_session_factory

    trace = RAGQueryTrace(
        query=query,
        kb_ids=kb_ids,
        retrieval_strategy=retrieval_strategy,
        user_id=user_id,
        total_found=total_found,
        returned_count=returned_count,
        has_results=returned_count > 0,
        latency_ms=latency_ms,
        is_error=is_error,
        retrieved_doc_ids=retrieved_doc_ids,
        step_traces=step_traces,
    )
    try:
        async with async_session_factory() as session:
            session.add(trace)
            await session.commit()
    except Exception as exc:  # pragma: no cover
        logger.warning(f"[ObservabilityService] Failed to persist RAG trace: {exc}")


def fire_and_forget_trace(**kwargs: Any) -> None:
    """Schedule record_rag_trace without blocking the caller."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(record_rag_trace(**kwargs))
        else:
            loop.run_until_complete(record_rag_trace(**kwargs))
    except Exception as exc:  # pragma: no cover
        logger.warning(f"[ObservabilityService] Could not schedule trace: {exc}")


# ---------------------------------------------------------------------------
# Read path — aggregation helpers
# ---------------------------------------------------------------------------


async def get_retrieval_quality(
    db: AsyncSession,
    kb_id: str | None = None,
    days: int = 7,
) -> dict[str, Any]:
    """
    Returns:
      hit_rate          — fraction of queries that returned ≥1 result
      avg_latency_ms    — mean query latency over the window
      empty_result_rate — fraction of queries with 0 results
      total_queries     — raw query count
      error_rate        — fraction of queries that raised an exception
    """
    since = datetime.utcnow() - timedelta(days=days)
    stmt = select(RAGQueryTrace).where(RAGQueryTrace.created_at >= since)  # type: ignore[arg-type]
    result = await db.execute(stmt)
    traces = result.scalars().all()

    if kb_id:
        traces = [t for t in traces if kb_id in (t.kb_ids or [])]

    total = len(traces)
    if total == 0:
        return {
            "kb_id": kb_id,
            "period_days": days,
            "total_queries": 0,
            "hit_rate": None,
            "empty_result_rate": None,
            "avg_latency_ms": None,
            "error_rate": None,
        }

    hit_count = sum(1 for t in traces if t.has_results)
    empty_count = sum(1 for t in traces if not t.has_results and not t.is_error)
    error_count = sum(1 for t in traces if t.is_error)
    avg_latency = sum(t.latency_ms for t in traces) / total

    return {
        "kb_id": kb_id,
        "period_days": days,
        "total_queries": total,
        "hit_rate": round(hit_count / total, 4),
        "empty_result_rate": round(empty_count / total, 4),
        "avg_latency_ms": round(avg_latency, 2),
        "error_rate": round(error_count / total, 4),
    }


async def get_hot_queries(
    db: AsyncSession,
    kb_id: str | None = None,
    limit: int = 20,
    days: int = 7,
) -> list[dict[str, Any]]:
    """
    Returns the most-frequently-issued queries in the window, ranked by count.
    """
    since = datetime.utcnow() - timedelta(days=days)
    stmt = select(RAGQueryTrace).where(RAGQueryTrace.created_at >= since)  # type: ignore[arg-type]
    result = await db.execute(stmt)
    traces = result.scalars().all()

    if kb_id:
        traces = [t for t in traces if kb_id in (t.kb_ids or [])]

    counter: Counter[str] = Counter(t.query for t in traces)
    return [
        {"query": q, "count": c, "rank": rank + 1}
        for rank, (q, c) in enumerate(counter.most_common(limit))
    ]


async def get_cold_documents(
    db: AsyncSession,
    kb_id: str,
    limit: int = 20,
    days: int = 30,
) -> list[dict[str, Any]]:
    """
    Returns document IDs that were retrieved the least within the analysis window,
    indicating potentially stale/irrelevant content.
    """
    since = datetime.utcnow() - timedelta(days=days)
    stmt = select(RAGQueryTrace).where(RAGQueryTrace.created_at >= since)  # type: ignore[arg-type]
    result = await db.execute(stmt)
    traces = result.scalars().all()

    traces = [t for t in traces if kb_id in (t.kb_ids or [])]

    doc_counter: Counter[str] = Counter()
    for t in traces:
        if t.retrieved_doc_ids:
            doc_counter.update(t.retrieved_doc_ids)

    # Least-common first
    least_common = doc_counter.most_common()[: -limit - 1 : -1]
    return [
        {"doc_id": doc_id, "retrieval_count": count, "rank": rank + 1}
        for rank, (doc_id, count) in enumerate(reversed(least_common))
    ]
