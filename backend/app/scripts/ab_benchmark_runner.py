import asyncio
import json
import time

from loguru import logger

from app.agents.swarm import SwarmOrchestrator
from app.services.evaluation.ab_tracker import ab_tracker


async def run_benchmark():
    swarm = SwarmOrchestrator()

    scenarios = [
        {"id": "SC-01", "name": "Simple RAG", "query": "HiveMind 是什么？它有哪些核心组件？"},
        {"id": "SC-02", "name": "Multi-step Web", "query": "查询 2024 年奥斯卡最佳影片是谁，并搜索该片导演的其他三部代表作。"},
        {"id": "SC-03", "name": "Logic Code", "query": "计算 1234567 的质因数分解，并用 Python 验证结果。"}
    ]

    variants = ["monolithic", "react"]
    rounds = 3

    logger.info("🚀 Starting Multi-round CoT A/B Benchmark...")

    results = []

    for round_idx in range(1, rounds + 1):
        logger.info(f"--- Round {round_idx} ---")
        for sc in scenarios:
            for var in variants:
                logger.info(f"Testing Scenario {sc['id']} | Variant: {var}")

                # Force variant via context
                context = {
                    "execution_variant": var,
                    "user_id": "benchmark_user"
                }

                try:
                    start_time = time.monotonic()
                    # Perform invoke
                    response = await swarm.invoke(sc['query'], context=context, conversation_id=f"bench_{sc['id']}_{var}_{round_idx}")
                    total_latency = (time.monotonic() - start_time) * 1000

                    # Get thinking stats from response
                    thinking_times = response.get("thinking_time_ms", [])
                    total_think_ms = sum(thinking_times)
                    num_calls = len(thinking_times)

                    results.append({
                        "round": round_idx,
                        "scenario": sc['id'],
                        "variant": var,
                        "total_latency_ms": total_latency,
                        "total_think_ms": total_think_ms,
                        "num_calls": num_calls
                    })

                    logger.info(f"✅ Finished: Think={total_think_ms:.0f}ms, Calls={num_calls}")
                except Exception as e:
                    logger.error(f"❌ Failed Scenario {sc['id']} ({var}): {e}")

    # Output Final Summary
    logger.info("📊 Benchmark Complete. Summarizing...")
    summary = ab_tracker.get_summary()
    print("\n" + "="*50)
    print("FINAL A/B BENCHMARK SUMMARY")
    print("="*50)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print("="*50)

if __name__ == "__main__":
    asyncio.run(run_benchmark())
