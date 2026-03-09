"""
Retrieval Pipeline — Orchestrator for RAG Retrieval.
"""

from app.core.vector_store import SearchType, VectorDocument

from .preprocessing import QueryPreProcessingStep
from .protocol import RetrievalContext
from .steps import (
    AclFilterStep,
    BaseRetrievalStep,
    ContextualCompressionStep,
    GraphRetrievalStep,
    HybridRetrievalStep,
    ParentChunkExpansionStep,
    PromptInjectionFilterStep,
    RerankingStep,
)


class RetrievalPipeline:
    """
    Standard RAG Retrieval Pipeline.
    Steps:
    1. Query Analysis & Expansion
    2. Hybrid Retrieval (Recall)
    3. Cross-Encoder Reranking (Precision)
    4. Parent Chunk Expansion (Contextualization)
    5. Contextual Compression (Optimization)
    """

    def __init__(self):
        # Default Pipeline Structure
        self.steps: list[BaseRetrievalStep] = [
            QueryPreProcessingStep(use_hyde=True, rewrite_query=True),
            GraphRetrievalStep(),  # Inject Graph Facts first
            HybridRetrievalStep(),
            AclFilterStep(),  # 权限校验 (ACL Document Filtering)
            RerankingStep(),
            ParentChunkExpansionStep(),
            ContextualCompressionStep(),  # 压缩上下文 (P2 Performance)
            PromptInjectionFilterStep(),  # 注入防护
        ]

    async def run(
        self,
        query: str,
        collection_names: list[str],
        top_k: int = 20,
        top_n: int = 5,
        search_type: str = SearchType.HYBRID,
        user_id: str | None = None,
        is_admin: bool = False,
    ) -> list[VectorDocument]:
        """
        Execute the retrieval pipeline.
        """
        ctx = RetrievalContext(
            query=query,
            kb_ids=collection_names,
            top_k=top_k,
            top_n=top_n,
            search_type=search_type,
            user_id=user_id,
            is_admin=is_admin,
        )

        for step in self.steps:
            await step.execute(ctx)

        return ctx.final_results, ctx.trace_log


# Expose as Singleton Service
_pipeline = RetrievalPipeline()


def get_retrieval_service() -> RetrievalPipeline:
    return _pipeline
