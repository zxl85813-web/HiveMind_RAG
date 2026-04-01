from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class Platform(str, Enum):
    FE = "FE"
    BE = "BE"

class EventCategory(str, Enum):
    USER_ACTION = "user_action"
    PERFORMANCE = "performance"
    ERROR = "error"
    SYSTEM = "system"

class UnifiedLog(BaseModel):
    """
    🛰️ [Sync-Source]: 与 frontend/src/core/schema/monitoring.ts 严格对齐
    全链路结构化追踪日志协议
    """
    ts: datetime = Field(default_factory=datetime.utcnow, description="ISO 8601 时间戳")
    level: LogLevel = Field(..., description="日志级别")
    trace_id: str | None = Field(None, description="全链路追踪 ID (UUID)")
    platform: Platform = Field(default=Platform.BE, description="平台来源")
    category: EventCategory = Field(..., description="业务分类")
    module: str = Field(..., description="具体业务组件或模块")
    action: str = Field(..., description="具体动作或事件名")
    msg: str = Field(..., description="人类可读的消息内容")
    meta: dict[str, Any] = Field(default_factory=dict, description="结构化元数据")
    env: str = Field(..., description="运行环境 (prod/dev/mock)")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
