"""
Artifact Schema v1 — TASK-KV-001

统一描述代码 / 文档 / SQL 三类知识资产的最小公共字段。
用于代码知识仓库 (Code Vault) 和 RAG 检索的证据回链。

字段规范:
  artifact_id  唯一标识
  type         资产类型 (code / doc / sql)
  path         相对于仓库根目录的路径
  version      语义版本号，默认 "1.0"
  updated_at   最后更新时间 (UTC)
  tags         标签列表（用于过滤与分类）
  content_hash SHA-256 内容哈希（变更检测用）
  source_kb_id 关联的知识库 ID（可选）
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field


class ArtifactType(StrEnum):
    CODE = "code"
    DOC = "doc"
    SQL = "sql"


class ArtifactSchema(BaseModel):
    """三类资产的最小公共字段 Schema（可直接做 Schema 校验的基础类）。"""

    artifact_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="唯一标识")
    type: ArtifactType
    path: str = Field(..., description="相对仓库根目录的路径，如 backend/app/services/xxx.py")
    version: str = Field(default="1.0", description="语义版本号")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="最后更新时间 (UTC)")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    content_hash: str | None = Field(default=None, description="SHA-256 内容哈希，用于变更检测")
    source_kb_id: str | None = Field(default=None, description="所属知识库 ID")

    @classmethod
    def validate_all_types(cls, data: dict) -> bool:
        """快速校验 data 是否满足三类资产的最小字段要求。"""
        required = {"type", "path"}
        return required.issubset(data.keys())


class CodeArtifact(ArtifactSchema):
    """代码资产：函数 / 类 / 路由 / 模块。"""

    type: Literal[ArtifactType.CODE] = ArtifactType.CODE
    language: str = Field(default="python", description="编程语言")
    symbols: list[str] = Field(default_factory=list, description="提取的函数/类/路由等符号名")
    module_deps: list[str] = Field(default_factory=list, description="直接模块依赖列表")


class DocType(StrEnum):
    ADR = "adr"               # Architecture Decision Record
    REQ = "req"               # 需求文档
    DESIGN = "design"         # 设计文档
    RUNBOOK = "runbook"       # 运维手册
    MEETING = "meeting"       # 会议纪要
    API_SPEC = "api_spec"     # API 规范
    UNKNOWN = "unknown"


class DocArtifact(ArtifactSchema):
    """文档资产：设计文档 / 需求 / ADR / Runbook 等。"""

    type: Literal[ArtifactType.DOC] = ArtifactType.DOC
    doc_type: DocType = Field(default=DocType.UNKNOWN, description="文档分类")
    title: str = Field(default="", description="文档标题")
    summary: str | None = Field(default=None, description="文档摘要（AI 生成）")


class SqlComplexityLevel(StrEnum):
    L1 = "L1"   # 简单
    L2 = "L2"   # 中等
    L3 = "L3"   # 复杂


class SqlArtifact(ArtifactSchema):
    """SQL 资产：查询 / 存储过程 / 视图定义等。"""

    type: Literal[ArtifactType.SQL] = ArtifactType.SQL
    complexity_level: SqlComplexityLevel = Field(default=SqlComplexityLevel.L1, description="SQL 复杂度级别")
    complexity_score: float = Field(default=0.0, description="复杂度分值 (0-100)")
    has_summary_card: bool = Field(default=False, description="是否已生成语义摘要卡")
    summary_card_id: str | None = Field(default=None, description="关联的 SqlSummaryCard ID")
    table_names: list[str] = Field(default_factory=list, description="涉及的表名列表")
    statement_count: int = Field(default=1, description="SQL 语句数量（切分后）")


# --- 工厂函数 ---

def make_code_artifact(path: str, language: str = "python", symbols: list[str] | None = None, tags: list[str] | None = None) -> CodeArtifact:
    return CodeArtifact(path=path, language=language, symbols=symbols or [], tags=tags or [])


def make_doc_artifact(path: str, doc_type: DocType = DocType.UNKNOWN, title: str = "", tags: list[str] | None = None) -> DocArtifact:
    return DocArtifact(path=path, doc_type=doc_type, title=title, tags=tags or [])


def make_sql_artifact(path: str, complexity_level: SqlComplexityLevel = SqlComplexityLevel.L1, tags: list[str] | None = None) -> SqlArtifact:
    return SqlArtifact(path=path, complexity_level=complexity_level, tags=tags or [])
