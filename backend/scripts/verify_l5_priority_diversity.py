
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

async def run_priority_diversity_test():
    logger.info("⚔️ [L5-PRIORITY-TEST] Testing Priority and Model Diversity...")

    # Setup context-aware agents
    pool = [ResearchAgent(), CodeAgent()]
    orchestrator = DebateOrchestrator(agents_pool=pool)

    # Test Case 1: Low Priority
    query_low = "How to add a comment to a python file?"
    logger.info(f"Test Case: LOW Priority - {query_low}")
    result_low = await orchestrator.run_debate(query_low)
    logger.info(f"Priority Detected: {result_low.scoping_audit.priority}")
    logger.info(f"Reasoning: {result_low.scoping_audit.priority_reasoning}")

    # Test Case 2: High Priority
    query_high = "Architect a global financial settlement system with sub-millisecond latency and PCI-DSS compliance."
    logger.info(f"Test Case: HIGH Priority - {query_high}")
    result_high = await orchestrator.run_debate(query_high)
    logger.info(f"Priority Detected: {result_high.scoping_audit.priority}")
    logger.info(f"Reasoning: {result_high.scoping_audit.priority_reasoning}")

    print("\n" + "█"*60)
    print("🏆 L5 PRIORITY & DIVERSITY REPORT")
    print("█"*60)
    print(f"CASE 1 (LOW)  - Priority: {result_low.scoping_audit.priority}")
    print(f"CASE 2 (HIGH) - Priority: {result_high.scoping_audit.priority}")
    print("█"*60)

if __name__ == "__main__":
    asyncio.run(run_priority_diversity_test())
