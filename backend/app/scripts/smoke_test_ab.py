import asyncio
import json
import time

from loguru import logger

from app.agents.swarm import SwarmOrchestrator
from app.services.evaluation.ab_tracker import ab_tracker


async def run_smoke_test():
    swarm = SwarmOrchestrator()
    # SC-01: Simple RAG
    query = "HiveMind 是什么？它有哪些核心组件？"
    variants = ["monolithic", "react"]

    logger.info("💨 Starting Smoke Test for A/B CoT Control...")

    for var in variants:
        logger.info(f"--- Variant: {var} ---")
        context = {"execution_variant": var}
        start_t = time.monotonic()
        try:
            # First invoke might trigger heavy loading (MCP/Skills)
            await swarm.invoke(query, context=context, conversation_id=f"smoke_{var}")
            logger.info(f"✅ {var} Test Completed in {(time.monotonic()-start_t)*1000:.0f}ms")
        except Exception as e:
            logger.error(f"❌ {var} Failed: {e}")

    summary = ab_tracker.get_summary()
    print("\n" + "="*50)
    print("A/B COHORT SMOKE TEST SUMMARY")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("="*50)

if __name__ == "__main__":
    asyncio.run(run_smoke_test())
