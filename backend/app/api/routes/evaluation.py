from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.common.response import ApiResponse
from app.models.evaluation import BadCase, EvaluationReport, EvaluationSet
from app.services.evaluation import EvaluationService

router = APIRouter()


class TestsetCreate(BaseModel):
    kb_id: str
    name: str
    count: int = 10


@router.post("/testset", response_model=ApiResponse[str])
async def create_testset(
    data: TestsetCreate, background_tasks: BackgroundTasks, db: AsyncSession = Depends(deps.get_db)
):
    """Trigger background generation of a ground-truth testset."""
    from app.core.database import get_db_session

    async def bg_gen():
        async for db_session in get_db_session():
            await EvaluationService.generate_testset(db_session, data.kb_id, data.name, data.count)
            break

    background_tasks.add_task(bg_gen)
    return ApiResponse.ok(message="Testset generation started in background")


@router.get("/testsets", response_model=ApiResponse[list[EvaluationSet]])
async def get_testsets(db: AsyncSession = Depends(deps.get_db)):
    """List all available evaluation sets."""
    from sqlmodel import select

    res = await db.execute(select(EvaluationSet))
    return ApiResponse.ok(data=res.scalars().all())


class EvaluationRun(BaseModel):
    model_name: str | None = "gpt-3.5-turbo"


@router.post("/{set_id}/evaluate", response_model=ApiResponse[str])
async def run_evaluation(
    set_id: str, data: EvaluationRun, background_tasks: BackgroundTasks, db: AsyncSession = Depends(deps.get_db)
):
    """Trigger background evaluation run with specified model."""
    from app.core.database import get_db_session

    async def bg_eval():
        async for db_session in get_db_session():
            await EvaluationService.run_evaluation(db_session, set_id, model_name=data.model_name)
            break

    background_tasks.add_task(bg_eval)
    return ApiResponse.ok(message=f"Evaluation run for {data.model_name} started in background")


@router.get("/reports", response_model=ApiResponse[list[EvaluationReport]])
async def get_reports(db: AsyncSession = Depends(deps.get_db)):
    """List all evaluation reports."""
    from sqlmodel import select

    res = await db.execute(select(EvaluationReport).order_by(EvaluationReport.created_at.desc()))
    return ApiResponse.ok(data=res.scalars().all())


@router.get("/reports/{report_id}", response_model=ApiResponse[EvaluationReport])
async def get_report_details(report_id: str, db: AsyncSession = Depends(deps.get_db)):
    """Get detailed results for a specific report."""
    report = await db.get(EvaluationReport, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ApiResponse.ok(data=report)


class BadCaseUpdate(BaseModel):
    status: str
    expected_answer: str | None = None
    reason: str | None = None


@router.get("/badcases", response_model=ApiResponse[list[BadCase]])
async def get_badcases(db: AsyncSession = Depends(deps.get_db)):
    """List all bad cases tracked from user feedback or failed evals."""
    from sqlmodel import select

    res = await db.execute(select(BadCase).order_by(BadCase.created_at.desc()))
    return ApiResponse.ok(data=res.scalars().all())


@router.put("/badcases/{case_id}", response_model=ApiResponse[BadCase])
async def update_badcase(case_id: str, update_data: BadCaseUpdate, db: AsyncSession = Depends(deps.get_db)):
    """Update BadCase status, expected answer, or reason."""
    case = await db.get(BadCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="BadCase not found")

    case.status = update_data.status
    if update_data.expected_answer is not None:
        case.expected_answer = update_data.expected_answer
    if update_data.reason is not None:
        case.reason = update_data.reason

    db.add(case)
    await db.commit()
    await db.refresh(case)
    return ApiResponse.ok(data=case)


@router.delete("/badcases/{case_id}", response_model=ApiResponse[str])
async def delete_badcase(case_id: str, db: AsyncSession = Depends(deps.get_db)):
    """Delete a BadCase."""
    case = await db.get(BadCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="BadCase not found")
    await db.delete(case)
    await db.commit()
    return ApiResponse.ok(message="Deleted successfully")


@router.get("/stats/kb/{kb_id}", response_model=ApiResponse[dict[str, Any]])
async def get_kb_health_stats(kb_id: str, db: AsyncSession = Depends(deps.get_db)):
    """Get health score and trend data for a specific Knowledge Base."""
    from sqlmodel import select

    stmt = select(EvaluationReport).where(EvaluationReport.kb_id == kb_id).order_by(EvaluationReport.created_at.asc())
    res = await db.execute(stmt)
    reports = list(res.scalars().all())

    if not reports:
        return ApiResponse.ok(data={"score": 0.0, "reports_count": 0, "trend": [], "status": "no_data"})

    avg_score = sum(r.total_score for r in reports) / len(reports)
    avg_faithfulness = sum(r.faithfulness for r in reports) / len(reports)
    avg_relevance = sum(r.answer_relevance for r in reports) / len(reports)

    trend = [
        {
            "timestamp": r.created_at.isoformat(),
            "score": r.total_score,
            "faithfulness": r.faithfulness,
            "relevance": r.answer_relevance,
        }
        for r in reports
    ]

    return ApiResponse.ok(
        data={
            "score": avg_score,
            "faithfulness": avg_faithfulness,
            "relevance": avg_relevance,
            "reports_count": len(reports),
            "trend": trend,
            "status": "healthy" if avg_score > 0.7 else "warning" if avg_score > 0.4 else "critical",
        }
    )


# ============================================================
#  GOV-EXP-001: A/B Execution Variant Experiment Endpoints
# ============================================================


@router.get("/ab/summary", response_model=ApiResponse[dict[str, Any]])
async def get_ab_summary():
    """
    GOV-EXP-001 A/B 实验汇总报告。

    比较 monolithic（集中思考）vs react（分散 Think→Act→Observe）两种模式的：
    - 平均思考耗时（ms）
    - 每次请求 LLM 调用次数
    - 平均质量分
    - 当前领先的模式及耗时节省百分比
    """
    from app.services.evaluation.ab_tracker import ab_tracker

    summary = ab_tracker.get_summary()
    return ApiResponse.ok(data=summary)


@router.get("/ab/records", response_model=ApiResponse[list[dict[str, Any]]])
async def get_ab_records(limit: int = 100):
    """
    GOV-EXP-001 A/B 原始记录列表（最新 N 条）。

    每条记录包含：variant、agent_name、total_think_ms、num_llm_calls、quality_score 等。
    """
    from dataclasses import asdict

    from app.services.evaluation.ab_tracker import ab_tracker

    with ab_tracker._lock:
        records = list(ab_tracker._records)

    recent = records[-limit:][::-1]  # 最新的在前
    return ApiResponse.ok(data=[asdict(r) for r in recent])
