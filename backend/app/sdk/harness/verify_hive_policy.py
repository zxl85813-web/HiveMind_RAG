import asyncio
from app.sdk.harness.engine import get_harness_engine
from app.sdk.core.logging import logger

async def test_hive_redlines():
    engine = get_harness_engine()
    
    # 模拟场景 A: 违反 No-Print 规则
    bad_code_1 = """
def process_data(data):
    print(f"Processing: {data}")  # 违反 HIVE.md
    return data
    """
    logger.info("--- Scenario A: Testing 'print()' blocking ---")
    res1 = await engine.check_change({"content": bad_code_1})
    print(f"RESULT: {'PASS' if res1.passed else 'BLOCKED'} | msg: {res1.message}")

    print("\n" + "="*50 + "\n")

    # 模拟场景 B: 违反 Async-Only 规则
    bad_code_2 = """
import time
async def fetch_remote():
    time.sleep(5)  # 违反 HIVE.md 的非阻塞要求
    return "done"
    """
    logger.info("--- Scenario B: Testing Synchronous Blocking ---")
    res2 = await engine.check_change({"content": bad_code_2})
    print(f"RESULT: {'PASS' if res2.passed else 'BLOCKED'} | msg: {res2.message}")

if __name__ == "__main__":
    asyncio.run(test_hive_redlines())
