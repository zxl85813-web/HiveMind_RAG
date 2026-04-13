
import asyncio
from app.sdk.core.graph_store import Neo4jStore

async def probe():
    store = Neo4jStore()
    print("--- Probing Requirement Mapping ---")
    try:
        # 1. 看看 Requirement 节点都有哪些外出关系
        res = await store.execute_query("MATCH (r:Requirement)-[r_rel]->(n) RETURN type(r_rel) as type, labels(n) as target_labels, count(*) as count")
        if not res:
            print("Warning: No outgoing relationships from Requirement nodes found!")
        else:
            for row in res:
                print(f"Relationship: {row['type']} -> Target: {row['target_labels']} (Count: {row['count']})")
        
        # 2. 获取最近的 10 个架构资产明细
        assets_res = await store.execute_query("MATCH (n:ArchNode) RETURN n.name as name, labels(n) as labels ORDER BY n.created_at DESC LIMIT 10")
        print("\n--- Recent ArchNodes ---")
        for row in assets_res:
            print(f"Name: {row['name']}, Labels: {row['labels']}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await store.close()

if __name__ == "__main__":
    asyncio.run(probe())
