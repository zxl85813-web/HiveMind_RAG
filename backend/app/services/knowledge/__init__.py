"""
services/knowledge — 知识库业务领域模块

包含:
  - KnowledgeService       KB 和 Document 的 CRUD 持久化
  - GraphExtractor         LLM 实体关系抽取 (GraphRAG Indexing)
  - GraphCommunityService  图谱社区检测与 LLM 摘要 (GraphRAG Querying)
"""
from .kb_service import KnowledgeService
from .graph_extractor import GraphExtractor
from .graph_community import GraphCommunityService

__all__ = ["KnowledgeService", "GraphExtractor", "GraphCommunityService"]
