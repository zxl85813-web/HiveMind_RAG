"""
Reranker Interface — Re-ranking and Fine-ranking for RAG.

所属模块: core
依赖模块: vector_store
注册位置: REGISTRY.md > Core > Reranker
"""
import abc
from typing import List, Tuple
from app.core.vector_store import VectorDocument

class BaseReranker(abc.ABC):
    """Abstract interface for Reranking models (Cross-Encoder)."""
    
    @abc.abstractmethod
    async def rerank(self, query: str, documents: List[VectorDocument], top_n: int = 5) -> List[VectorDocument]:
        """
        Re-rank a list of documents based on relevance to the query.
        
        Args:
            query: The user query.
            documents: Candidate documents from retrieval.
            top_n: Number of documents to return after reranking.
        """
        pass

class MockReranker(BaseReranker):
    """
    In-memory Mock Reranker.
    Simulates a Cross-Encoder by performing stricter keyword matching 
    and boosting exact phrase matches.
    """
    
    async def rerank(self, query: str, documents: List[VectorDocument], top_n: int = 5) -> List[VectorDocument]:
        if not documents:
            return []
            
        scored_docs: List[Tuple[VectorDocument, float]] = []
        query_terms = set(query.lower().split())
        
        for doc in documents:
            content = doc.page_content.lower()
            score = 0.0
            
            # 1. Exact Phrase Match (High Boost)
            if query.lower() in content:
                score += 10.0
                
            # 2. Key Term Density (Fine-grained)
            for term in query_terms:
                if term in content:
                    score += 1.0
                    
            # 3. Penalize very long docs (if needed) or boost short precise answers
            # Mock heuristic: slightly boost items with Metadata
            if "type" in doc.metadata:
                score += 0.1
                
            scored_docs.append((doc, score))
            
        # Sort desc
        scored_docs.sort(key=lambda x: x[1], reverse=True)
        
        # Debug Log
        # print(f"🔍 [Rerank] Top score: {scored_docs[0][1] if scored_docs else 0}")
        
        return [doc for doc, score in scored_docs[:top_n]]

# Singleton
_global_reranker = MockReranker()

def get_reranker() -> BaseReranker:
    return _global_reranker
