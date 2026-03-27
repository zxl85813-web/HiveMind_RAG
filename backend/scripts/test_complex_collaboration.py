import asyncio
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Add backend to path and load .env
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

def load_env():
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        print(f"📡 Loading real keys from {env_path}")
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value.strip('"').strip("'")
    else:
        print("⚠️ No .env found in backend/")

load_env()

# Only keep the test db override
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./complex_swarm_test.db")
from app.services.agents.supervisor import SupervisorAgent
from app.services.agents.workers.research_agent import ResearchAgent
from app.services.agents.workers.code_agent import CodeAgent
from app.services.agents.workers.reviewer_agent import ReviewerAgent
from app.services.agents.memory_bridge import SwarmMemoryBridge
from app.core.database import init_db, engine
from sqlmodel import SQLModel, select
from app.models.observability import SwarmTrace, SwarmSpan

async def run_complex_simulation():
    print("🔥 [HiveMind Lab] Starting Complex Collaboration & Observability Stress Test")
    
    # 0. Prep Environment
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    user_id = "stress_test_user_001"
    memory = SwarmMemoryBridge(user_id=user_id)
    
    # 1. Initialize Swarm with full Expert Panel
    agents = [ResearchAgent(), CodeAgent(), ReviewerAgent()]
    supervisor = SupervisorAgent(agents=agents, user_id=user_id)
    
    # 2. Define Complex Objective
    # Needs Research -> Design -> Cross-Review -> Final Synthesis
    objective = """
    设计一个符合 GDPR 标准的分布式身份认证中间件方案。要求：
    1. 调研最新的 JWT 安全堆栈建议 (Research)
    2. 生成中间件核心代码 (Code)
    3. 针对跨站攻击 (XSS/CSRF) 进行同行评审 (Reviewer)
    """
    
    print(f"\n[Objective] {objective.strip()}\n")
    
    # 3. Execution with Cognitive Loop
    start_time = datetime.now()
    results = await supervisor.run_swarm(objective, user_id=user_id)
    duration = (datetime.now() - start_time).total_seconds()
    
    print(f"\n✅ Swarm Execution Finished in {duration:.2f}s")
    print(f"Status: {results.get('status')}")
    print(f"Trace Id: {results.get('trace_id')}")
    
    # 4. TRACE DRILLING (可观察性验证)
    print("\n--- 🧭 [Observability Drill] Recovering Execution Traces ---")
    trace_id = results.get("trace_id")
    
    # Wait a bit for async background spans to finish writing
    await asyncio.sleep(2)
    
    async with engine.connect() as conn:
        # Fetch the root trace
        # Using SQLModel's session for cleaner syntax if we had it, but async engine works too
        from sqlalchemy import text
        
        # 1. Check Root Trace
        trace_q = text("SELECT * FROM obs_swarm_traces WHERE id = :tid")
        trace_res = await conn.execute(trace_q, {"tid": trace_id})
        trace = trace_res.first()
        if trace:
            print(f"📍 Root Trace Status: {trace.status}")
            print(f"💭 Supervisor Reasoning: {trace.triage_reasoning[:200] if trace.triage_reasoning else 'N/A'}...")
        
        # 2. Check Spans (The "Steps" left by agents)
        spans_q = text("SELECT * FROM obs_swarm_spans WHERE swarm_trace_id = :tid ORDER BY created_at")
        spans_res = await conn.execute(spans_q, {"tid": trace_id})
        spans = spans_res.all()
        
        print(f"\n👣 [Agent Steps] Found {len(spans)} segments on the blackboard:")
        for s in spans:
            print(f"   [{s.agent_name}] -> {s.status} ({s.latency_ms:.0f}ms)")
            if s.agent_name == "HVM-Reviewer":
                print(f"      🛡️ Reviewer Audit Result: {str(s.output)[:100]}...")

    # 5. MEMORY PERSISTENCE CHECK (留痕迹验证)
    print("\n--- 💾 [Persistence Audit] Memory Recall Verification ---")
    # Verify if we can recall this context now
    recall = await memory.load_historical_context("GDPR JWT Middleware")
    if "GDPR" in recall:
        print("✅ Success: The Swarm outcome has been persisted to L3/L5 semantic memory!")
    else:
        print("⚠️ Warning: Could not find GDPR in recalled memory.")

if __name__ == "__main__":
    asyncio.run(run_complex_simulation())
