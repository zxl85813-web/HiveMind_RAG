
import asyncio
import sys
from pathlib import Path

# Fix paths for imports
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.core.graph_store import get_graph_store

async def diagnose():
    store = get_graph_store()
    
    # 查找名称为空或缺失的节点
    cypher = """
    MATCH (n:ArchNode)
    WHERE n.name IS NULL OR n.name = ""
    RETURN labels(n) as labels, n.id as id, n.path as path
    LIMIT 20
    """
    records = await store.execute_query(cypher)
    
    print(f"Found {len(records)} nodes with empty names (showing top 20):")
    for r in records:
        print(f" - ID: {r['id']} | Labels: {r['labels']} | Path: {r['path']}")
    
    await store.close()

if __name__ == "__main__":
    asyncio.run(diagnose())
