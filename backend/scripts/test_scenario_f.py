import asyncio
import sys
import os
from pathlib import Path

# Add backend to path and load .env
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def load_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value.strip('"').strip("'")
load_env()

# Only keep the test db override
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_swarm.db")

from app.services.agents.supervisor import SupervisorAgent
from app.services.agents.workers.research_agent import ResearchAgent
from app.services.agents.workers.code_agent import CodeAgent
from app.services.agents.workers.reviewer_agent import ReviewerAgent
from app.services.agents.memory_bridge import SwarmMemoryBridge
from app.core.database import init_db, engine
from sqlmodel import SQLModel

async def run_scenario_f():
    print("🎬 SCENARIO F: 认知闭环自进化 (Reflection Feedback)")
    
    await init_db()
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        
    user_id = "suite_test_user"
    agents = [ResearchAgent(), CodeAgent(), ReviewerAgent()]
    supervisor = SupervisorAgent(agents=agents, user_id=user_id)

    objective = "再次尝试设计 JWT 中间件。由于黑板中存有之前的 GAP 反思（关于 XSS 过滤），观察 Supervisor 此时生成的 T1 指令是否已经预埋了'注意 XSS 过滤'的 Checkpoint。"
    
    results = await supervisor.run_swarm(objective, user_id=user_id)
    print(f"\n🏁 [Result] Status: {results.get('status')} | Trace: {results.get('trace_id')}")

if __name__ == "__main__":
    asyncio.run(run_scenario_f())
