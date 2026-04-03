import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlmodel import JSON, Field, SQLModel

class PromptStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ROLLBACK = "rollback"

class PromptDefinition(SQLModel, table=True):
    """
    Prompt 版本控制与治理模型 (P0 - Prompt Governance)。
    职责:
    1. 集中存储全系统的 Prompt 模版。
    2. 支持语义版本化 (SemVer) 对比。
    3. 支持一键回滚。
    """
    __tablename__ = "gov_prompt_definitions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    
    # 唯一标识符，例如 "smart_grep_expansion"
    slug: str = Field(index=True)
    
    # 版本号 (建议使用 SemVer, 如 1.0.1)
    version: str = Field(index=True)
    
    # 是否为当前 slug 的主版本
    is_current: bool = Field(default=False, index=True)
    
    # Prompt 原始内容 (含 {query} 等占位符)
    content: str = Field()
    
    # 关联模型 (推荐使用的模型，如 "gpt-4o")
    recommended_model: str | None = Field(default=None)
    
    status: PromptStatus = Field(default=PromptStatus.DRAFT, index=True)
    
    # 变更日志
    change_log: str | None = Field(default=None)
    
    # 元数据 (如作者、预估 Token 数等)
    meta_info: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
