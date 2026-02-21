"""
统一 API 响应包装 — 标准化所有 API 返回格式。

成功响应:
    {
        "success": true,
        "data": { ... },
        "message": "OK"
    }

错误响应: (由 core/exceptions.py 的全局处理器生成)
    {
        "success": false,
        "error_code": "NOT_FOUND",
        "message": "Resource not found",
        "detail": {}
    }

参见: REGISTRY.md > 后端 > common > response
"""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    统一 API 成功响应。

    用法:
        @router.post("/", response_model=ApiResponse[KBResponse])
        async def create_kb(...):
            kb = await service.create(...)
            return ApiResponse.ok(kb)
    """

    success: bool = True
    data: T | None = None
    message: str = "OK"

    @classmethod
    def ok(cls, data: Any = None, message: str = "OK") -> "ApiResponse":
        """构建成功响应。"""
        return cls(success=True, data=data, message=message)

    @classmethod
    def created(cls, data: Any = None) -> "ApiResponse":
        """构建创建成功响应。"""
        return cls(success=True, data=data, message="Created")

    @classmethod
    def deleted(cls) -> "ApiResponse":
        """构建删除成功响应。"""
        return cls(success=True, data=None, message="Deleted")
