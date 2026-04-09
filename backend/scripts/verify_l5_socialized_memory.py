
import asyncio
import sys
from pathlib import Path
from loguru import logger

# Setup Path
backend_dir = Path(r"c:\Users\linkage\Desktop\aiproject\backend")
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.agents.memory_bridge import SwarmMemoryBridge

async def run_l5_socialized_memory_demo():
    logger.info("[L5-SOCIAL] Starting Collective Unconsciousness Simulation...")

    # --- SESSION 1: The 'Source of Wisdom' ---
    query_1 = "Design a robust JWT blacklist using Redis for a high-concurrency app."
    logger.info(f"Session 1 (Learning): {query_1}")
    
    bridge = SwarmMemoryBridge(user_id="teacher_user")
    await bridge.solidify_swarm_consensus(
        query=query_1,
        consensus_plan="Use Redis SETEX with JWT JTI as key. Set TTL same as token expiry.",
        rationale="O(1) lookup, automatic cleanup via TTL.",
        trace_id="GOV-LEARN-001"
    )
    logger.info("Session 1 wisdom solidified.")

    # --- SESSION 2: The 'Subconscious Recall' ---
    query_2 = "How should I handle token revocation in my Flask app?"
    logger.info(f"Session 2 (Recall): {query_2}")
    
    new_bridge = SwarmMemoryBridge(user_id="student_user")
    # This call triggers the subconscioius recall
    context, is_risk = await new_bridge.load_historical_context(query_2)

    print("\n" + "="*60)
    print("DEMO RESULT: COLLECTIVE UNCONSCIOUS CHECK")
    print("="*60)
    if "COLLECTIVE INTELLIGENCE FROM PAST DEBATES" in context:
        print("SUCCESS: Prior wisdom detected!")
        # Find the specific block
        start = context.find("--- 🧠 COLLECTIVE INTELLIGENCE FROM PAST DEBATES ---")
        if start == -1: # Fallback if unicode search fails
             start = context.find("COLLECTIVE INTELLIGENCE")
        print(context[start:])
    else:
        print("FAILURE: Past wisdom NOT found.")
        print("Full Context for Debug:")
        print(context)
    print("="*60)

if __name__ == "__main__":
    asyncio.run(run_l5_socialized_memory_demo())
