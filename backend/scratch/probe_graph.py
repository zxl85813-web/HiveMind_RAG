
import asyncio
from app.sdk.core.graph_store import Neo4jStore

async def probe():
    store = Neo4jStore()
    print("Probing Graph Labels...")
    try:
        # 获取所有标签及其分布
        res = await store.execute_query("MATCH (n) RETURN labels(n) as tags, count(*) as count")
        if not res:
            print("Graph is empty!")
        else:
            for row in res:
                print(f"Tag: {row['tags']}, Count: {row['count']}")
        
        # 获取关系分布
        rel_res = await store.execute_query("MATCH ()-[r]->() RETURN type(r) as type, count(*) as count")
        print("\nProbing Relationship Types...")
        for row in rel_res:
            print(f"Type: {row['type']}, Count: {row['count']}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await store.close()

if __name__ == "__main__":
    asyncio.run(probe())
