
import os
import asyncio
import sys
import hashlib
from pathlib import Path

# 🏗️ [Path Fix]: Ensure backend is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.sdk.core.graph_store import Neo4jStore

def get_md5(path: Path) -> str:
    try:
        with open(path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()
    except:
        return ""

async def register_files():
    store = Neo4jStore()
    print("--- Starting File Registration into Knowledge Graph ---")
    
    scan_targets = [
        ROOT_DIR / "backend" / "app",
        ROOT_DIR / "frontend" / "src",
        ROOT_DIR / "docs"
    ]
    
    skipped = {".venv", "__pycache__", "node_modules", ".git", "storage", "dist"}
    target_exts = {".py", ".tsx", ".ts", ".md"}
    
    count = 0
    for target in scan_targets:
        if not target.exists(): continue
        for root, _, files in os.walk(target):
            if any(s in root for s in skipped): continue
            for file in files:
                ext = Path(file).suffix
                if ext not in target_exts: continue
                
                full_path = Path(root) / file
                rel_path = full_path.relative_to(ROOT_DIR)
                node_id = str(rel_path).replace("\\", "/")
                h = get_md5(full_path)
                
                # MERGE File node
                query = """
                MERGE (f:File {id: $id})
                SET f.name = $name, f.path = $path, f.hash = $hash, f.updated_at = timestamp()
                SET f:ArchNode
                RETURN f.id
                """
                await store.execute_query(query, {
                    "id": node_id,
                    "name": file,
                    "path": str(rel_path),
                    "hash": h
                })
                count += 1
                if count % 20 == 0:
                    print(f"Registered {count} files...")

    print(f"--- Registration Complete! Total files registered/updated: {count} ---")
    await store.close()

if __name__ == "__main__":
    asyncio.run(register_files())
