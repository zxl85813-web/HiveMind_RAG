"""
Model 基类 Mixin — 所有 SQLModel 共享的字段和行为。

用法:
    class MyModel(TimestampMixin, SQLModel, table=True):
        id: str = Field(default_factory=generate_id, primary_key=True)
        name: str

参见: REGISTRY.md > 后端 > common > base
"""

import uuid
from datetime import UTC, datetime

from sqlmodel import Field


def generate_id() -> str:
    """生成标准 UUID v4 字符串。全项目统一使用此函数生成 ID。"""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    """生成 UTC 时间。全项目统一使用此函数获取当前时间。"""
    return datetime.now(UTC)


class TimestampMixin:
    """
    时间戳 Mixin — 自动添加 created_at / updated_at。

    所有数据模型都应使用:
        class User(TimestampMixin, SQLModel, table=True):
            ...
    """

    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class SoftDeleteMixin:
    """
    软删除 Mixin — 标记删除而非物理删除。

    用法:
        class Document(SoftDeleteMixin, TimestampMixin, SQLModel, table=True):
            ...

    查询时需过滤: WHERE is_deleted = False
    """

    is_deleted: bool = Field(default=False)
    deleted_at: datetime | None = Field(default=None)
