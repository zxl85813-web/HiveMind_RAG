"""
Chat endpoints — SSE streaming for Q&A.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

from app.common.response import ApiResponse

# 这里使用 Any 模拟 User，后续换成 auth 的 Depends
from app.schemas.chat import ChatRequest, ConversationListItem
from app.services.chat_service import ChatService
from app.services.rate_limit_governance import rate_limit_governance_center

from app.api.deps import get_current_user, get_db
from app.models.chat import User
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()


@router.post("/completions")
async def chat_completions(
    request: Request,
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """
    流式对话接口 (Server-Sent Events)。
    """
    logger.info(f"Stream request received from {current_user.username}: {body.message[:20]}...")

    api_key = request.headers.get("x-api-key")
    decision = rate_limit_governance_center.check(
        route=str(request.url.path),
        user_id=current_user.id,
        api_key=api_key,
    )
    if not bool(decision["allowed"]):
        retry_after = int(decision["retry_after_sec"])
        raise HTTPException(
            status_code=429,
            detail={
                "message": "Rate limit exceeded",
                "reason_code": decision["reason_code"],
                "dimension": decision["dimension"],
            },
            headers={"Retry-After": str(retry_after)},
        )

    # 🛰️ [FE-GOV-003]: 提取前端语言偏好
    accept_language = request.headers.get("accept-language")

    # 获取生成器
    generator = ChatService.chat_stream(body, user_id=current_user.id, accept_language=accept_language)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx 禁用缓冲，关键！
        },
    )


@router.get("/conversations", response_model=ApiResponse[list[ConversationListItem]])
async def list_conversations(
    limit: int = 20, 
    offset: int = 0,
    current_user: User = Depends(get_current_user),
):
    """获取会话列表。"""
    try:
        conversations = await ChatService.get_conversations(user_id=current_user.id, limit=limit, offset=offset)
        return ApiResponse.ok(data=conversations)
    except Exception as e:
        logger.error(f"Failed to fetch conversations for {current_user.username}: {e}")
        return ApiResponse.ok(data=[], message="Failed to load history")


@router.get("/conversations/{conversation_id}", response_model=ApiResponse)
async def get_conversation(
    conversation_id: str,
    msg_limit: int = 50,
    msg_offset: int = 0,
):
    """获取单个会话详情。

    [Fix-09] 支持消息分页：msg_limit 控制每页条数（默认 50），
    msg_offset 控制偏移量，用于向前翻页加载更早的消息。
    """
    conv = await ChatService.get_conversation(
        conversation_id, msg_limit=msg_limit, msg_offset=msg_offset
    )
    if not conv:
        return ApiResponse.error(message="Conversation not found", code=404)

    # 使用分页后的消息列表（_paged_messages），而非触发全量 lazy load
    messages = getattr(conv, "_paged_messages", [])
    return ApiResponse.ok(
        data={
            "id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at,
            "updated_at": conv.updated_at,
            "messages": [
                {
                    "id": m.id,
                    "role": m.role,
                    "content": m.content,
                    "created_at": m.created_at,
                    "metadata": m.metadata_json,
                }
                for m in messages
            ],
            "pagination": {
                "limit": msg_limit,
                "offset": msg_offset,
                "has_more": len(messages) == msg_limit,
            },
        }
    )


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除会话。"""
    success = await ChatService.delete_conversation(conversation_id)
    if success:
        return ApiResponse.ok(message="Deleted")
    return ApiResponse.error(message="Delete failed", code=400)


class FeedbackRequest(BaseModel):
    rating: int  # 1 for like, -1 for dislike
    feedback_text: str | None = None


@router.post("/messages/{message_id}/feedback")
async def submit_feedback(message_id: str, req: FeedbackRequest):
    """Provide feedback for a specific AI message."""
    success = await ChatService.record_feedback(message_id, req.rating, req.feedback_text)
    if success:
        return ApiResponse.ok(message="Feedback recorded")
    return ApiResponse.error(message="Message not found or update failed", code=400)
