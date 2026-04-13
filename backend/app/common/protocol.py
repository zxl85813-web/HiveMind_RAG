from enum import Enum
from typing import Literal

# 🛡️ [PROTOCOL-LITERALS]: 定义全系统唯一的枚举常量，防止 Success vs success 漂移。
# 后端 Pydantic Model 必须使用这些 Literal 或 Enum。

class GovernanceStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RESOLVED = "resolved"

class SwarmStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    REFLECTING = "reflecting"
    ERROR = "error"

class McpStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"

# 类型别名用于 Pydantic 校验
SystemStatusType = Literal["pending", "processing", "completed", "failed", "cancelled", "resolved"]
McpStatusType = Literal["connected", "disconnected"]
