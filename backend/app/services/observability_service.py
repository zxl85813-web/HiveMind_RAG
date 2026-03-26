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
import json
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

_background_tasks: set[asyncio.Task] = set()


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
    import hashlib

    try:
        async with async_session_factory() as session:
            # 🔒 [Integrity] Fetch the last record's hash to form the chain
            from sqlalchemy import desc
            last_stmt = select(RAGQueryTrace).order_by(desc(RAGQueryTrace.created_at)).limit(1)
            last_res = await session.execute(last_stmt)
            last_record = last_res.scalar_one_or_none()
            p_hash = last_record.h_integrity if last_record else "0000000000000000000000000000000000000000000000000000000000000000"

            # Prepare integrity content (minimal context for proof of existence/intent)
            payload = f"{p_hash}|{query}|{user_id}|{total_found}"
            h_integrity = hashlib.sha256(payload.encode()).hexdigest()

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
                p_hash=p_hash,
                h_integrity=h_integrity
            )
            session.add(trace)
            await session.commit()
        logger.debug(f"[AuditIntegrity] Recorded trace with signature {h_integrity[:8]}")
    except Exception as exc:  # pragma: no cover
        logger.warning(f"[ObservabilityService] Failed to persist RAG trace: {exc}")


def fire_and_forget_trace(**kwargs: Any) -> None:
    """Schedule record_rag_trace without blocking the caller."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = loop.create_task(record_rag_trace(**kwargs))
            _background_tasks.add(task)
            task.add_done_callback(_background_tasks.discard)
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
    return [{"query": q, "count": c, "rank": rank + 1} for rank, (q, c) in enumerate(counter.most_common(limit))]


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


async def get_memory_lifecycle_stats(db: AsyncSession) -> dict[str, Any]:
    """获取情节记忆的生命周期统计数据 (EP-010)."""
    from sqlalchemy import func

    from app.models.episodic import EpisodicMemory

    # 1. 总量统计
    total_count_stmt = select(func.count(EpisodicMemory.id))
    total_count = (await db.execute(total_count_stmt)).scalar() or 0

    # 2. 活跃度统计 (Temperature > 0.5)
    active_count_stmt = select(func.count(EpisodicMemory.id)).where(EpisodicMemory.temperature > 0.5)
    active_count = (await db.execute(active_count_stmt)).scalar() or 0

    # 3. 召回率统计 (Recall count > 0)
    recalled_count_stmt = select(func.count(EpisodicMemory.id)).where(EpisodicMemory.recall_count > 0)
    recalled_count = (await db.execute(recalled_count_stmt)).scalar() or 0

    # 4. 平均热度
    avg_temp_stmt = select(func.avg(EpisodicMemory.temperature))
    avg_temp = (await db.execute(avg_temp_stmt)).scalar() or 0

    return {
        "total_episodes": total_count,
        "active_episodes": active_count,
        "recalled_episodes": recalled_count,
        "utilization_rate": round(recalled_count / total_count, 2) if total_count > 0 else 0.0,
        "avg_temperature": round(float(avg_temp), 2),
    }


# ---------------------------------------------------------------------------
# Phase 0 Baseline Tracking
# ---------------------------------------------------------------------------


async def record_baseline_metrics(
    metrics: list[dict[str, Any]], user_id: str | None = None, session_id: str | None = None
) -> None:
    """批量记录前端上传的基线指标。"""
    from app.core.database import async_session_factory
    from app.models.observability import BaselineMetric

    async with async_session_factory() as session:
        for m in metrics:
            metric = BaselineMetric(
                metric_name=m["name"],
                value=m["value"],
                user_id=user_id,
                session_id=session_id,
                context=m.get("context", {}),
            )
            session.add(metric)
        await session.commit()


async def get_baseline_summary(db: AsyncSession) -> dict[str, Any]:
    """
    生成基线指标的统计摘要报告。
    支持 A/B 分组对比 (context ->> 'grp')。
    """
    from sqlalchemy import func

    from app.models.observability import BaselineMetric

    # 聚合查询：按指标名称和实验分组聚合
    # context ->> 'grp' 用于提取 JSON 中的分组信息
    stmt = select(
        BaselineMetric.metric_name,
        func.coalesce(BaselineMetric.context["grp"].as_string(), "control").label("group"),
        func.count(BaselineMetric.id).label("count"),
        func.avg(BaselineMetric.value).label("mean"),
        func.max(BaselineMetric.value).label("max"),
    ).group_by(BaselineMetric.metric_name, "group")

    result = await db.execute(stmt)
    rows = result.all()

    # 格式化输出为: { "MetricName": { "control": { stats }, "experiment": { stats } } }
    report = {}
    for name, group, count, mean, max_val in rows:
        if name not in report:
            report[name] = {}

        report[name][group] = {
            "count": count,
            "mean": round(float(mean), 2),
            "max": round(float(max_val), 2),
        }
    return report


async def get_ai_diagnostics(db: AsyncSession) -> dict[str, Any]:
    """
    结合基线数据与 LLM，生成架构诊断报告。
    HMER: R (Reflect) - AI 辅助深度反思。
    """
    from app.core.llm import get_llm_service

    summary = await get_baseline_summary(db)
    if not summary:
        return {"status": "INSUFFICIENT_DATA", "analysis": "目前还没有足够的基线采集数据，请先在前端进行一些对话操作。"}

    # 构造诊断 Prompt
    prompt = f"""
