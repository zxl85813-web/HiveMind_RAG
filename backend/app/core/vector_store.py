"""
Vector Store Interface — Abstract storage for embeddings.

所属模块: core
依赖模块: langchain_core (optional), numpy (optional)
注册位置: REGISTRY.md > Core > VectorStore
"""

import abc
import os
import uuid
from typing import Any

from loguru import logger
from pydantic import BaseModel

from app.core.config import settings

try:
    from elasticsearch import AsyncElasticsearch, helpers

    ES_AVAILABLE = True
except ImportError:
    ES_AVAILABLE = False


class VectorDocument(BaseModel):
    page_content: str
    metadata: dict[str, Any] = {}
    embedding: list[float] | None = None
    score: float = 0.0


class SearchType(str):
    VECTOR = "vector"
    BM25 = "bm25"
    HYBRID = "hybrid"


class BaseVectorStore(abc.ABC):
    """Abstract interface for Vector Store operations."""

    @abc.abstractmethod
    async def add_documents(self, documents: list[VectorDocument], collection_name: str) -> list[str]:
        """Add documents to the vector store."""
        pass

    @abc.abstractmethod
    async def search(
        self, query: str, search_type: str = SearchType.HYBRID, k: int = 4, collection_name: str = "default"
    ) -> list[VectorDocument]:
        """Unified search method supporting Vector, BM25, and Hybrid modes."""
        pass

    @abc.abstractmethod
    async def delete_documents(self, collection_name: str, filter_metadata: dict[str, Any]) -> None:
        """Delete documents from the vector store based on metadata."""
        pass

    async def similarity_search(self, query: str, k: int = 4, collection_name: str = "default") -> list[VectorDocument]:
        """Legacy method for vector search."""
        return await self.search(query, SearchType.VECTOR, k, collection_name)


class MockVectorStore(BaseVectorStore):
    """In-memory Mock Vector Store with basic keyword matching simulation."""

    def __init__(self):
        self._store: dict[str, list[VectorDocument]] = {}

    async def add_documents(self, documents: list[VectorDocument], collection_name: str) -> list[str]:
        if collection_name not in self._store:
            self._store[collection_name] = []

        ids = []
        for _i, doc in enumerate(documents):
            self._store[collection_name].append(doc)
            ids.append(f"{collection_name}_{len(self._store[collection_name])}")

        print(f"📚 [MockVectorStore] Added {len(documents)} docs to collection '{collection_name}'")
        return ids

    async def search(
        self, query: str, search_type: str = SearchType.HYBRID, k: int = 4, collection_name: str = "default"
    ) -> list[VectorDocument]:
        docs = self._store.get(collection_name, [])
        if not docs:
            return []

        query_terms = set(query.lower().split())
        scored_docs = []

        for doc in docs:
            content_lower = doc.page_content.lower()

            # 1. Mock BM25 Score (Term Frequency)
            bm25_score = 0
            for term in query_terms:
                bm25_score += content_lower.count(term)

            # 2. Mock Vector Score
            vector_score = bm25_score + (1.0 if query.lower() in content_lower else 0.0)

            final_score = 0.0
            if search_type == SearchType.BM25:
                final_score = bm25_score
            elif search_type == SearchType.VECTOR:
                final_score = vector_score
            else:
                final_score = (bm25_score * 0.5) + (vector_score * 0.5)

            if final_score > 0:
                scored_docs.append((doc, final_score))

        scored_docs.sort(key=lambda x: x[1], reverse=True)
        results = []
        for doc, score in scored_docs[:k]:
            doc.score = score
            results.append(doc)
        return results

    async def delete_documents(self, collection_name: str, filter_metadata: dict[str, Any]) -> None:
        if collection_name not in self._store:
            return
        initial_count = len(self._store[collection_name])
        self._store[collection_name] = [
            doc
            for doc in self._store[collection_name]
            if not all(doc.metadata.get(k) == v for k, v in filter_metadata.items())
        ]
        deleted_count = initial_count - len(self._store[collection_name])
        print(f"📚 [MockVectorStore] Deleted {deleted_count} docs from '{collection_name}'")


