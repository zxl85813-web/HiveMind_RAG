
import asyncio
import sys
from pathlib import Path

# Fix paths for imports
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.core.graph_store import get_graph_store

async def check():
    store = get_graph_store()
    node_id = 'backend/app/services/agents/review_governance.py::ReviewGovernance.get_governance_context'
    
    # 1. 检查节点是否存在
    res_node = await store.execute_query("MATCH (n {id: $id}) RETURN n", {"id": node_id})
    if not res_node:
        print(f"Node NOT FOUND: {node_id}")
        # Try finding similar
        res_similar = await store.execute_query("MATCH (n:ArchNode) WHERE n.id CONTAINS 'get_governance_context' RETURN n.id LIMIT 5")
        print(f"Similar nodes: {[n['n.id'] for n in res_similar]}")
        await store.close()
        return

    # 2. 检查所有的关系 (In or Out)
    res_rel = await store.execute_query("MATCH (n {id: $id})-[r]-(m) RETURN type(r) as type, labels(m) as labels, m.id as mid", {"id": node_id})
    print(f"Relationships for {node_id}:")
    for r in res_rel:
        print(f" - [{r['type']}] -> {r['labels']} (ID: {r['mid']})")
    
    if not res_rel:
        print("RESULT: No relationships found. Node is an island.")

    await store.close()

if __name__ == "__main__":
    asyncio.run(check())
