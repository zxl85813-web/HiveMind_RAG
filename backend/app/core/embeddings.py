"""
Embeddings Service — Embed text using ZhipuAI.
"""

from zhipuai import ZhipuAI

from app.sdk.core import settings


class BaseEmbeddingService:
    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


class ZhipuEmbeddingService(BaseEmbeddingService):
    def __init__(self):
        self.client = ZhipuAI(api_key=settings.EMBEDDING_API_KEY)
        self.model = settings.EMBEDDING_MODEL

    def embed_query(self, text: str) -> list[float]:
        return self._embed_with_cache(text)

    from functools import lru_cache

    @lru_cache(maxsize=1024)  # noqa: B019
    def _embed_with_cache(self, text: str) -> list[float]:
        try:
            response = self.client.embeddings.create(model=self.model, input=text)
            return response.data[0].embedding
        except Exception as e:
            print(f"Error embedding query: {e}")
            return [0.0] * settings.EMBEDDING_DIMS

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        # Zhipu might not support batch or limits it.
        # We can loop or batch small groups.
        embeddings = []
        for text in texts:
            embeddings.append(self.embed_query(text))
        return embeddings


# Singleton
_service = None


def get_embedding_service():
    global _service
    if not _service:
        _service = ZhipuEmbeddingService()
    return _service
