from fastapi import APIRouter
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
        return ApiResponse.error(f"Failed: {str(e)}")


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

