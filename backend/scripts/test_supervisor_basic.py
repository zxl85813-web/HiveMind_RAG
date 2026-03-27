import asyncio
import sys
from pathlib import Path

# Paths
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path: sys.path.insert(0, str(backend_dir))

from app.services.agents.supervisor import SupervisorAgent
from app.services.agents.workers.research_agent import ResearchAgent

async def test_minimal():
    print("Testing Minimal Supervisor Planning...")
    supervisor = SupervisorAgent(agents=[ResearchAgent()], user_id="test_user")
    
    # Let's see the planner response directly
    plan = await supervisor._plan("Write a simple hello world.")
    print(f"\n[PLAN REASONING] {plan.reasoning}")
    print(f"[TASKS] {plan.tasks}")
    
    if not plan.tasks:
        print("\n🚨 PLANNER RETURNED ZERO TASKS. Check LLM Gateway.")

if __name__ == "__main__":
    from app.core.logging import setup_script_context
    setup_script_context("test_sup")
    asyncio.run(test_minimal())
