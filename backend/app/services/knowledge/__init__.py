"""
services/knowledge — 知识库业务领域模块

包含:
  - KnowledgeService       KB 和 Document 的 CRUD 持久化
  - GraphExtractor         LLM 实体关系抽取 (GraphRAG Indexing)
  - GraphCommunityService  图谱社区检测与 LLM 摘要 (GraphRAG Querying)
"""

from .graph_community import GraphCommunityService
from .graph_extractor import GraphExtractor
from .kb_service import KnowledgeService

__all__ = ["GraphCommunityService", "GraphExtractor", "KnowledgeService"]
