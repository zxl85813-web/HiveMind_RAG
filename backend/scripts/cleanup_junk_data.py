import asyncio
import os
import sys
from pathlib import Path

# Add backend to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.sdk.core.graph_store import Neo4jStore

async def cleanup():
    store = Neo4jStore()
    print("[Cleanup] Removing test data 'Torture Chamber'...")
    
    # 1. Delete nodes with "Torture Chamber" in name
    query1 = "MATCH (n) WHERE n.name CONTAINS 'Torture Chamber' DETACH DELETE n"
    await store.execute_query(query1)
    print("Removed 'Torture Chamber' nodes.")

    # 2. Delete nodes with name 'T' or other single-char junk
    query2 = "MATCH (n) WHERE n.name = 'T' OR n.name = ' ' DETACH DELETE n"
    await store.execute_query(query2)
    print("Removed junk nodes.")
    
    print("Cleanup complete.")
    await store.close()

if __name__ == "__main__":
    asyncio.run(cleanup())
