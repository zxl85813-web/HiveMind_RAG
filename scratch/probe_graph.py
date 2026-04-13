
import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from app.sdk.core.graph_store import get_graph_store

async def probe_graph():
    store = get_graph_store()
    try:
        # 1. Get all SoftwareComponents
        components = await store.execute_query(
            "MATCH (s:SoftwareComponent) "
            "RETURN s.name as name LIMIT 50"
        )
        print("--- SoftwareComponents ---")
        for c in components:
            print(f"Component: {c['name']}")
        
        # 3. Check for specific nodes
        incidents = await store.execute_query("MATCH (i:Incident) RETURN count(i) as count")
        print("Incident Count:", incidents)
        
        reflections = await store.execute_query("MATCH (r:Reflection) RETURN count(r) as count")
        print("Reflection Count:", reflections)
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(probe_graph())
