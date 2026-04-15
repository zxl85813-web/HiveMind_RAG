from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.common.response import ApiResponse
from app.models.evaluation import BadCase, EvaluationReport, EvaluationSet
from app.models.evolution import CognitiveDirective
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
    apply_reflection: bool = False


@router.post("/{set_id}/evaluate", response_model=ApiResponse[str])
async def run_evaluation(
    set_id: str, data: EvaluationRun, background_tasks: BackgroundTasks, db: AsyncSession = Depends(deps.get_db)
):
    """Trigger background evaluation run with specified model."""
    from app.core.database import get_db_session

    async def bg_eval():
        async for db_session in get_db_session():
            await EvaluationService.run_evaluation(
                db_session, set_id, model_name=data.model_name, apply_reflection=data.apply_reflection
            )
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
    """List all bad cases with AI-generated guidance for annotators."""
    from sqlmodel import select
    from app.core.llm import get_llm_service
    import json

    res = await db.execute(select(BadCase).order_by(BadCase.created_at.desc()))
    cases = res.scalars().all()
    
    # Optional: Enhance with guidance if missing (just-in-time enrichment)
    # In production, this would be computed once at record time.
    return ApiResponse.ok(data=cases)


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


@router.post("/badcases/{case_id}/promote", response_model=ApiResponse[dict[str, Any]])
async def promote_badcase_to_gold(case_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(deps.get_db)):
    """
    HITL Evolution: Promote a corrected BadCase to Gold Testset AND trigger cognitive learning.
    """
    from app.services.evolution.experience_learner import experience_learner
    
    # 1. Promote to Testset (Benchmark loop)
    item = await EvaluationService.promote_bad_case_to_testset(db, case_id)
    
    # 2. Trigger Learning (Directive loop) in background
    async def bg_learn():
        from app.core.database import get_db_session
        async for db_session in get_db_session():
            await experience_learner.learn_from_correction(db_session, case_id)
            break
            
    background_tasks.add_task(bg_learn)
    
    return ApiResponse.ok(data={
        "item_id": item.id,
        "set_id": item.set_id,
        "message": "Promoted to Benchmark and queued for Cognitive Learning"
    })


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

@router.get("/governance/summary", response_model=ApiResponse[dict[str, Any]])
async def get_governance_summary(db: AsyncSession = Depends(deps.get_db)):
    """获取智体治理中心汇总数据。"""
    from sqlmodel import select, func
    
    # 1. L3 分数统计
    reports_stmt = select(EvaluationReport).order_by(EvaluationReport.created_at.desc()).limit(10)
    reports_res = await db.execute(reports_stmt)
    recent_reports = list(reports_res.scalars().all())
    
    avg_l3 = sum(r.total_score for r in recent_reports) / len(recent_reports) if recent_reports else 0.0
    
    # 2. 进化指令统计
    directives_stmt = select(func.count(CognitiveDirective.id))
    directives_count_res = await db.execute(directives_stmt)
    total_directives = directives_count_res.scalar() or 0
    
    # 3. BadCase 统计
    badcases_stmt = select(func.count(BadCase.id))
    badcases_count_res = await db.execute(badcases_stmt)
    total_badcases = badcases_count_res.scalar() or 0
    
    # 4. 最近进化动态
    latest_directives_stmt = select(CognitiveDirective).order_by(CognitiveDirective.updated_at.desc()).limit(5)
    latest_directives_res = await db.execute(latest_directives_stmt)
    latest_directives = list(latest_directives_res.scalars().all())

    return ApiResponse.ok(data={
        "l3_avg_score": round(avg_l3, 2),
        "active_directives_count": total_directives,
        "total_badcases": total_badcases,
        "latest_directives": latest_directives,
        "quality_status": "stable" if avg_l3 > 0.75 else "degrading"
    })

@router.get("/directives", response_model=ApiResponse[list[CognitiveDirective]])
async def get_cognitive_directives(db: AsyncSession = Depends(deps.get_db)):
    """获取所有已提炼的认知进化指令。"""
    from sqlmodel import select
    res = await db.execute(select(CognitiveDirective).order_by(CognitiveDirective.updated_at.desc()))
    return ApiResponse.ok(data=res.scalars().all())


class DirectiveUpdate(BaseModel):
    directive: str | None = None
    status: str | None = None  # pending, approved, rejected
    is_active: bool | None = None


@router.put("/directives/{directive_id}", response_model=ApiResponse[CognitiveDirective])
async def update_directive(
    directive_id: str, data: DirectiveUpdate, db: AsyncSession = Depends(deps.get_db)
):
    """人工审计：更新、批准或禁用认知指令。"""
    directive = await db.get(CognitiveDirective, directive_id)
    if not directive:
        raise HTTPException(status_code=404, detail="Directive not found")

    if data.directive is not None:
        directive.directive = data.directive
    if data.status is not None:
        directive.status = data.status
        # If approved, automatically activate; if rejected, deactivate
        if data.status == "approved":
            directive.is_active = True
        elif data.status == "rejected":
            directive.is_active = False
    if data.is_active is not None:
        directive.is_active = data.is_active

    import datetime
    directive.updated_at = datetime.datetime.utcnow()
    
    db.add(directive)
    await db.commit()
    await db.refresh(directive)
    return ApiResponse.ok(data=directive)


@router.delete("/directives/{directive_id}", response_model=ApiResponse[str])
async def delete_directive(directive_id: str, db: AsyncSession = Depends(deps.get_db)):
    """删除指定的认知指令。"""
    directive = await db.get(CognitiveDirective, directive_id)
    if not directive:
        raise HTTPException(status_code=404, detail="Directive not found")
    await db.delete(directive)
    await db.commit()
    return ApiResponse.ok(message="Directive deleted successfully")


