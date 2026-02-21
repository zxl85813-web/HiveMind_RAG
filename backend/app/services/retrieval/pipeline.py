"""
Retrieval Pipeline — Orchestrator for RAG Retrieval.
"""
from typing import List
from .protocol import RetrievalContext
from .steps import BaseRetrievalStep, QueryPreProcessingStep, HybridRetrievalStep, RerankingStep
from app.core.vector_store import VectorDocument, SearchType

class RetrievalPipeline:
    """
    Standard RAG Retrieval Pipeline.
    Steps:
    1. Query Analysis & Expansion
    2. Hybrid Retrieval (Recall)
    3. Cross-Encoder Reranking (Precision)
    """
    
    def __init__(self):
        # Default Pipeline Structure
        self.steps: List[BaseRetrievalStep] = [
            QueryPreProcessingStep(),
            HybridRetrievalStep(),
            RerankingStep()
        ]

    async def run(
        self, 
        query: str, 
        collection_names: List[str],
        top_k: int = 20,
        top_n: int = 5,
        search_type: str = SearchType.HYBRID
    ) -> List[VectorDocument]:
        """
        Execute the retrieval pipeline.
        """
        ctx = RetrievalContext(
            query=query,
            kb_ids=collection_names,
            top_k=top_k,
            top_n=top_n,
            search_type=search_type
        )
        
        for step in self.steps:
            await step.execute(ctx)
            
        return ctx.final_results

# Expose as Singleton Service
_pipeline = RetrievalPipeline()

def get_retrieval_service() -> RetrievalPipeline:
    return _pipeline
