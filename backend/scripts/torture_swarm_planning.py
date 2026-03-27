"""
Test Cognitive Loop (M4.2.0)

Simulates the DAG execution and validation loop for the new HiveMind Supervisor Architecture.
"""

import sys
import os
import asyncio
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path: sys.path.insert(0, str(backend_dir))
from dotenv import load_dotenv
load_dotenv(backend_dir / ".env")

from app.services.agents.supervisor import SupervisorAgent
from app.services.agents.workers.research_agent import ResearchAgent
from app.services.agents.workers.code_agent import CodeAgent

async def run_cognitive_challenge():
    print("[Swarm Cognitive Loop] Initializing Agent Swarm...")
    
    agents = [
        ResearchAgent(kb_ids=[]),
        CodeAgent()
    ]
    
    supervisor = SupervisorAgent(agents=agents, max_loops=3)
    
    query = "Investigate the HiveMind security rules for Context Expansion and write a Python script verifying ACL logic."
    print(f"\n[Objective] {query}\n")
    
    print("Triggering Swarm Execution (Research -> Plan -> Execute -> Verify)")
    result = await supervisor.run_swarm(query=query)
    
    print("\n[Swarm Result]")
    print(f"Success: {result['success']}")
    print(f"Loops Used: {result.get('loops_used', 0)}")
    
    print("\n[Final Shared Context (Outputs)]")
    if 'final_context' in result:
        for t_id, t_out in result['final_context'].items():
            print(f"--- Task {t_id} ---")
            print(f"{str(t_out)[:300]}...\n")
            
    print("\n--- DONE ---")

if __name__ == "__main__":
    asyncio.run(run_cognitive_challenge())
