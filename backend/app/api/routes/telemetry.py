from typing import Any

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user_optional
from app.common.response import ApiResponse

router = APIRouter()

@router.post("/telemetry", response_model=ApiResponse[dict[str, str]], summary="架构遥测对账收口")
async def post_telemetry(
    payload: dict[str, Any],
    # 🛰️ [Architecture-Gate]: 遥测允许匿名发送（如 PageUnload 时令牌失效），但记录关联
    user: Any = Depends(get_current_user_optional)
):
    """
    接收前端发出的极限遥测包（如 TTFT, 页面关闭埋点）。
    目前直接异步记录到日志，后续可接入 ClickHouse 或 Prometheus。
    """
    from loguru import logger

    event_type = payload.get("type", "unknown")
    user_id = user.id if user else "anonymous"

    logger.info(f"[Telemetry][{event_type}] Received from user {user_id}: {payload.get('payload')}")

    return ApiResponse.ok(data={"status": "accepted"})
