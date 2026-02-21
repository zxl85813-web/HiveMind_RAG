"""
Retrieval Service — Orchestrations search and reranking.

所属模块: services
依赖模块: core.vector_store, core.reranker
注册位置: REGISTRY.md > Services > RetrievalService
"""
from typing import List, Optional
from loguru import logger
from app.core.vector_store import get_vector_store, VectorDocument, SearchType
from app.core.reranker import get_reranker

class RetrievalService:
    """
    Handles the full retrieval pipeline:
    1. Hybrid Search (Vector + Keyword)
    2. Candidate Selection (Top K)
    3. Re-ranking (Cross-Encoder)
    4. Metadata Filtering
    """

    def __init__(self):
        self.vector_store = get_vector_store()
        self.reranker = get_reranker()

    async def retrieve(
        self, 
        query: str, 
        collection_names: List[str], 
        top_k: int = 20, 
        top_n: int = 5,
        search_type: str = SearchType.HYBRID
    ) -> List[VectorDocument]:
        """
        Retrieve documents from one or more collections.
        """
        all_candidates: List[VectorDocument] = []
        
        # 1. Multi-Collection Retrieval
        # TODO: Ideally optimize this with parallel async or single filtered query if supported
        for collection in collection_names:
            try:
                # Get more candidates for reranking (e.g. 2x requested top_n)
                # Or use top_k per collection
                if not collection: continue
                
                docs = await self.vector_store.search(
                    query=query,
                    search_type=search_type,
                    k=top_k,
                    collection_name=collection
                )
                all_candidates.extend(docs)
                
            except Exception as e:
                logger.warning(f"Retrieval failed for collection {collection}: {e}")

        if not all_candidates:
            return []

        # deduplicate by content or ID if possible
        # MockVectorStore doesn't return IDs easily in search result objects (Metadata has doc_id)
        unique_candidates = {d.page_content: d for d in all_candidates}.values()
        candidates_list = list(unique_candidates)
        
        logger.info(f"🔍 Found {len(candidates_list)} candidates from {len(collection_names)} collections")

        # 2. Re-Ranking (Precision)
        # Using Cross-Encoder (Mock)
        ranked_docs = await self.reranker.rerank(
            query=query, 
            documents=candidates_list, 
            top_n=top_n
        )
        
        logger.info(f"✨ Reranked Top {len(ranked_docs)}")
        
        return ranked_docs

# Singleton instance
_retrieval_service = RetrievalService()

def get_retrieval_service() -> RetrievalService:
    return _retrieval_service
