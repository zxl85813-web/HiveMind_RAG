import asyncio
import os
import sys
from pathlib import Path

# Add backend to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

from app.core.database import async_session_factory
from app.models.knowledge import KnowledgeBase
from sqlmodel import select, delete

async def cleanup_kb():
    print("[Cleanup] Removing 'Torture Chamber' from KnowledgeBase (Postgres)...")
    async with async_session_factory() as session:
        # Find and Delete
        stmt = delete(KnowledgeBase).where(KnowledgeBase.name.like("%Torture Chamber%"))
        result = await session.execute(stmt)
        await session.commit()
        print(f"Cleanup complete in SQL.")

if __name__ == "__main__":
    asyncio.run(cleanup_kb())