class ElasticVectorStore(BaseVectorStore):
    """Production Vector Store using Elasticsearch 8.x."""

    def __init__(self):
        if not ES_AVAILABLE:
            raise RuntimeError("elasticsearch package not installed")

        url = f"http://{settings.ES_HOST}:{settings.ES_PORT}"
        if settings.ES_API_KEY:
            self.client = AsyncElasticsearch(url, api_key=settings.ES_API_KEY)
        else:
            self.client = AsyncElasticsearch(url)

        logger.info(f"🔌 Connected to Elasticsearch at {url}")

    async def ensure_index(self, index_name: str):
        if not await self.client.indices.exists(index=index_name):
            mapping = {
                "mappings": {
                    "properties": {
                        "content": {"type": "text", "analyzer": "standard"},
                        "metadata": {"type": "object"},
                        "embedding": {
                            "type": "dense_vector",
                            "dims": settings.EMBEDDING_DIMS,
                            "index": True,
                            "similarity": "cosine",
                        },
                    }
                }
            }
            await self.client.indices.create(index=index_name, body=mapping)

    async def add_documents(self, documents: list[VectorDocument], collection_name: str) -> list[str]:
        index_name = f"{settings.ES_INDEX_PREFIX}_{collection_name}".lower()
        await self.ensure_index(index_name)

        actions = []
        ids = []  # ES bulk doesn't return created IDs easily, logic simplified
        for doc in documents:
            vec = doc.embedding if doc.embedding else [0.0] * settings.EMBEDDING_DIMS

            action = {
                "_index": index_name,
                "_source": {"content": doc.page_content, "metadata": doc.metadata, "embedding": vec},
            }
            actions.append(action)

        await helpers.async_bulk(self.client, actions)
        logger.info(f"indexed {len(documents)} docs to ES index {index_name}")
        return ids

    async def search(
        self, query: str, search_type: str = SearchType.HYBRID, k: int = 4, collection_name: str = "default"
    ) -> list[VectorDocument]:
        index_name = f"{settings.ES_INDEX_PREFIX}_{collection_name}".lower()
        if not await self.client.indices.exists(index=index_name):
            logger.warning(f"Index {index_name} does not exist")
            return []

        # Lazy import to avoid circular dep if any
        from app.core.embeddings import get_embedding_service

        embedder = get_embedding_service()
        query_vec = embedder.embed_query(query)

        body = {}
        if search_type == SearchType.VECTOR:
            body = {"knn": {"field": "embedding", "query_vector": query_vec, "k": k, "num_candidates": 100}}
        elif search_type == SearchType.BM25:
            body = {"query": {"match": {"content": query}}, "size": k}
        else:  # Hybrid
            body = {
                "query": {"match": {"content": query}},
                "knn": {"field": "embedding", "query_vector": query_vec, "k": k, "num_candidates": 100},
                "size": k,
            }

        try:
            resp = await self.client.search(index=index_name, body=body)
        except Exception as e:
            logger.error(f"ES Search failed: {e}")
            return []

        results = []
        for hit in resp["hits"]["hits"]:
            source = hit["_source"]
            results.append(VectorDocument(page_content=source["content"], metadata=source.get("metadata", {})))
        return results

    async def delete_documents(self, collection_name: str, filter_metadata: dict[str, Any]) -> None:
        index_name = f"{settings.ES_INDEX_PREFIX}_{collection_name}".lower()
        if not await self.client.indices.exists(index=index_name):
            return

        must_clauses = [{"match": {f"metadata.{k}": v}} for k, v in filter_metadata.items()]
        query = {"query": {"bool": {"must": must_clauses}}}

        try:
            await self.client.delete_by_query(index=index_name, body=query)
            logger.info(f"Deleted docs from ES index {index_name} with filter {filter_metadata}")
        except Exception as e:
            logger.error(f"ES Delete failed: {e}")


class ChromaVectorStore(BaseVectorStore):
    """Local Vector Store using ChromaDB."""

    def __init__(self):
        import chromadb

        path = os.path.join(os.getcwd(), "data", "chroma")
        os.makedirs(path, exist_ok=True)

        self.client = chromadb.PersistentClient(path=path)
        logger.info(f"💾 Connected to ChromaDB at {path}")

    async def add_documents(self, documents: list[VectorDocument], collection_name: str) -> list[str]:
        # Chroma operations are blocking, run in executor if needed for high volume
        # Simplified for now
        collection = self.client.get_or_create_collection(name=collection_name)

        ids = [f"id_{uuid.uuid4()}" for _ in documents]
        texts = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        embeddings = [doc.embedding for doc in documents if doc.embedding]

        if embeddings:
            collection.add(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)
        else:
            collection.add(ids=ids, documents=texts, metadatas=metadatas)

        logger.info(f"Chroma: Added {len(documents)} docs to {collection_name}")
        return ids

    async def search(
        self, query: str, search_type: str = SearchType.HYBRID, k: int = 4, collection_name: str = "default"
    ) -> list[VectorDocument]:
        collection = self.client.get_or_create_collection(name=collection_name)

        results = collection.query(query_texts=[query], n_results=k)

        docs = []
        if results and results["documents"]:
            for i in range(len(results["documents"][0])):
                docs.append(
                    VectorDocument(
                        page_content=results["documents"][0][i],
                        metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                        score=1.0 - (results["distances"][0][i] if results.get("distances") else 0.0)
                    )
                )
        return docs

    async def delete_documents(self, collection_name: str, filter_metadata: dict[str, Any]) -> None:
        try:
            collection = self.client.get_collection(name=collection_name)
            # ChromaDB where filter
            # Example: {"doc_id": "123"}
            collection.delete(where=filter_metadata)
            logger.info(f"Chroma: Deleted docs from {collection_name} with filter {filter_metadata}")
        except Exception as e:
            logger.warning(f"Chroma delete failed or collection not found: {e}")


# Singleton Factory
_global_store = None


def get_vector_store() -> BaseVectorStore:
    global _global_store
    if _global_store:
        return _global_store

    if settings.VECTOR_STORE_TYPE == "elasticsearch" and ES_AVAILABLE:
        try:
            _global_store = ElasticVectorStore()
        except Exception as e:
            logger.error(f"⚠️ Failed to init ElasticVectorStore: {e}. Falling back to Mock.")
            _global_store = MockVectorStore()
    elif settings.VECTOR_STORE_TYPE == "chroma":
        try:
            _global_store = ChromaVectorStore()
        except Exception as e:
            logger.error(f"⚠️ Failed to init ChromaVectorStore: {e}. Falling back to Mock.")
            _global_store = MockVectorStore()
    else:
        _global_store = MockVectorStore()

    return _global_store
