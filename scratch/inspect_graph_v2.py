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
        # Get count per label
        counts = await store.execute_query("MATCH (n) RETURN labels(n), count(n)")
        print("Label Counts:", counts)
        
        # Get Requirement IDs
        reqs = await store.execute_query("MATCH (n:Requirement) RETURN n.id LIMIT 10")
        print("Requirement IDs:", reqs)
        
        # Get SoftwareAsset IDs
        assets = await store.execute_query("MATCH (n:SoftwareAsset) RETURN n.id LIMIT 10")
        print("SoftwareAsset IDs:", assets)
    finally:
        await store.close()

if __name__ == "__main__":
    asyncio.run(main())
