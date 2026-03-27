import asyncio
import sys
from pathlib import Path
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

# Paths
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path: sys.path.insert(0, str(backend_dir))

from app.core.database import engine, init_db
from app.models.observability import SwarmSpan, SwarmTrace

async def inspect():
    await init_db()
    async with AsyncSession(engine) as session:
        # Get traces first
        stmt_t = select(SwarmTrace).order_by(SwarmTrace.created_at.desc()).limit(4)
        traces = (await session.exec(stmt_t)).all()
        
        print(f"=== EVALUATION TRACE AUDIT ({len(traces)}) ===")
        for t in reversed(traces):
            print(f"\n[TRACE] Query: {t.query}")
            print(f"Status: {t.status} | Time: {t.latency_ms:.1f}ms")
            
            # Get spans for this trace
            stmt_s = select(SwarmSpan).where(SwarmSpan.swarm_trace_id == t.id).order_by(SwarmSpan.created_at.asc())
            spans = (await session.exec(stmt_s)).all()
            for s in spans:
                print(f"  -> {s.agent_name} | Out: {s.output[:200]}...")
            print("-" * 50)

if __name__ == "__main__":
    asyncio.run(inspect())
