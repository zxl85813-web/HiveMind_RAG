
import asyncio
from app.sdk.core.graph_store import Neo4jStore
import json

async def check():
    store = Neo4jStore()
    print("Checking Requirement attributes...")
    try:
        res = await store.execute_query("MATCH (r:Requirement) RETURN r LIMIT 5")
        data = [dict(row['r']) for row in res]
        with open("scratch/req_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("Done. Saved to scratch/req_data.json")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await store.close()

if __name__ == "__main__":
    asyncio.run(check())
