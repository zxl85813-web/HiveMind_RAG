import os
import time
from typing import Any, Optional

from elasticsearch import Elasticsearch
from pydantic import BaseModel

from app.core.logging import logger


class HeavySearchResult(BaseModel):
    id: str
    index: str
    content: str
    score: float
    title: str | None = None
    metadata: dict[str, Any] = {}
    source_url: str | None = None

class GlobalKnowledgeService:
    """Tier-5: Cold Retrieval Layer (Elasticsearch).
    
    This service is HEAVY and should only be invoked when local/warm 
    memories (Tiers 1-4) provide insufficient context.
    """

    _instance: Optional['GlobalKnowledgeService'] = None
    _client: Elasticsearch | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GlobalKnowledgeService, cls).__new__(cls)
        return cls._instance

    @property
    def client(self) -> Elasticsearch | None:
        """Lazy init: established connection only when needed."""
        if self._client is None:
            host = os.getenv("ES_HOST")
            port = os.getenv("ES_PORT")
            api_key = os.getenv("ES_API_KEY")

            if not all([host, port, api_key]):
                logger.warning("❄️ [ES-Service] Configuration missing, skipping initialization.")
                return None

            try:
                self._client = Elasticsearch(
                    f"http://{host}:{port}",
                    api_key=api_key,
                    timeout=5,
                    max_retries=2,
                    retry_on_timeout=True
                )
                # Test connection once
                if not self._client.ping():
                    logger.error("❌ [ES-Service] Ping failed, instance might be offline.")
                    self._client = None
                else:
                    logger.info("📡 [ES-Service] Tier-5 (Cold Path) connection established.")
            except Exception as e:
                logger.error(f"❌ [ES-Service] Connection failed: {e}")
                self._client = None
        return self._client

    async def global_search(
        self,
        query: str,
        limit: int = 30,
        min_score: float = 0.3
    ) -> list[HeavySearchResult]:
        """Perform a deep keyword/BM25 search on global indices."""
        es = self.client
        if not es:
            return []

        index_prefix = os.getenv("ES_INDEX_PREFIX", "linkrag")
        start_time = time.perf_counter()

        try:
            # Multi-field search for better relevancy
            body = {
                "size": limit,
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["content^2", "title^3", "metadata.tags^1.5", "summary"],
                        "type": "best_fields",
                        "fuzziness": "AUTO"
                    }
                },
                "highlight": {
                    "fields": {
                        "content": {"number_of_fragments": 1, "fragment_size": 200}
                    }
                }
            }

            resp = es.search(index=f"{index_prefix}*", body=body)
            hits = resp.get("hits", {}).get("hits", [])

            results = []
            for hit in hits:
                score = hit.get("_score", 0)
                if score < min_score:
                    continue

                source = hit.get("_source", {})
                highlight = hit.get("highlight", {}).get("content", [""])

                results.append(HeavySearchResult(
                    id=hit.get("_id"),
                    index=hit.get("_index"),
                    content=highlight[0] or source.get("content", "")[:200],
                    score=float(score),
                    title=source.get("title"),
                    metadata=source.get("metadata", {}),
                    source_url=source.get("url")
                ))

            elapsed = (time.perf_counter() - start_time) * 1000
            logger.info(f"❄️ [ES-Search] Query='{query[:30]}' hits={len(results)} time={elapsed:.1f}ms")
            return results

        except Exception as e:
            logger.warning(f"❄️ [ES-Search] Query failed: {e}")
            return []

def get_global_knowledge_service() -> GlobalKnowledgeService:
    return GlobalKnowledgeService()
