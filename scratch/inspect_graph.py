import asyncio
import sys
import os

# Set up paths
backend_dir = r"c:\Users\linkage\Desktop\aiproject\backend"
sys.path.append(backend_dir)

from app.sdk.core.graph_store import get_graph_store

async def main():
    store = get_graph_store()
    try:
        # Get labels
        labels = await store.execute_query("CALL db.labels()")
        print("Labels:", labels)
        
        # Get some IDs
        ids = await store.execute_query("MATCH (n) RETURN n.id, labels(n) LIMIT 10")
        print("Sample IDs:", ids)
    finally:
        await store.close()

if __name__ == "__main__":
    asyncio.run(main())
