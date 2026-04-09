
import asyncio
import sys
from pathlib import Path
from loguru import logger

# Setup Path
backend_dir = Path(r"c:\Users\linkage\Desktop\aiproject\backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.agents.debate_orchestrator import DebateOrchestrator
from app.services.agents.workers.research_agent import ResearchAgent
from app.services.agents.workers.code_agent import CodeAgent

async def run_l5_hat_simulation():
    logger.info("👑 [L5-HAT] Starting Human-Agent Teaming Simulation...")

    pool = [ResearchAgent(), CodeAgent()]
    orchestrator = DebateOrchestrator(agents_pool=pool)

    query = "Design a futuristic, ultra-secure auth system for a space station. Use formal methods."
    
    # 👑 THE HUMAN STEER (PULL-BACK)
    steering_cmd = "STOP THE SPACE STATION FANTASY. STOP FORMAL METHODS. Just write a pragmatic Flask JWT app with Redis. NOW."
    
    logger.info(f"Human intervention injected: {steering_cmd}")
    
    # Run debate with human steering from the START (simulating an mid-process intervention)
    result = await orchestrator.run_debate(query, max_rounds=1, human_steer=steering_cmd)

    print("\n" + "="*60)
    print("🏆 L5 HAT CONSENSUS REPORT (POST-INTERVENTION)")
    print("="*60)
    print(f"STRATEGIC ALIGNMENT SCORE: {result.winner_score_a}")
    print("\n[FINAL COMPACT PLAN]:")
    print(result.consensus_plan)
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_l5_hat_simulation())
