import io
import sys
import asyncio
import os
import uuid
from pathlib import Path
from datetime import datetime

# Configure standard streams for UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend to path and load .env
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def load_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    parts = line.strip().split("=", 1)
                    if len(parts) == 2:
                        key, value = parts
                        os.environ[key] = value.strip('"').strip("'")
load_env()

# Fresh DB for isolated Scenario F test
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./f_fresh.db"

from app.services.agents.supervisor import SupervisorAgent
from app.services.agents.workers.research_agent import ResearchAgent
from app.services.agents.workers.code_agent import CodeAgent
from app.services.agents.workers.reviewer_agent import ReviewerAgent
from app.services.agents.memory_bridge import SwarmMemoryBridge
from app.core.database import init_db, engine
from sqlmodel import SQLModel

async def run_scenario_f_fresh():
    print("🎬 SCENARIO F: Cognitive Self-Evolution (Guided Recall)")
    
    # 0. Prep Fresh DB
    await init_db()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        
    # 🧪 Pre-seed a GAP Reflection representing a 'Past Failure' for JWT
    from app.models.agents import ReflectionEntry, ReflectionType
    from sqlmodel.ext.asyncio.session import AsyncSession
    
    async with AsyncSession(engine) as session:
        entry = ReflectionEntry(
            type=ReflectionType.KNOWLEDGE_GAP,
            agent_name='HVM-Reviewer',
            signal_type='gap',
            topic='JWT Middleware',
            summary='Previous JWT implementation MISSES XSS filtering headers and had insecure default alg.',
            action_taken='Always include helmet-style security headers and force RS256.',
            match_key='swarm_fail_f_user',
            confidence_score=0.95
        )
        session.add(entry)
        await session.commit()
    print("✅ Seeded Reflection Log with a PAST FAILURE regarding JWT.")
        
    user_id = "f_user"
    agents = [ResearchAgent(), CodeAgent(), ReviewerAgent()]
    supervisor = SupervisorAgent(agents=agents, user_id=user_id)

    objective = "再次尝试设计 JWT 中间件方案。"
    print(f"\n[Objective] {objective}")
    
    results = await supervisor.run_swarm(objective, user_id=user_id)
    print(f"\n🏁 [Result] Status: {results.get('status')} | Trace: {results.get('trace_id')}")
    
    # Verify Recall
    import aiosqlite
    async with aiosqlite.connect("f_fresh.db") as db:
        async with db.execute("SELECT triage_reasoning FROM obs_swarm_traces WHERE id = ?", (results.get("trace_id"),)) as cur:
            row = await cur.fetchone()
            if row:
                reasoning = row[0]
                print("\n--- 🧠 Cognitive Audit (Reasoning) ---")
                print(reasoning)
                if "XSS" in reasoning or "correction" in reasoning.lower() or "previous" in reasoning.lower():
                    print("\n🏆 SUCCESS: Supervisor successfully RECALLED the past failure and adjusted the plan!")
                else:
                    print("\n⚠️ PARTIAL: Supervisor used internal knowledge but didn't explicitly link to reflection ID.")

if __name__ == "__main__":
    try:
        asyncio.run(run_scenario_f_fresh())
    except Exception as e:
        print(f"CRASHED: {e}")
