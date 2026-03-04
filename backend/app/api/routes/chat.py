"""
Chat endpoints — SSE streaming for Q&A.
"""

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from loguru import logger

from app.common.response import ApiResponse

# 这里使用 Any 模拟 User，后续换成 auth 的 Depends
from app.schemas.chat import ChatRequest, ConversationListItem
from app.services.chat_service import ChatService

router = APIRouter()

# 临时模拟当前用户
CURRENT_USER_ID = "mock-user-001"


@router.post("/completions")
async def chat_completions(
    request: ChatRequest,
    # TODO: current_user: User = Depends(get_current_user)
):
    """
    流式对话接口 (Server-Sent Events)。

    请求:
        POST /api/chat/completions
        body: { "message": "你好", "conversation_id": null }

    响应:
        text/event-stream
        data: {"type": "content", "delta": "你"}
        ...
    """
    logger.info(f"Stream request received: {request.message[:20]}...")

    # 获取生成器
    generator = ChatService.chat_stream(request, user_id=CURRENT_USER_ID)

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
async def list_conversations(limit: int = 20, offset: int = 0):
    """获取会话列表。"""
    try:
        conversations = await ChatService.get_conversations(user_id=CURRENT_USER_ID, limit=limit, offset=offset)
        return ApiResponse.ok(data=conversations)
    except Exception as e:
        logger.error(f"Failed to fetch conversations: {e}")
        return ApiResponse.ok(data=[], message="Failed to load history")


@router.get("/conversations/{conversation_id}", response_model=ApiResponse)
async def get_conversation(conversation_id: str):
    """获取单个会话详情。"""
    conv = await ChatService.get_conversation(conversation_id)
    if not conv:
        return ApiResponse.error(message="Conversation not found", code=404)
    
    # 将模型转为 Schema (TODO: 这里的转换逻辑在大型项目中通常放在 mapper 或 schema 内部)
    return ApiResponse.ok(data={
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
                "metadata": m.metadata_json # TODO: parse JSON if needed
            } for m in conv.messages
        ]
    })


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """删除会话。"""
    success = await ChatService.delete_conversation(conversation_id)
    if success:
        return ApiResponse.ok(message="Deleted")
    return ApiResponse.error(message="Delete failed", code=400)


from pydantic import BaseModel

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
