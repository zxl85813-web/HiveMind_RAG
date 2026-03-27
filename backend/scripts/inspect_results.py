import asyncio
import sys
from pathlib import Path
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# Paths
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path: sys.path.insert(0, str(backend_dir))

from app.core.database import engine, init_db
from app.models.observability import SwarmSpan

async def inspect():
    await init_db()
    async with AsyncSession(engine) as session:
        stmt = select(SwarmSpan).order_by(SwarmSpan.created_at.desc()).limit(10)
        results = (await session.exec(stmt)).all()
        
        print(f"--- LATEST SPANS ({len(results)}) ---")
        for s in results:
            print(f"\n[ID: {s.id}] Agent: {s.agent_name}")
            print(f"Instruction: {s.instruction[:100]}...")
            print(f"Output: {s.output[:1000]}...")
            print("-" * 20)

if __name__ == "__main__":
    asyncio.run(inspect())
