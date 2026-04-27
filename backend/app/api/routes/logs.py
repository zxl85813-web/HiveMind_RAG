from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Any
from app.sdk.core.logging import logger
from app.common.response import ApiResponse

router = APIRouter()

class FrontendLogEntry(BaseModel):
    level: str
    module: str
    message: str
    trace_id: str | None = None
    data: Any | None = None

class FrontendBatchLog(BaseModel):
    batch: List[FrontendLogEntry]

@router.post("/ingest", response_model=ApiResponse)
async def ingest_frontend_logs(request: FrontendBatchLog):
    """
    [M8.1] 统一日志摄入：接收来自前端的消息、错误与埋点。
    将前端日志泵入一致的 backend/logs/hivemind_*.log 中，实现全链路全栈观测。
    """
    for entry in request.batch:
        # 使用 loguru 的 bind 功能，将前端元数据注入到结构化日志中
        scoped_logger = logger.bind(
            platform="FE",
            module=f"FE:{entry.module}",
            trace_id=entry.trace_id or "fe-anonymous"
        )
        
        level = entry.level.upper()
        msg = f"{entry.message} | data: {entry.data}" if entry.data else entry.message
        
        if level == "ERROR":
            scoped_logger.error(msg)
        elif level == "WARNING":
            scoped_logger.warning(msg)
        elif level == "DEBUG":
            scoped_logger.debug(msg)
        else:
            scoped_logger.info(msg)
            
    return ApiResponse.ok(message=f"Ingested {len(request.batch)} FE log entries")
