
import asyncio
import os
import sys
from pathlib import Path

# Setup Path
backend_dir = Path(r"c:\Users\linkage\Desktop\aiproject\backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///c:/Users/linkage/Desktop/aiproject/hivemind.db"
os.environ["TESTING"] = "1"

from app.services.agents.memory_bridge import SwarmMemoryBridge
from app.core.database import engine
from app.models.evolution import CognitiveDirective
from sqlmodel import SQLModel

async def test_memory_recall():
    print("Starting Memory Recall Test...")
    
    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # 1. Manually seed a directive
    print("Step 1: Seeding a consolidated directive...")
    from app.core.database import async_session_factory
    async with async_session_factory() as session:
        # Clear old ones
        from sqlmodel import delete
        await session.execute(delete(CognitiveDirective))
        
        seed = CognitiveDirective(
            topic="RAG_STABILITY",
            directive="MANDATORY: Check document timestamps before citing.",
            confidence_score=0.99,
            version=2
        )
        session.add(seed)
        await session.commit()
        print("Seeded 'RAG_STABILITY' directive.")

    # 2. Verify recall via MemoryBridge
    print("\nStep 2: Verifying MemoryBridge recall...")
    bridge = SwarmMemoryBridge(user_id="demo_user")
    # This query should be fast as it now handles LLM errors gracefully
    context, is_high_risk = await bridge.load_historical_context("RAG stability check")
    
    print("\n--- RECALLED CONTEXT ---")
    print(context)
    
    if "SYSTEM DIRECTIVE" in context and "MANDATORY: Check document timestamps" in context:
        print("\n✅ SUCCESS: Learning Write-Back Verified!")
    else:
        print("\n❌ FAILED: Directive not found in context.")

if __name__ == "__main__":
    asyncio.run(test_memory_recall())
