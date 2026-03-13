"""
Retrieval Pipeline — Orchestrator for RAG Retrieval.
"""

from app.core.vector_store import SearchType, VectorDocument
from app.schemas.auth import AuthorizationContext

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
    TruthAlignmentStep,
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
        # Keep a default step chain and expose lightweight A/B variants.
        self._default_steps: list[BaseRetrievalStep] = [
            QueryPreProcessingStep(use_hyde=True, rewrite_query=True),
            GraphRetrievalStep(),  # Inject Graph Facts first
            HybridRetrievalStep(),
            TruthAlignmentStep(),  # 数据治理：真相对齐 (M2.3.1)
            AclFilterStep(),  # 权限校验 (ACL Document Filtering)
            RerankingStep(),
            ParentChunkExpansionStep(),
            ContextualCompressionStep(),  # 压缩上下文 (P2 Performance)
            PromptInjectionFilterStep(),  # 注入防护
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
        top_k: int = 20,
        top_n: int = 5,
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
