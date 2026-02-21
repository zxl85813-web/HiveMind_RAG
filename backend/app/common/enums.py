"""
通用枚举 — 跨模块共享的枚举类型。

只放真正被 2 个以上模块使用的枚举。
单模块专用枚举应放在对应模块内。

参见: REGISTRY.md > 后端 > common > enums
"""

from enum import Enum


class Status(str, Enum):
    """通用状态 — 适用于文档处理、任务执行等。"""

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    """通用优先级。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SortOrder(str, Enum):
    """排序方向。"""

    ASC = "asc"
    DESC = "desc"
