
import asyncio
import sys
from pathlib import Path
from loguru import logger

# Setup Path
backend_dir = Path(r"c:\Users\linkage\Desktop\aiproject\backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.agents.workers.scoping_agent import ScopingAgent

async def run_l5_scoping_demo():
    logger.info("🧐 [L5-SCOPING] Testing the 'Anti-Blind Discussion' Gate...")

    scoper = ScopingAgent()
    
    # 🌫️ VAGUE QUERY
    vague_query = "I want a multi-agent system for coding."
    
    audit = await scoper.audit_query(vague_query)

    print("\n" + "!"*60)
    print("🚦 SCOPING AUDIT REPORT")
    print("!"*60)
    print(f"IS CLEAR: {audit.is_clear}")
    print(f"MISSING: {audit.missing_dimensions}")
    print("\n[CRITICAL QUESTIONS FOR HUMAN]:")
    for q in audit.critical_questions:
        print(f"❓ {q}")
    print("\n[SUGGESTED DEFAULTS if no answer]:")
    print(audit.suggested_defaults)
    print("!"*60)

if __name__ == "__main__":
    asyncio.run(run_l5_scoping_demo())