你是一名资深 AI 前端架构师。
以下是我们 HiveMind RAG 系统 Phase 0 阶段采集到的用户端真实性能基线数据:

{json.dumps(summary, indent=2, ensure_ascii=False)}

请基于以上数据进行“架构巡检”，输出一份诊断报告。要求如下:
1. 诊断现状: 重点关注 TTFT (首字延迟) 和 P95 延迟。根据行业标准(TTFT < 800ms 为佳)判断当前性能水平。
2. 根因推测:
   - 如果 TTFT 很高，推测是否是由于 RAG 链路太长或服务端推理首包太慢。
   - 如果 List Fetch 很高，推测是否是由于后端数据库索引缺失或前端缺乏持久化缓存。
3. 重构建议: 针对上述问题，给出 2-3 条具体的 HMER Phase 2/3 重构建议（例如：引入 IndexedDB, 增加流式断点续传, 实现推测性预加载）。
4. 风险评估: 给出总体健康度等级 (HEALTHY | WARNING | CRITICAL)。

请用 Markdown 格式输出。
    """

    llm = get_llm_service()
    analysis = await llm.chat_complete([{"role": "user", "content": prompt}], temperature=0.3)

    # 简单的风险判定逻辑
    status = "HEALTHY"
    ttft_metric = summary.get("TTFT (Baseline)", {})
    ttft = ttft_metric.get("mean", 0)

    if ttft > 1500:
        status = "CRITICAL"
    elif ttft > 800:
        status = "WARNING"

    return {"status": status, "metrics_snapshot": summary, "analysis": analysis}


async def get_hmer_phase_gate(phase: int, db: AsyncSession) -> dict[str, Any]:
    """
    HMER: R (Reflect) - 阶段性准出审计。
    评估当前阶段是否完成，并给出转入下一阶段的反思建议。
    """
    from app.core.llm import get_llm_service

    summary = await get_baseline_summary(db)

    prompt = f"""
你是一名 AI 架构审计员。正在对 HMER (Hypothesis-Measure-Experiment-Reflect) 体系的 Phase {phase} 进行准出审计。

### 当前阶段背景:
Phase 0: 基线性能采集与瓶颈定位。目标是获得真实延迟证据。

### 实时基线指标摘要:
{json.dumps(summary, indent=2, ensure_ascii=False)}

### 审计任务:
1. 准出评估: 样本量是否足够? 指标是否有代表性?
2. 瓶颈反思: 根据 P95 和均值，当前系统最急需重构的“出血点”在哪里?
3. 下一步指令: 如果进入 Phase 1 (Architecture Design)，我们应该重点优化哪一套流程?
4. 反思提问: 抛出 1-2 个深刻的问题，引导架构师进行深度思考（例如：我们追求延迟降低，是否会牺牲数据的最终一致性?）。

请以“架构师审计周报”的口吻，使用 Markdown 输出。
    """

    llm = get_llm_service()
    report = await llm.chat_complete([{"role": "user", "content": prompt}], temperature=0.5)

    return {"phase": phase, "audit_report": report, "ready_to_proceed": len(summary) > 0}
