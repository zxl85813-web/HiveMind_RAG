import asyncio
import os
import sys
from pathlib import Path

# Add backend to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.sdk.core.graph_store import Neo4jStore
from app.core.database import async_session_factory
from app.models.knowledge import KnowledgeBase
from sqlmodel import delete

async def superior_fix():
    neo4j = Neo4jStore()
    
    print("--- 1. Aggressive Junk Purge (Neo4j) ---")
    # Delete anything suspicious
    junk_patterns = ['Torture Chamber', 'T', ' ', 'test_', 'Mock']
    for p in junk_patterns:
        q = "MATCH (n) WHERE n.name = $p OR n.name CONTAINS $p DETACH DELETE n"
        await neo4j.execute_query(q, {"p": p})
        print(f"Purged pattern: {p}")

    print("--- 2. Metadata Backfill & Inheritance ---")
    # Rule: Ensure all ArchNodes have a created_at
    ts_fix_q = "MATCH (n:ArchNode) WHERE n.created_at IS NULL SET n.created_at = timestamp(), n.updated_at = timestamp()"
    await neo4j.execute_query(ts_fix_q)
    print("Forced timestamps on all nodes.")

    # Rule: If a node is linked to a File, it should inherit the File's path
    inheritance_q = """
    MATCH (f:File)-[*..2]-(n:ArchNode)
    WHERE n.path IS NULL AND f.path IS NOT NULL
    SET n.path = f.path, n.created_at = COALESCE(n.created_at, f.created_at)
    RETURN count(*) as count
    """
    await neo4j.execute_query(inheritance_q)

    # Rule: If a node is linked to a File...

    # Rule: If ID looks like a path, use it
    path_infer_q = """
    MATCH (n:ArchNode)
    WHERE n.path IS NULL AND (n.id CONTAINS '/' OR n.id CONTAINS '.py' OR n.id CONTAINS '.tsx')
    SET n.path = n.id, n.created_at = COALESCE(n.created_at, timestamp())
    RETURN count(n) as count
    """
    res2 = await neo4j.execute_query(path_infer_q)
    print(f"Inferred path for {res2[0]['count']} nodes.")

    # Rule: Cleanup remaining nulls
    final_fallback = """
    MATCH (n:ArchNode)
    WHERE n.path IS NULL
    SET n.path = '[Virtual Asset]', n.created_at = COALESCE(n.created_at, timestamp())
    """
    await neo4j.execute_query(final_fallback)

    await neo4j.close()

    print("--- 3. SQL Cleanup (Postgres) ---")
    async with async_session_factory() as session:
        stmt = delete(KnowledgeBase).where(KnowledgeBase.name.like("%Torture Chamber%"))
        await session.execute(stmt)
        # Also delete KBs named 'T'
        stmt2 = delete(KnowledgeBase).where(KnowledgeBase.name == "T")
        await session.execute(stmt2)
        await session.commit()
    print("SQL Cleanup Complete.")

if __name__ == "__main__":
    asyncio.run(superior_fix())