# ─── SME Assistance Endpoints ──────────────────────────────────────────────

class SMEAssistRequest(BaseModel):
    answer: str
    context: str | None = None

@router.post("/sme/assist-claims", response_model=ApiResponse[list[str]])
async def assist_claims(data: SMEAssistRequest):
    """SME 辅助：自动将标准回答拆解为核心事实点。"""
    from app.services.evaluation.claim_extractor import claim_extractor
    claims = await claim_extractor.extract_claims(data.answer)
    return ApiResponse.ok(data=claims)

@router.post("/sme/verify-consistency", response_model=ApiResponse[dict[str, Any]])
async def verify_sme_answer(data: SMEAssistRequest):
    """SME 辅助：校验专家填写的答案是否与系统背景知识库一致。"""
    from app.services.evaluation.claim_extractor import claim_extractor
    if not data.context:
        return ApiResponse.ok(data={"is_consistent": True, "issues": []})
    
    result = await claim_extractor.verify_with_context(data.answer, data.context)
    return ApiResponse.ok(data=result)

@router.post("/sme/submit", response_model=ApiResponse[str])
async def submit_sme_gold_case(data: SMEAssistRequest, db: AsyncSession = Depends(deps.get_db)):
    """SME 辅助：手动提交一个业务专家认定的金色标准。"""
    from app.models.evaluation import EvaluationSet, EvaluationItem
    from sqlmodel import select
    
    # 1. Get or create the Evolution Set
    set_name = "HITL_Evolution_Set"
    stmt = select(EvaluationSet).where(EvaluationSet.name == set_name)
    res = await db.execute(stmt)
    eval_set = res.scalars().first()
    
    if not eval_set:
        # Default to the first KB if no KB is specified, or handle accordingly
        # For simplicity, we'll try to find a default KB
        from app.models.knowledge import KnowledgeBase
        kb_res = await db.execute(select(KnowledgeBase).limit(1))
        kb = kb_res.scalars().first()
        kb_id = kb.id if kb else "default"
        
        eval_set = EvaluationSet(
            kb_id=kb_id, 
            name=set_name, 
            description="Automatically generated from human-corrected or SME-provided cases."
        )
        db.add(eval_set)
        await db.commit()
        await db.refresh(eval_set)
        
    # 2. Create Item
    item = EvaluationItem(
        set_id=eval_set.id,
        question=data.question,
        ground_truth=data.answer,
        reference_context=data.context[:1000] if data.context else None,
        category="sme_manual",
        difficulty=5
    )
    db.add(item)
    await db.commit()
    return ApiResponse.ok(message="Golden case saved successfully")

@router.get("/governance/gates", response_model=ApiResponse[dict[str, Any]])
async def get_governance_gates():
    """
    获取治理门禁 (Governance Gates) 的实时合规状态。
    聚合来自 logs/service_governance/ 的 SG1, SG2, SG3, SG4 报告。
    """
    import json
    import os
    from pathlib import Path
    
    logs_dir = Path("logs/service_governance")
    gates = {
        "SG1": {"name": "Stability Window", "status": "unknown", "passed": False, "details": {}},
        "SG2": {"name": "Resilience CB", "status": "unknown", "passed": False, "details": {}},
        "SG3": {"name": "Cost-Quality Balance", "status": "unknown", "passed": False, "details": {}},
        "SG4": {"name": "Closure Readiness", "status": "unknown", "passed": False, "details": {}}
    }
    
    # 1. SG1: Stability Window
    sg1_path = logs_dir / "gate_sg1_window_report.json"
    if sg1_path.exists():
        try:
            data = json.loads(sg1_path.read_text(encoding="utf-8"))
            gates["SG1"]["status"] = "computed"
            gates["SG1"]["passed"] = data.get("gate_result", {}).get("passed", False)
            gates["SG1"]["details"] = data.get("metrics", {})
        except Exception: pass

    # 2. SG2: Resilience (Step 3)
    sg2_path = logs_dir / "step3_cb_report.json"
    if sg2_path.exists():
        try:
            data = json.loads(sg2_path.read_text(encoding="utf-8"))
            gates["SG2"]["status"] = "computed"
            gates["SG2"]["passed"] = data.get("overall_success", False)
            gates["SG2"]["details"] = {"results": data.get("results", [])}
        except Exception: pass

    # 3. SG3: Cost-Quality (Step 5)
    sg3_path = logs_dir / "step5_sg3_cost_quality_report.json"
    if sg3_path.exists():
        try:
            data = json.loads(sg3_path.read_text(encoding="utf-8"))
            gates["SG3"]["status"] = "computed"
            gates["SG3"]["passed"] = data.get("gate_result", {}).get("passed", False)
            gates["SG3"]["details"] = data.get("metrics", {})
        except Exception: pass

    # 4. SG4: Closure Readiness (Step 7)
    sg4_path = logs_dir / "step7_closure_readiness_report.json"
    if sg4_path.exists():
        try:
            data = json.loads(sg4_path.read_text(encoding="utf-8"))
            gates["SG4"]["status"] = "computed"
            gates["SG4"]["passed"] = data.get("gate_result", {}).get("all_passed", False)
            gates["SG4"]["details"] = data.get("gates", {})
        except Exception: pass

    return ApiResponse.ok(data={
        "gates": gates,
        "overall_status": "READY_ FOR_PROD" if gates["SG4"]["passed"] else "STABILIZING"
    })

