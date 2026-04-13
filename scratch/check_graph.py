
import asyncio
import os
import sys
sys.path.append(os.path.join(os.getcwd(), "backend"))
from app.sdk.core.graph_store import get_graph_store

async def check():
    store = get_graph_store()
    counts = await store.execute_query(
        "MATCH (n) WHERE labels(n)[0] IN ['Incident', 'DecisionPoint', 'SoftwareComponent'] "
        "RETURN labels(n)[0] as label, count(n) as count"
    )
    for c in counts:
        print(f"Label: {c['label']}, Count: {c['count']}")

if __name__ == "__main__":
    asyncio.run(check())
