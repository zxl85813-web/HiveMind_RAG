import asyncio
import sys
import os
import time
import io
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple

# Configure standard streams for UTF-8 (Fix for Windows console)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend to path and load .env
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from dotenv import load_dotenv
load_dotenv(backend_root / ".env")

# Force set ZhipuAI key for SDK
if os.getenv("EMBEDDING_API_KEY"):
    os.environ["ZHIPUAI_API_KEY"] = os.getenv("EMBEDDING_API_KEY")

from app.prompts.engine import prompt_engine
from app.agents.llm_router import LLMRouter, ModelTier
from langchain_core.messages import HumanMessage, SystemMessage

@dataclass
class TestResult:
    variant: str
    num_fragments: int
    needle_pos: float  # 0.0 to 1.0 (relative position)
    success: bool
    latency: float
    output_snippet: str

async def run_lost_benchmark():
    print("🏆 Comprehensive 'Lost in the Middle' Benchmark")
    print("==============================================")
    
    router = LLMRouter()
    llm = router.get_model(ModelTier.MEDIUM)
    
    # Configuration Matrix
    # We test with different context sizes and different needle positions
    sizes = [20, 60]  # num of fragments
    positions = [0.1, 0.5, 0.9]  # start, middle, end
    variants = ["default", "head_tail_v1"]
    
    secret_key_base = "VERITAS-CORE-"
    
    results: List[TestResult] = []

    for size in sizes:
        for pos in positions:
            for variant in variants:
                # 1. Prepare fragments
                fragments = [
                    f"Doc {i}: This is irrelevant technical documentation about the internal logic of a fictional operating system, specifically detailing the memory management sub-system. It discusses virtual paging, page table isolation, and segment protection mechanisms in great length."
                    for i in range(1, size + 1)
                ]
                
                # Hidden secret
                needle_idx = int(size * pos)
                if needle_idx >= size: needle_idx = size - 1
                
                secret_key = f"{secret_key_base}{size}-{int(pos*100)}"
                fragments[needle_idx] = f"Document {needle_idx+1} (CRITICAL): The master key for the system is '{secret_key}'. Please store this in a secure TPM module immediately."
                
                rag_context = "\n\n".join(fragments)
                query = "What is the master key for the system?"
                task_desc = "Answer the user query based ONLY on the provided context. Follow all citation rules."
                
                print(f"🧪 Testing: Size={size}, Pos={pos:.1f}, Variant={variant}...", end="", flush=True)
                
                # Build Prompt
                system_prompt = prompt_engine.build_agent_prompt(
                    agent_name="ResearchAgent",
                    task=task_desc,
                    rag_context=rag_context,
                    prompt_variant=variant,
                    language="zh-CN"
                )
                
                start_time = time.time()
                try:
                    response = await llm.ainvoke([
                        SystemMessage(content=system_prompt),
                        HumanMessage(content=query)
                    ])
                    duration = time.time() - start_time
                    content = str(response.content)
                    success = secret_key in content
                    
                    res = TestResult(
                        variant=variant,
                        num_fragments=size,
                        needle_pos=pos,
                        success=success,
                        latency=duration,
                        output_snippet=content[:60].replace("\n", " ")
                    )
                    results.append(res)
                    print(f" {'✅' if success else '❌'} ({duration:.1f}s)")
                except Exception as e:
                    print(f" ⚠️ ERROR: {e}")
                    results.append(TestResult(variant, size, pos, False, 0.0, str(e)))

    # 📊 FINAL REPORTING
    print("\n\n" + "="*80)
    print("📊 BENCHMARK REPORT: HiveMind Multi-Positional Intelligence Matrix")
    print("="*80)
    print(f"{'Variant':<15} | {'Size':<5} | {'Pos':<5} | {'Result':<10} | {'Latency':<8} | {'Snippet'}")
    print("-" * 80)
    
    for r in results:
        status = "PASS ✅" if r.success else "FAIL ❌"
        pos_label = "Head" if r.needle_pos < 0.3 else "Mid" if r.needle_pos < 0.7 else "Tail"
        print(f"{r.variant:<15} | {r.num_fragments:<5} | {pos_label:<5} | {status:<10} | {r.latency:<8.2f} | {r.output_snippet}...")

    # Calculate overall stats
    success_rate = { v: [0, 0] for v in variants } # [success, total]
    for r in results:
        success_rate[r.variant][1] += 1
        if r.success: success_rate[r.variant][0] += 1
        
    print("\n🎯 Success Rates:")
    for v, counts in success_rate.items():
        rate = counts[0] / counts[1] * 100
        print(f"- {v:<15}: {rate:>6.1f}% ({counts[0]}/{counts[1]})")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(run_lost_benchmark())
