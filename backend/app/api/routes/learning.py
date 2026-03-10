from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.common.response import ApiResponse
from app.services.learning_service import LearningService

router = APIRouter()


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int  # 1 or -1
    comment: str | None = None


@router.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """提交用户反馈。"""
    try:
        await LearningService.record_feedback(
            message_id=request.message_id, rating=request.rating, comment=request.comment
        )
        await LearningService.learn_from_feedback(request.message_id)
        return ApiResponse.ok(message="Feedback received")
    except Exception as e:
        return ApiResponse.error(f"Failed: {e!s}")


@router.get("/subscriptions", response_model=ApiResponse)
async def list_subscriptions():
    """获取订阅列表。"""
    subs = await LearningService.get_subscriptions()
    return ApiResponse.ok(data=subs)


class AddSubscriptionRequest(BaseModel):
    topic: str


@router.post("/subscriptions", response_model=ApiResponse)
async def add_subscription(request: AddSubscriptionRequest):
    """添加订阅。"""
    sub = await LearningService.add_subscription(request.topic)
    return ApiResponse.ok(data=sub)


@router.delete("/subscriptions/{sub_id}", response_model=ApiResponse)
async def delete_subscription(sub_id: str):
    """删除订阅。"""
    await LearningService.delete_subscription(sub_id)
    return ApiResponse.ok(message="Deleted")


@router.get("/discoveries", response_model=ApiResponse)
async def list_discoveries():
    """获取技术发现列表。"""
    discoveries = await LearningService.get_discoveries()
    return ApiResponse.ok(data=discoveries)


@router.post("/daily-cycle", response_model=ApiResponse)
async def run_daily_cycle():
    """执行一次每日自省学习循环并生成学习报告。"""
    result = await LearningService.run_daily_learning_cycle()
    return ApiResponse.ok(data=result.model_dump(), message="Daily learning cycle completed")


class DailyReportsQuery(BaseModel):
    limit: int = 7


@router.get("/daily-reports", response_model=ApiResponse)
async def list_daily_reports(limit: int = 7):
    """列出最近生成的每日学习报告文件。"""
    from pathlib import Path

    from app.core.config import settings

    repo_root = Path(__file__).resolve().parents[4]
    report_dir = repo_root / settings.SELF_LEARNING_REPORT_DIR
    if not report_dir.exists():
        return ApiResponse.ok(data=[])

    files = sorted(report_dir.glob("*.md"), reverse=True)
    data = [str(f.relative_to(repo_root)).replace("\\", "/") for f in files[: max(1, limit)]]
    return ApiResponse.ok(data=data)


@router.get("/daily-report-content", response_model=ApiResponse)
async def get_daily_report_content(report_path: str):
    """读取指定日报 Markdown 内容，用于前端预览。"""
    try:
        content = LearningService.read_report_content(report_path)
        return ApiResponse.ok(data={"report_path": report_path, "content": content})
    except FileNotFoundError:
        return ApiResponse.ok(data={"report_path": report_path, "content": ""}, message="Report not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid report path: {e!s}") from e
