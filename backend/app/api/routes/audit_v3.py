"""
HITL Audit Router (V3 Architecture).

Provides the frontend with a queue of 'flagged' documents for human review.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.api.deps import get_current_user, get_db
from app.common.response import ApiResponse
from app.models.chat import User
from app.models.observability import FileTrace, HITLTask, TraceStatus

router = APIRouter(prefix="/audit", tags=["v3-audit"])


@router.get("/queue", response_model=ApiResponse[list[HITLTask]])
async def get_audit_queue(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all pending human review tasks."""
    stmt = select(HITLTask).where(HITLTask.final_verdict is None).order_by(HITLTask.created_at.desc())
    results = db.execute(stmt).scalars().all()
    return ApiResponse.ok(data=results)


@router.post("/{task_id}/resolve", response_model=ApiResponse[dict])
async def resolve_audit_task(
    task_id: str,
    verdict: str,  # APPROVED, REJECTED, RETRY
    comment: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """User submits a decision for a flagged document."""
    task = db.get(HITLTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Audit task not found")

    trace = db.get(FileTrace, task.trace_id)
    if not trace:
        raise HTTPException(status_code=404, detail="Associated trace not found")

    from datetime import datetime

    task.final_verdict = verdict
    task.reviewed_by = current_user.email
    task.reviewer_comment = comment
    task.reviewed_at = datetime.utcnow()

    # Update Trace Status accordingly
    if verdict == "APPROVED":
        trace.status = TraceStatus.APPROVED
        # Logic to trigger final vectorization stage would go here
    elif verdict == "REJECTED":
        trace.status = TraceStatus.REJECTED
    elif verdict == "RETRY":
        trace.status = TraceStatus.PENDING
        # Logic to re-queue the Celery task

    db.add(task)
    db.add(trace)
    db.commit()

    # Post the human-correction as a reflection to the blackboard
    from app.core.telemetry.blackboard import get_blackboard

    blackboard = get_blackboard()
    await blackboard.post_reflection(
        agent_name="HumanReviewer",
        topic=f"correction:{trace.file_path}",
        content={"verdict": verdict, "comment": comment},
    )

    return ApiResponse.ok(data={"status": "resolved", "verdict": verdict})
