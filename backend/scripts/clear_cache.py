"""
Purge poisoned entries from the Semantic Cache.

This script connects to the active vector store and deletes
the entire 'semantic_cache' collection, removing all cached
entries (including corrupted ones with tool_calls leaks).
"""
import asyncio
import os
import sys

# Ensure app modules are importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.vector_store import get_vector_store
from app.services.cache_service import CacheService

async def purge_semantic_cache():
    store = get_vector_store()
    collection_name = CacheService.CACHE_COLLECTION
    
    print(f"🧹 Purging semantic cache collection: '{collection_name}'")
    
    # For ChromaDB, we can delete the entire collection
    if hasattr(store, 'client') and hasattr(store.client, 'delete_collection'):
        try:
            store.client.delete_collection(name=collection_name)
            print(f"✅ Successfully deleted ChromaDB collection '{collection_name}'")
        except Exception as e:
            print(f"⚠️ ChromaDB delete failed (may not exist): {e}")
    # For Elasticsearch, delete the index
    elif hasattr(store, 'client') and hasattr(store.client, 'indices'):
        from app.core.config import settings
        index_name = f"{settings.ES_INDEX_PREFIX}_{collection_name}".lower()
        try:
            if await store.client.indices.exists(index=index_name):
                await store.client.indices.delete(index=index_name)
                print(f"✅ Successfully deleted ES index '{index_name}'")
            else:
                print(f"ℹ️ ES index '{index_name}' does not exist")
        except Exception as e:
            print(f"⚠️ ES delete failed: {e}")
    # For MockVectorStore
    elif hasattr(store, '_store'):
        if collection_name in store._store:
            del store._store[collection_name]
            print(f"✅ Cleared MockVectorStore collection '{collection_name}'")
        else:
            print(f"ℹ️ No collection '{collection_name}' in MockVectorStore")
    else:
        print("❌ Unknown vector store type, cannot purge.")
    
    print("🎉 Cache purge complete. Next chat message will go through LLM fresh.")

if __name__ == "__main__":
    asyncio.run(purge_semantic_cache())
