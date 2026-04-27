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
    from app.sdk.core.logging import trace_id_var

    event_type = payload.get("type", "unknown")
    user_id = user.id if user else "anonymous"
    content = payload.get("payload", {})

    # 🛰️ [Context-Restoration]: 如果是统一日志包，恢复其前端 trace_id 到后端日志上下文
    if event_type == "unified_log" and isinstance(content, dict):
        fe_trace_id = content.get("trace_id")
        if fe_trace_id:
            trace_id_var.set(fe_trace_id)
        
        # 使用结构化方式记录，方便 ELK/日志分析
        logger.bind(
            fe_module=content.get("module"),
            fe_action=content.get("action"),
            fe_level=content.get("level")
        ).info(f"Frontend UnifiedLog: {content.get('msg')} | Meta: {content.get('meta')}")
    else:
        logger.info(f"[Telemetry][{event_type}] Received from user {user_id}: {content}")

    return ApiResponse.ok(data={"status": "accepted"})
