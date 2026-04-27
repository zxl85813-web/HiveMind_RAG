
import os
import asyncio
import sys
import subprocess
import re
from pathlib import Path

# 🏗️ [Path Fix]: Ensure backend is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.sdk.core.graph_store import Neo4jStore

async def industrial_index():
    store = Neo4jStore()
    print("[Industrial Index] Starting deep architecture harvesting...")
    # now = int(asyncio.get_event_loop().time() * 1000) # Milli for compatibility

    # 1. Index Rules (.agent/rules)
    print("--- 1. Harvesting Rules ---")
    rules_dir = ROOT_DIR / ".agent" / "rules"
    if rules_dir.exists():
        for rule_file in rules_dir.glob("*.md"):
            rel_path = rule_file.relative_to(ROOT_DIR)
            query = """
            MERGE (r:Rule {id: $id})
            SET r.name = $name, r.type = 'ProcessRule', 
                r.path = $path, r.updated_at = timestamp(),
                r.created_at = COALESCE(r.created_at, timestamp())
            SET r:ArchNode
            """
            await store.execute_query(query, {
                "id": rule_file.name,
                "name": rule_file.stem.replace("-", " ").title(),
                "path": str(rel_path).replace("\\", "/")
            })
            print(f"Index Rule: {rule_file.name}")

    # 2. Index Git History (Commits & Personnel)
    print("--- 2. Harvesting Git History ---")
    try:
        log_format = "%H|%an|%ae|%at|%s"
        result = subprocess.run(
            ["git", "log", "-n", "50", f"--format={log_format}"],
            capture_output=True, text=True, cwd=ROOT_DIR
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if not line: continue
                h, author, email, timestamp, subject = line.split("|")
                ts_milli = int(timestamp) * 1000
                
                await store.execute_query("""
                    MERGE (p:Person {id: $email})
                    SET p.name = $name, p.platform = 'Git',
                        p.created_at = COALESCE(p.created_at, $ts)
                    SET p:ArchNode
                """, {"email": email, "name": author, "ts": ts_milli})
                
                await store.execute_query("""
                    MERGE (c:Commit {id: $hash})
                    SET c.message = $msg, c.timestamp = $ts, c.author = $author,
                        c.name = $msg, c.created_at = COALESCE(c.created_at, $ts)
                    SET c:ArchNode
                """, {"hash": h, "msg": subject, "ts": ts_milli, "author": author})
                
                await store.execute_query("""
                    MATCH (p:Person {id: $email}), (c:Commit {id: $hash})
                    MERGE (p)-[:AUTHORED]->(c)
                """, {"email": email, "hash": h})
    except Exception as e:
        print(f"Git indexing failed: {e}")

    # 3. Index Code Files & Annotations
    print("--- 3. Harvesting Code Assets ---")
    scan_targets = [ROOT_DIR / "backend" / "app", ROOT_DIR / "frontend" / "src"]
    for target in scan_targets:
        if not target.exists(): continue
        for root, _, files in os.walk(target):
            for file in files:
                if not file.endswith((".py", ".tsx", ".ts")): continue
                path = Path(root) / file
                rel_path = path.relative_to(ROOT_DIR)
                file_id = str(rel_path).replace("\\", "/")
                
                # Create/Update File Node
                await store.execute_query("""
                    MERGE (f:File {id: $id})
                    SET f.name = $name, f.path = $path,
                        f.updated_at = timestamp(),
                        f.created_at = COALESCE(f.created_at, timestamp())
                    SET f:ArchNode
                """, {
                    "id": file_id,
                    "name": file,
                    "path": file_id
                })

                try:
                    with open(path, "r", encoding="utf-8") as f:
                        lines = f.readlines()
                        for i, line in enumerate(lines):
                            matches = re.findall(r"(TODO|FIXME|REQ-\d+|DES-\d+):?\s*(.*)", line)
                            for tag, msg in matches:
                                comment_id = f"comment-{file_id}-{i}"
                                await store.execute_query("""
                                    MERGE (c:Comment {id: $id})
                                    SET c.tag = $tag, c.content = $content, c.line = $line,
                                        c.name = $name, c.path = $path,
                                        c.created_at = COALESCE(c.created_at, timestamp())
                                    SET c:ArchNode
                                    WITH c
                                    MATCH (f:File {id: $file_id})
                                    MERGE (f)-[:HAS_COMMENT]->(c)
                                """, {
                                    "id": comment_id,
                                    "tag": tag,
                                    "content": msg.strip()[:100],
                                    "line": i + 1,
                                    "name": f"{tag}: {file}",
                                    "path": file_id,
                                    "file_id": file_id
                                })
                except:
                    pass

    print("[Industrial Index] Complete!")
    await store.close()

if __name__ == "__main__":
    asyncio.run(industrial_index())
