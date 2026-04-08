import asyncio
import logging
from app.sdk.harness.engine import get_harness_engine
from app.sdk.core.logging import logger

async def demo_harness():
    engine = get_harness_engine()
    
    # Scenario 1: Safe change
    safe_code = "print('Hello, HiveMind!')"
    logger.info("--- Scenario 1: Releasing SAFE code change ---")
    result1 = await engine.check_change({"content": safe_code})
    print(f"RESULT: {'PASS' if result1.passed else 'BLOCKED'} | msg: {result1.message}")

    print("\n" + "="*50 + "\n")

    # Scenario 2: Dangerous change (trying to import os)
    risky_code = """
import os
def delete_system():
    os.system('rm -rf /')
    """
    logger.info("--- Scenario 2: Releasing RISKY code change (import os) ---")
    result2 = await engine.check_change({"content": risky_code})
    print(f"RESULT: {'PASS' if result2.passed else 'BLOCKED'} | msg: {result2.message}")

if __name__ == "__main__":
    asyncio.run(demo_harness())
