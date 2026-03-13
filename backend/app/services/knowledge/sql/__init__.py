"""
SQL Knowledge Services (TASK-KV-003 ~ KV-006)

  complexity_grader  — SQL 复杂度分级器 (L1/L2/L3)
  splitter           — 长 SQL 切分器（语句边界 + CTE 逻辑段）
  summary_card       — SQL 语义摘要卡 v1（purpose/inputs/outputs/logic/biz_rules/risks/tags/sql_hash）
  retrieval_chain    — 摘要优先检索链 + RetrievalPipeline 集成 Step
"""

from .complexity_grader import ComplexityReport, SqlComplexityGrader, sql_complexity_grader
from .retrieval_chain import (
    EvidenceStatus,
    SqlEvidence,
    SqlSummaryFirstStep,
    SqlSummaryRetrievalChain,
    is_sql_related_query,
    sql_summary_chain,
)
from .splitter import SegmentType, SqlSegment, SqlSplitter, sql_splitter
from .summary_card import SqlSummaryCard, SqlSummaryCardService, sql_summary_card_service

__all__ = [
    # KV-003
    "SqlComplexityGrader",
    "ComplexityReport",
    "sql_complexity_grader",
    # KV-004
    "SqlSplitter",
    "SqlSegment",
    "SegmentType",
    "sql_splitter",
    # KV-005
    "SqlSummaryCardService",
    "SqlSummaryCard",
    "sql_summary_card_service",
    # KV-006
    "SqlSummaryRetrievalChain",
    "SqlSummaryFirstStep",
    "SqlEvidence",
    "EvidenceStatus",
    "is_sql_related_query",
    "sql_summary_chain",
]
