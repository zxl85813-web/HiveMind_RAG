import asyncio
import os
import sys
from pathlib import Path

# Add backend to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.sdk.core.graph_store import Neo4jStore

async def verify():
    store = Neo4jStore()
    print("--- Verification Results ---")
    
    # 1. Check Torture Chamber
    res1 = await store.execute_query("MATCH (n) WHERE n.name CONTAINS 'Torture Chamber' RETURN count(n) as count")
    print(f"Torture Chamber count: {res1[0]['count']}")

    # 2. Check Files with path and created_at
    res2 = await store.execute_query("MATCH (f:File) RETURN count(f) as count")
    print(f"File count: {res2[0]['count']}")
    
    res3 = await store.execute_query("MATCH (f:File) WHERE f.path IS NOT NULL AND f.created_at IS NOT NULL RETURN count(f) as count")
    print(f"File with metadata count: {res3[0]['count']}")

    res4 = await store.execute_query("MATCH (f:File) RETURN f.id, f.path, f.created_at LIMIT 3")
    print(f"Sample Files: {res4}")
    
    await store.close()

if __name__ == "__main__":
    asyncio.run(verify())
