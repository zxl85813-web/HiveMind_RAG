"""
统一分页 — 请求参数 + 响应包装。

用法:
    @router.get("/", response_model=PaginatedResponse[ConversationListItem])
    async def list_conversations(
        pagination: PaginationParams = Depends(),
        db: AsyncSession = Depends(get_db),
    ):
        items, total = await service.list(pagination)
        return PaginatedResponse.of(items, total, pagination)

参见: REGISTRY.md > 后端 > common > pagination
"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """
    分页请求参数 — 通过 FastAPI Query 自动注入。

    用法:
        async def handler(pagination: PaginationParams = Depends()):
            offset = pagination.offset
            limit = pagination.limit
    """

    page: int = Field(default=1, ge=1, description="页码 (从 1 开始)")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")

    @property
    def offset(self) -> int:
        """计算 SQL OFFSET。"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """SQL LIMIT (即 page_size)。"""
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    """
    统一分页响应格式。

    示例:
        {
            "items": [...],
            "total": 42,
            "page": 1,
            "page_size": 20,
            "total_pages": 3
        }
    """

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def of(cls, items: list[T], total: int, params: PaginationParams) -> "PaginatedResponse[T]":
        """从查询结果构建分页响应。"""
        total_pages = (total + params.page_size - 1) // params.page_size
        return cls(
            items=items,
            total=total,
            page=params.page,
            page_size=params.page_size,
            total_pages=total_pages,
        )
