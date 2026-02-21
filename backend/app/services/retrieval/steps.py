import abc
from typing import List
from app.core.vector_store import get_vector_store, VectorDocument
from app.core.reranker import get_reranker
from .protocol import RetrievalContext

class BaseRetrievalStep(abc.ABC):
    @abc.abstractmethod
    async def execute(self, ctx: RetrievalContext):
        """Execute step and update context"""
        pass

class QueryPreProcessingStep(BaseRetrievalStep):
    """
    ARAG: Analyze query, expand intent, normalize text.
    Similar to 'IngestionParser'.
    """
    async def execute(self, ctx: RetrievalContext):
        # 1. Expand query (Mock: Add lowercase version or expand vague terms)
        ctx.expanded_queries = [ctx.query]
        
        # If query is very short, maybe add context?
        if len(ctx.query) < 5:
            ctx.log("QueryApply", f"Query '{ctx.query}' is short.")
        else:
            # Mock expansion
            # ctx.expanded_queries.append(ctx.query + " definition")
            pass
            
        ctx.log("QueryProc", f"Prepared {len(ctx.expanded_queries)} queries")

class HybridRetrievalStep(BaseRetrievalStep):
    """
    Recall Phase (Retrieval): Retrieve candidates from VectorStore.
    Equivalent to 'Ingestion' but reversed (Store -> Memory).
    """
    async def execute(self, ctx: RetrievalContext):
        store = get_vector_store()
        all_docs = []
        
        for q in ctx.expanded_queries:
            for kb_id in ctx.kb_ids:
                try:
                    docs = await store.search(
                        query=q,
                        search_type=ctx.search_type,
                        k=ctx.top_k,
                        collection_name=kb_id
                    )
                    all_docs.extend(docs)
                except Exception as e:
                    ctx.log("Retrieval", f"Error querying {kb_id}: {e}")
                    
        # Dedup by content
        unique_docs = {}
        for d in all_docs:
            if d.page_content not in unique_docs:
                unique_docs[d.page_content] = d
                
        ctx.candidates = list(unique_docs.values())
        ctx.log("Retrieval", f"Found {len(ctx.candidates)} unique candidates from {len(ctx.kb_ids)} KBs")

class RerankingStep(BaseRetrievalStep):
    """
    Precision Phase (Ranking): Re-rank candidates using Cross-Encoder.
    This ensures Top N results are highly relevant.
    """
    async def execute(self, ctx: RetrievalContext):
        if not ctx.candidates:
            ctx.final_results = []
            return

        reranker = get_reranker()
        
        # Rerank
        ranked = await reranker.rerank(
            query=ctx.query,
            documents=ctx.candidates,
            top_n=ctx.top_n
        )
        ctx.final_results = ranked
        ctx.log("Rerank", f"Selected top {len(ranked)} documents")
