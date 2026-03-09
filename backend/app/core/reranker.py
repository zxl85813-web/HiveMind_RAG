"""
Reranker Interface — Re-ranking and Fine-ranking for RAG.

所属模块: core
依赖模块: vector_store
注册位置: REGISTRY.md > Core > Reranker
"""

import abc
import threading

from app.core.logging import logger
from app.core.vector_store import VectorDocument


class BaseReranker(abc.ABC):
    """Abstract interface for Reranking models (Cross-Encoder)."""

    @abc.abstractmethod
    async def rerank(self, query: str, documents: list[VectorDocument], top_n: int = 5) -> list[VectorDocument]:
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

    async def rerank(self, query: str, documents: list[VectorDocument], top_n: int = 5) -> list[VectorDocument]:
        if not documents:
            return []

        scored_docs: list[tuple[VectorDocument, float]] = []
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


class BGEReranker(BaseReranker):
    """
    Real Cross-Encoder Reranker using HuggingFace / SentenceTransformers.
    Default to BAAI/bge-reranker-base (or a smaller model for MVP).
    """

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3"):
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def _get_model(self):
        # Lazy load to avoid blocking startup if model needs downloading
        if self._model is None:
            with self._lock:
                if self._model is None:
                    try:
                        from sentence_transformers import CrossEncoder

                        logger.info(f"Loading Reranker Model: {self.model_name}...")
                        self._model = CrossEncoder(self.model_name)
                        logger.info(f"Reranker Model {self.model_name} loaded successfully.")
                    except ImportError:
                        logger.error("sentence-transformers not installed! Reranker will fail.")
                        raise
        return self._model

    async def rerank(self, query: str, documents: list[VectorDocument], top_n: int = 5) -> list[VectorDocument]:
        if not documents:
            return []

        try:
            model = self._get_model()
            pairs = [
                [query, doc.page_content[:2000]] for doc in documents
            ]  # Truncate if too long to prevent token limit errors

            # predict
            scores = model.predict(pairs)

            doc_scores = list(zip(documents, scores, strict=False))
            doc_scores.sort(key=lambda x: x[1], reverse=True)

            ret_docs = []
            for doc, score in doc_scores[:top_n]:
                # Dynamically set score attribute
                doc.score = float(score)
                ret_docs.append(doc)

            return ret_docs

        except Exception as e:
            logger.error(f"Error during reranking: {e}")
            # Fallback to mock logic if model fails
            logger.warning("Falling back to MockReranker logic.")
            mock = MockReranker()
            return await mock.rerank(query, documents, top_n)


# Global Instance
_global_reranker = BGEReranker()


def get_reranker() -> BaseReranker:
    return _global_reranker
