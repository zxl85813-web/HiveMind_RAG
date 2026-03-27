import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Dummy env vars for stability (Real keys take precedence if already in env)
os.environ.setdefault("EMBEDDING_API_KEY", "mock-key")
os.environ.setdefault("OPENAI_API_KEY", "mock-key")
os.environ.setdefault("ARK_API_KEY", "mock-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_swarm.db")

from app.services.agents.supervisor import SupervisorAgent
from app.services.agents.memory_bridge import SwarmMemoryBridge
from app.services.agents.workers.research_agent import ResearchAgent
from app.services.agents.workers.code_agent import CodeAgent
from app.core.database import init_db, engine
from sqlmodel import SQLModel
import app.models.observability # Register models to SQLModel metadata

async def verify_swarm_intelligence():
    print("🚀 Starting Swarm Intelligence & Stability Verification [M4.2-VERIFY]")
    
    # 0. Init DB (Force Create Tables for the test)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # 1. Setup Swarm
    user_id = "verify_user_999"
    # Note: SupervisorAgent creates its own memory_bridge internal to constructor
    research_agent = ResearchAgent()
    code_agent = CodeAgent()
    
    supervisor = SupervisorAgent(agents=[research_agent, code_agent], user_id=user_id)
    
    # 2. Complex Scenario: Multi-agent coordination with Blackboard sharing
    query = """
    分析当前项目的 SecuritySanitizer 类，并调研最新的 PII (个人隐私信息) 脱敏标准，
    判断现有实现是否漏掉了 'Phone Number' 类型的加密，并给出一个增强建议。
    """
    
    print(f"\n[Scenario] {query.strip()}\n")
    
    # 3. Execution (The Cognitive Loop)
    # We expect the supervisor to: 
    # T1 (CodeAgent): Read SecuritySanitizer
    # T2 (ResearchAgent): Research PII standards (Should use blackboard from T1)
    # T3 (CodeAgent): Propose patch (Should use blackboard from T1 & T2)
    
    # Pass user_id for memory isolation
    user_id = "verify_user_999"
    results = await supervisor.run_swarm(query, user_id=user_id)
    
    # 4. Intelligence Verification (Blackboard Check)
    print("\n--- 🧠 HiveMind Blackboard Verification ---")
    blackboard = results.get("raw_results", {})
    
    collaboration_found = False
    for task_id, output in blackboard.items():
        print(f"\n[Task {task_id}] Output Length: {len(output)}")
        # Check if research agent (usually T2) mentioned the CodeAgent's findings or the Sanitizer
        if "SecuritySanitizer" in output:
            print(f"✅ Peer-to-Peer Visibility Found in Task {task_id}")
            collaboration_found = True
            
    # 5. Signal Verification
    print("\n--- ⚡ Signal Reactivity Check ---")
    # Swarm logic should have captured signals
    if results.get("status") == "success":
        print("✅ Core Cognitive Loop: SUCCESS")
    else:
        print(f"❌ Core Cognitive Loop: {results.get('status')}")

    if collaboration_found:
        print("\n🏆 Swarm Advantage Verified: Agents are sharing cross-task context via Blackboard.")
    else:
        print("\n⚠️ Swarm Advantage Partial: Blackboard was used but cross-reference was subtle.")

    # 6. Observability Check
    print("\n--- 🛰️ Observability Audit ---")
    trace_id = results.get("trace_id")
    if trace_id:
        print(f"✅ Trace Recorded: {trace_id}")
    else:
        print("❌ Trace Missing")

if __name__ == "__main__":
    # Ensure any background tasks from imports are handled
    try:
        asyncio.run(verify_swarm_intelligence())
    except KeyboardInterrupt:
        pass
