
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

from app.services.evolution.knowledge_distiller import knowledge_distiller
from app.services.agents.memory_bridge import SwarmMemoryBridge
from app.core.database import init_db, engine

async def test_learning_loop():
    print("Starting Evolutionary Learning Loop Test...")
    from sqlmodel import SQLModel
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # 1. Distill knowledge from past failures
    print("Step 1: Distilling pending reflections into consolidated directives...")
    try:
        count = await knowledge_distiller.distill_latest_reflections()
        print(f"Distilled {count} new/updated directives.")
    except Exception as e:
        print(f"Distillation failed (expected due to API): {e}")
        print("Manually seeding a directive for demonstration...")
        from app.models.evolution import CognitiveDirective
        from app.core.database import async_session_factory
        async with async_session_factory() as session:
            seed = CognitiveDirective(
                topic="RAG_RELIABILITY",
                directive="MANDATORY: Verify all citations against provided text chunks. No magic conclusions allowed.",
                confidence_score=0.95,
                version=1
            )
            session.add(seed)
            await session.commit()
            print("Seeded 'RAG_RELIABILITY' directive.")

    # 2. Verify and load via MemoryBridge
    print("\nStep 2: Verifying MemoryBridge recall...")
    bridge = SwarmMemoryBridge(user_id="l3_eval_bot")
    # Using a query that would match the topic
    context, is_high_risk = await bridge.load_historical_context("RAG reliability and citation check")
    
    print("\n--- RECALLED CONTEXT SNIPPET ---")
    if "SYSTEM DIRECTIVE" in context:
        # Grep for directives
        for line in context.split("\n"):
            if "!!! [SYSTEM DIRECTIVE]" in line:
                print(line)
    else:
        print("No directives found in context.")
    
    print(f"\nIs High Risk: {is_high_risk}")

if __name__ == "__main__":
    asyncio.run(test_learning_loop())
