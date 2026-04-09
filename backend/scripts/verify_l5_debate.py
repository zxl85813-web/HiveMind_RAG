
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

async def run_l5_debate_simulation():
    logger.info("⚔️ [L5-SIMULATION] Initializing Inter-Swarm Debate...")

    # Setup context-aware agents
    pool = [ResearchAgent(), CodeAgent()]
    orchestrator = DebateOrchestrator(agents_pool=pool)

    query = "Design a production-ready authentication system for a trillion-dollar e-commerce platform. Focus on ACTIONABLE architecture, not academic proofs."

    logger.info(f"The Focused Debate Query: {query}")
    
    result = await orchestrator.run_debate(query, max_rounds=1)

    print("\n" + "█"*60)
    print("🏆 L5 DEBATE CONSENSUS REPORT")
    print("█"*60)
    print(f"WINNER PERFORMANCE SCORE: {result.winner_score_a}")
    print(f"WINNER SECURITY SCORE: {result.winner_score_b}")
    print("\n[SYNTHESIZED GOLDEN PLAN]:")
    print(result.consensus_plan)
    print("█"*60)

if __name__ == "__main__":
    asyncio.run(run_l5_debate_simulation())
