
import asyncio
import os
import sys
from pathlib import Path

# 🏗️ [Path Fix]: Ensure backend is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.sdk.core.graph_store import Neo4jStore

async def heal():
    store = Neo4jStore()
    print("--- Starting Architecture Self-Healing (POWER ALIGNMENT) ---")
    
    try:
        # 1. 抓取所有需求 ID
        reqs = await store.execute_query("MATCH (r:Requirement) RETURN r.id as id")
        all_req_ids = [r['id'] for r in reqs if r['id']]
        print(f"Tracking IDs: {all_req_ids}")

        # 2. 预解析项目结构 (减少 IO)
        root_dir = Path("..").resolve()
        target_exts = {'.py', '.tsx', '.ts', '.md'}
        skipped = {'node_modules', '.venv', '.git', 'storage', 'dist'}
        
        mapping_count = 0
        
        # 先把所有代码节点捞出来，加速匹配
        print("Fetching code assets from graph...")
        assets = await store.execute_query("MATCH (n:ArchNode) RETURN n.name as name")
        asset_names = {a['name'] for a in assets if a['name']}
        print(f"Graph has {len(asset_names)} architecture nodes.")

        for path in root_dir.rglob("*"):
            if path.suffix not in target_exts: continue
            if any(s in path.parts for s in skipped): continue
            
            try:
                content = path.read_text(encoding="utf-8")
                filename = path.name
                
                for rid in all_req_ids:
                    if rid in content:
                        print(f"TRACE: {rid} found in {filename}")
                        # 3. 跨标签、跨属性暴力补链
                        query = """
                        MATCH (r:Requirement {id: $req_id})
                        MATCH (n) WHERE n.name = $filename OR (n:File AND n.path CONTAINS $filename)
                        MERGE (r)-[:IMPLEMENTED_BY]->(n)
                        RETURN count(n) as matched
                        """
                        res = await store.execute_query(query, {"req_id": rid, "filename": filename})
                        if res and res[0]['matched'] > 0:
                            print(f"SUCCESS: Linked {rid} to {filename}")
                            mapping_count += 1
            except Exception:
                continue

        print(f"\n--- Healing Complete! Total links established: {mapping_count} ---")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await store.close()

if __name__ == "__main__":
    asyncio.run(heal())
