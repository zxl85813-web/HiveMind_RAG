"""
Purge poisoned entries from the Semantic Cache.

This script connects to the active vector store and deletes
the entire 'semantic_cache' collection, removing all cached
entries (including corrupted ones with tool_calls leaks).
"""

import asyncio
import os
import sys
from pathlib import Path

# Ensure app modules are importable
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_script_context, get_trace_logger
setup_script_context("clear_cache")
t_logger = get_trace_logger("scripts.clear_cache")

# 🛰️ [Architecture-Fix]: Windows Console UTF-8 Force
try:
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except (AttributeError, Exception):
    pass

from app.core.vector_store import get_vector_store
from app.services.cache_service import CacheService


async def purge_semantic_cache():
    store = get_vector_store()
    collection_name = CacheService.CACHE_COLLECTION

    t_logger.info(f"🧹 Purging semantic cache collection: '{collection_name}'", action="purge_start")

    # For ChromaDB, we can delete the entire collection
    if hasattr(store, "client") and hasattr(store.client, "delete_collection"):
        try:
            store.client.delete_collection(name=collection_name)
            t_logger.success(f"✅ Successfully deleted ChromaDB collection '{collection_name}'", action="purge_success")
        except Exception as e:
            t_logger.warning(f"⚠️ ChromaDB delete failed (may not exist): {e}", action="purge_warn")
    # For Elasticsearch, delete the index
    elif hasattr(store, "client") and hasattr(store.client, "indices"):
        from app.core.config import settings

        index_name = f"{settings.ES_INDEX_PREFIX}_{collection_name}".lower()
        try:
            if await store.client.indices.exists(index=index_name):
                await store.client.indices.delete(index=index_name)
                t_logger.success(f"✅ Successfully deleted ES index '{index_name}'", action="purge_success")
            else:
                t_logger.info(f"ℹ️ ES index '{index_name}' does not exist", action="purge_skip")
        except Exception as e:
            t_logger.error(f"⚠️ ES delete failed: {e}", action="purge_error")
    # For MockVectorStore
    elif hasattr(store, "_store"):
        if collection_name in store._store:
            del store._store[collection_name]
            t_logger.success(f"✅ Cleared MockVectorStore collection '{collection_name}'", action="purge_success")
        else:
            t_logger.info(f"ℹ️ No collection '{collection_name}' in MockVectorStore", action="purge_skip")
    else:
        t_logger.error("❌ Unknown vector store type, cannot purge.", action="purge_failed")

    t_logger.info("🎉 Cache purge complete. Next chat message will go through LLM fresh.", action="purge_finish")


if __name__ == "__main__":
    asyncio.run(purge_semantic_cache())
