"""
Semantic Cache Service (P2).
Uses Vector Search to find similar answered questions.

@covers REQ-002
"""

import time
from typing import Any, ClassVar

from loguru import logger

from app.core.vector_store import VectorDocument, get_vector_store


class CacheService:
    CACHE_COLLECTION: ClassVar[str] = "semantic_cache"
    ROUTE_CACHE_COLLECTION: ClassVar[str] = "route_cache"
    THRESHOLD: ClassVar[float] = 0.96  # High threshold for semantic equivalence
    ROUTE_THRESHOLD: ClassVar[float] = 0.92 # Slightly lower for routing variations


    # Tokens that indicate a corrupted/internal response — NEVER cache or return these
    POISON_TOKENS: ClassVar[list[str]] = ["tool_calls_begin", "tool_sep", "tool_call_end", "tool▁calls", "tool▁sep"]

    @staticmethod
    async def get_cached_response(query: str) -> dict[str, Any] | None:
        """
        Retrieves a cached answer if a similar query was processed before.
        """
        store = get_vector_store()
        try:
            # Search for the query itself in the cache collection
            results = await store.search(
                query=query,
                k=1,
                collection_name=CacheService.CACHE_COLLECTION,
                search_type="vector",  # Always use vector for semantic similarity
            )

            if not results:
                return None

            match = results[0]
            score = getattr(match, "score", 0.0)

            # Distance check (for cosine similarity, higher is better)
            if score < CacheService.THRESHOLD:
                logger.debug(f"Cache miss: closest match score {score:.4f} < {CacheService.THRESHOLD}")
                return None

            answer = match.metadata.get("answer", match.page_content)

            # --- Safety Valve: Reject poisoned cache entries ---
            if any(token in answer for token in CacheService.POISON_TOKENS):
                logger.warning(f"🚫 Poisoned cache entry detected for '{query}', discarding.")
                return None

            # Also reject if the "answer" is just the query echoed back
            if answer.strip() == query.strip():
                logger.warning(f"🚫 Echo cache entry detected for '{query}', discarding.")
                return None

            logger.info(f"🧠 Semantic Cache Hit for: '{query}' (score: {score:.4f})")
            return {"content": answer, "metadata": match.metadata, "score": score}
        except Exception as e:
            logger.warning(f"Cache lookup failed: {e}")
            return None

    @staticmethod
    async def set_cached_response(query: str, response: str, metadata: dict[str, Any] | None = None):
        """
        Store a query-response pair in the semantic cache.
        Validates that the response is clean before caching.
        """
        # --- Safety Valve: Never cache poisoned responses ---
        if metadata is None:
            metadata = {}
        if any(token in response for token in CacheService.POISON_TOKENS):
            logger.warning(f"🚫 Refusing to cache poisoned response for '{query}'")
            return

        # Don't cache very short responses (likely errors or placeholders)
        if len(response.strip()) < 10:
            logger.debug(f"Skipping cache for too-short response: '{response[:50]}'")
            return

        store = get_vector_store()
        try:
            # Store 'Query' as content so it's searchable, and 'Answer' in metadata.
            cache_doc = VectorDocument(
                page_content=query, metadata={"answer": response, "cached_at": time.time(), **metadata}
            )
            await store.add_documents([cache_doc], collection_name=CacheService.CACHE_COLLECTION)
            logger.debug(f"💾 Cached response for: '{query}'")
        except Exception as e:
            logger.error(f"Failed to cache response: {e}")

    @staticmethod
    async def get_cached_route(query: str) -> str | None:
        """
        JIT Route Cache (GOV-004).
        Retrieves a previously successful agent/step routing for this query.
        """
        store = get_vector_store()
        try:
            results = await store.search(
                query=query,
                k=1,
                collection_name=CacheService.ROUTE_CACHE_COLLECTION,
                search_type="vector"
            )
            if results and results[0].score >= CacheService.ROUTE_THRESHOLD:
                target_route = results[0].metadata.get("target")
                if target_route:
                    logger.info(f"⚡ [JIT Cache] Route Hit: '{query[:30]}' -> {target_route}")
                    return target_route
        except Exception as e:
            logger.warning(f"Route cache lookup failed: {e}")
        return None

    @staticmethod
    async def set_cached_route(query: str, target: str):
        """
        Store a routing decision in the JIT cache.
        """
        store = get_vector_store()
        try:
            cache_doc = VectorDocument(
                page_content=query,
                metadata={"target": target, "cached_at": time.time()}
            )
            await store.add_documents([cache_doc], collection_name=CacheService.ROUTE_CACHE_COLLECTION)
        except Exception as e:
            logger.error(f"Failed to cache route: {e}")

    # 🛰️ [M5.2.1] Intent Cache: Transient storage for prefetched results
    _intent_cache: ClassVar[dict[str, Any]] = {}

    @staticmethod
    def set_intent_cache(session_id: str, data: Any, ttl_sec: int = 60):
        """Store transient prefetched data for a session."""
        CacheService._intent_cache[session_id] = {
            "data": data,
            "expiry": time.time() + ttl_sec
        }
        logger.debug(f"🛰️ [IntentCache] Stored prefetch for session {session_id}")

    @staticmethod
    def get_intent_cache(session_id: str) -> Any | None:
        """Retrieve and clean up prefetched data."""
        entry = CacheService._intent_cache.get(session_id)
        if not entry:
            return None
        
        if time.time() > entry["expiry"]:
            del CacheService._intent_cache[session_id]
            return None
            
        # Optional: Pop after read to ensure freshness? 
        # For now, we keep it until message_final clears it.
        return entry["data"]

    @staticmethod
    def clear_intent_cache(session_id: str):
        """Manual cleanup of intent cache."""
        CacheService._intent_cache.pop(session_id, None)



try:
    import tiktoken
except ImportError:
    tiktoken = None


class TokenService:
    """Utility for tracking token usage and costs."""

    @staticmethod
    def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
        """Count tokens accurately using tiktoken."""
        if not text:
            return 0

        if tiktoken:
            try:
                # Attempt to get encoding for the specific model
                try:
                    encoding = tiktoken.encoding_for_model(model)
                except KeyError:
                    # Fallback for unknown models
                    encoding = tiktoken.get_encoding("cl100k_base")

                return len(encoding.encode(text))
            except Exception as e:
                logger.warning(f"tiktoken counting failed: {e}")

        # Fallback: ~4 characters per token
        return len(text) // 4 + 1

    @staticmethod
    def calculate_cost(prompt_tokens: int, completion_tokens: int, model: str = "gpt-3.5-turbo") -> float:
        """Calculate USD cost based on model pricing."""
        # Standard pricing: prompt 0.0015/1k, completion 0.002/1k
        return (prompt_tokens * 0.0015 + completion_tokens * 0.002) / 1000
