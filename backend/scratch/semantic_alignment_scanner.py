
import asyncio
import os
from pathlib import Path
from app.sdk.core.graph_store import Neo4jStore
from app.sdk.core.config import settings

async def semantic_sync():
    store = Neo4jStore()
    print("--- Starting Architecture Semantic Alignment Scan ---")
    
    try:
        # 1. 获取所有需求定义
        reqs = await store.execute_query("MATCH (r:Requirement) RETURN r.id as id, r.name as name")
        req_profiles = {r['id']: r['name'].lower() for r in reqs if r['id']}
        print(f"Loaded {len(req_profiles)} semantic clusters for matching.")

        # 2. 扫描无标记的核心文件
        root_dir = Path("..").resolve()
        target_exts = {'.py', '.tsx'}
        skipped = {'node_modules', '.venv', '.git', 'storage', 'dist'}
        
        mapping_count = 0
        
        for path in root_dir.rglob("*"):
            if path.suffix not in target_exts: continue
            if any(s in path.parts for s in skipped): continue
            
            # 如果文件名已经带有某种功能暗示 (如 auth, swarm, memory)
            fname_lower = path.name.lower()
            content_hint = ""
            try:
                # 仅读取前 50 行获取上下文
                with open(path, 'r', encoding='utf-8') as f:
                    content_hint = "".join([f.readline() for _ in range(50)]).lower()
            except:
                continue

            # 3. 核心词分词对齐 (Smart Matching)
            fname_tokens = set(fname_lower.replace('_', '-').split('-'))
            
            for rid, rname in req_profiles.items():
                # 获取需求的核心词集合 (排除 REQ-001 等前缀)
                req_tokens = set(rname.replace('_', '-').replace('.', '-').split('-'))
                # 移除干扰项
                req_tokens = {t for t in req_tokens if len(t) > 3 and not t.startswith('req')}
                
                # 如果有交集，则认为有关联
                if req_tokens & fname_tokens:
                    print(f"SEMANTIC MATCH: {rid} ({req_tokens}) <~> {path.name}")
                    
                    query = """
                    MATCH (r:Requirement {id: $req_id})
                    MATCH (n) WHERE n.name = $filename
                    MERGE (r)-[:IMPLEMENTED_BY]->(n)
                    RETURN count(n) as matched
                    """
                    await store.execute_query(query, {"req_id": rid, "filename": path.name})
                    mapping_count += 1
                    break

        print(f"\n--- Scan Complete! Semantically aligned {mapping_count} legacy files. ---")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await store.close()

if __name__ == "__main__":
    asyncio.run(semantic_sync())
