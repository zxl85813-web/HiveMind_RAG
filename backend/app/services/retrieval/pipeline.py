"""
Retrieval Pipeline — Orchestrator for RAG Retrieval.
"""

from app.core.vector_store import SearchType, VectorDocument
from app.schemas.auth import AuthorizationContext
from app.services.knowledge.sql.retrieval_chain import SqlSummaryFirstStep

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
    RRFHybridStep,
    SearchSubagentsStep,
    TruthAlignmentStep,
)


class RetrievalPipeline:
    """
    Standard RAG Retrieval Pipeline.
    Steps:
    1. Query Analysis & Expansion
    2. Graph Retrieval (Inject Facts)
    3. Search Subagents (parallel sub-query retrieval for ambiguous queries) [2.1H]
    4. RRF Hybrid Retrieval — BM25 + Vector with Reciprocal Rank Fusion [2.1H]
    5. Truth Alignment (GOV-001)
    6. ACL Filter
    7. Cross-Encoder Reranking: Top 150 → Top 20 [2.1H Contextual Reranking P0]
    8. Parent Chunk Expansion
    9. Contextual Compression
    10. Prompt Injection Filter
    """

    def __init__(self):
        self._default_steps: list[BaseRetrievalStep] = [
            QueryPreProcessingStep(use_hyde=True, rewrite_query=True),
            GraphRetrievalStep(),           # Inject Graph Facts first
            SqlSummaryFirstStep(),          # SQL 摘要优先检索（TASK-KV-006）
            SearchSubagentsStep(),          # 2.1H: parallel sub-query sub-agents
            RRFHybridStep(),                # 2.1H: BM25 + Vector + RRF fusion
            TruthAlignmentStep(),           # 数据治理：真相对齐 (M2.3.1)
            AclFilterStep(),                # 权限校验 (ACL Document Filtering)
            RerankingStep(),                # 2.1H: Cross-Encoder Top 150→20
            ParentChunkExpansionStep(),
            ContextualCompressionStep(),    # 压缩上下文 (P2 Performance)
            PromptInjectionFilterStep(),    # 注入防护
        ]

    def _resolve_steps(self, variant: str) -> list[BaseRetrievalStep]:
        """Resolve retrieval chain by variant for A/B experiments."""
        if variant == "ab_no_graph":
            return [
                QueryPreProcessingStep(use_hyde=True, rewrite_query=True),
                HybridRetrievalStep(),
                AclFilterStep(),
                RerankingStep(),
                ParentChunkExpansionStep(),
                ContextualCompressionStep(),
                PromptInjectionFilterStep(),
            ]

        if variant == "ab_no_compress":
            return [
                QueryPreProcessingStep(use_hyde=True, rewrite_query=True),
                GraphRetrievalStep(),
                HybridRetrievalStep(),
                TruthAlignmentStep(),
                AclFilterStep(),
                RerankingStep(),
                ParentChunkExpansionStep(),
                PromptInjectionFilterStep(),
            ]

        return self._default_steps

    async def run(
        self,
        query: str,
        collection_names: list[str],
        top_k: int = 150,   # 2.1H Contextual Reranking P0: recall 150 candidates
        top_n: int = 20,    # 2.1H Contextual Reranking P0: inject top 20 after rerank
        search_type: str = SearchType.HYBRID,
        user_id: str | None = None,
        is_admin: bool = False,
        auth_context: AuthorizationContext | None = None,
        variant: str = "default",
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
            auth_context=auth_context,
        )

        steps = self._resolve_steps(variant)
        ctx.log("Pipeline", f"variant={variant} steps={len(steps)}")

        for step in steps:
            await step.execute(ctx)

        return ctx.final_results, ctx.trace_log


# Expose as Singleton Service
_pipeline = RetrievalPipeline()


def get_retrieval_service() -> RetrievalPipeline:
    return _pipeline
