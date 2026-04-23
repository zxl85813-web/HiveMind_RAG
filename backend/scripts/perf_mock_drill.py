import asyncio
import time
import argparse
import random
import statistics
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any
from unittest.mock import MagicMock, AsyncMock, patch

# 🏗️ [Phase 1]: Path and Context Setup
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.logging import setup_script_context, get_trace_logger
from app.schemas.knowledge_protocol import KnowledgeResponse, KnowledgeFragment, KnowledgeQuality
from app.services.llm_gateway import GatewayResponse

setup_script_context("perf_mock_drill")
logger = get_trace_logger("scripts.perf_mock_drill")

@dataclass
class PerfResult:
    latencies: List[float] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def total_requests(self) -> int:
        return self.success_count + self.failure_count

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    @property
    def rps(self) -> float:
        return self.total_requests / self.duration if self.duration > 0 else 0

    def get_stats(self) -> Dict[str, Any]:
        if not self.latencies:
            return {}
        return {
            "rps": round(self.rps, 2),
            "total": self.total_requests,
            "success": self.success_count,
            "failure": self.failure_count,
            "p50": round(statistics.median(self.latencies) * 1000, 2),
            "p90": round(statistics.quantiles(self.latencies, n=10)[8] * 1000, 2) if len(self.latencies) >= 10 else 0,
            "p99": round(statistics.quantiles(self.latencies, n=100)[98] * 1000, 2) if len(self.latencies) >= 100 else 0,
            "avg": round(statistics.mean(self.latencies) * 1000, 2),
            "duration_sec": round(self.duration, 2)
        }

# --- Mock Implementations ---

async def mock_llm_call(tier: int, prompt: str, system_prompt: str, **kwargs) -> GatewayResponse:
    # Simulate some internal processing time
    await asyncio.sleep(random.uniform(0.01, 0.05)) 
    return GatewayResponse(
        content=f"Mock response for tier {tier}. Input: {prompt[:20]}...",
        metadata={"model": "mock-llm", "tier": tier, "mocked": True}
    )

async def mock_rag_retrieve(query: str, kb_ids: list, **kwargs) -> KnowledgeResponse:
    # Simulate retrieval latency (e.g. Elasticsearch/VectorDB)
    await asyncio.sleep(random.uniform(0.02, 0.1))
    return KnowledgeResponse(
        query=query,
        fragments=[
            KnowledgeFragment(
                content=f"Mock fragment for {query}",
                kb_id="mock-kb",
                source_id="doc-1",
                chunk_index=0,
                score=0.9
            )
        ],
        total_found=1,
        processing_time_ms=50.0,
        quality=KnowledgeQuality(max_score=0.9, avg_score=0.9, is_satisfactory=True, quality_tier="EXCELLENT")
    )

# --- Test Scenarios ---

async def simulate_chat_user(user_id: int, result: PerfResult, semaphore: asyncio.Semaphore):
    async with semaphore:
        start = time.perf_counter()
        try:
            from app.services.chat_service import chat_service
            # We assume chat_service uses llm_gateway which we will patch in main
            await chat_service.create_conversation(user_id=f"user-{user_id}", title=f"Perf Test {user_id}")
            # Note: In a real test, we'd call the actual endpoint or service method
            # For this drill, we simulate a chat completion call
            from app.services.llm_gateway import llm_gateway
            await llm_gateway.call_tier(tier=1, prompt="Hello", system_prompt="Be a mock")
            
            result.latencies.append(time.perf_counter() - start)
            result.success_count += 1
        except Exception as e:
            logger.error(f"User {user_id} failed: {e}")
            result.failure_count += 1

async def simulate_query_user(user_id: int, result: PerfResult, semaphore: asyncio.Semaphore):
    async with semaphore:
        start = time.perf_counter()
        try:
            from app.services.rag_gateway import RAGGateway
            gateway = RAGGateway()
            # We will patch retrieve in main
            await gateway.retrieve(query=f"What is {user_id}?", kb_ids=["mock-kb"])
            
            result.latencies.append(time.perf_counter() - start)
            result.success_count += 1
        except Exception as e:
            logger.error(f"Query {user_id} failed: {e}")
            result.failure_count += 1

# --- Main Runner ---

async def run_perf_test(mode: str, total: int, concurrent: int):
    result = PerfResult()
    semaphore = asyncio.Semaphore(concurrent)
    
    logger.info(f"🚀 Starting Mock Perf Drill | Mode: {mode} | Total: {total} | Concurrent: {concurrent}")
    
    # 🧪 [Mock Patching]
    with patch("app.services.llm_gateway.LLMGateway.call_tier", side_effect=mock_llm_call), \
         patch("app.services.rag_gateway.RAGGateway.retrieve", side_effect=mock_rag_retrieve):
        
        result.start_time = time.perf_counter()
        
        tasks = []
        for i in range(total):
            if mode == "chat":
                tasks.append(simulate_chat_user(i, result, semaphore))
            else:
                tasks.append(simulate_query_user(i, result, semaphore))
        
        await asyncio.gather(*tasks)
        
        result.end_time = time.perf_counter()

    stats = result.get_stats()
    logger.success(f"🏁 Perf Drill Completed: {stats}")
    
    # Export report
    report_path = backend_dir / "logs" / "perf" / f"mock_{mode}_{int(time.time())}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    report_path.write_text(json.dumps(stats, indent=2))
    print(f"\nReport saved to: {report_path}")
    return stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["chat", "query"], default="chat")
    parser.add_argument("--total", type=int, default=100)
    parser.add_argument("--concurrent", type=int, default=10)
    args = parser.parse_args()
    
    asyncio.run(run_perf_test(args.mode, args.total, args.concurrent))
