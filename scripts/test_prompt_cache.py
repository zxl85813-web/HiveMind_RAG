#!/usr/bin/env python3
"""
Three-Layer Prompt Cache Test
==============================
测试三层 Prompt 架构的 Redis 缓存和 DeepSeek KV Cache 命中效果。

测试流程:
  1. 清除所有 Harness prompt 缓存
  2. 第一次调用 build_static_shell() — 预期 Redis MISS，查图谱
  3. 第二次调用 build_static_shell() — 预期 Redis HIT
  4. 调用 assemble_prompt() 两次，观察 system_prompt 是否一致
  5. 用相同的 system_prompt 调用 LLM 两次，观察 KV Cache 命中

用法:
    cd backend
    python ../scripts/test_prompt_cache.py
"""

import asyncio
import sys
import time
from pathlib import Path

# 确保 backend 在 path 中
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from dotenv import load_dotenv
load_dotenv(BASE_DIR / "backend" / ".env")


async def test_redis_cache():
    """测试 Redis 层的缓存命中。"""
    print("=" * 70)
    print("  TEST 1: Redis Cache (Layer 1 + Layer 2)")
    print("=" * 70)

    from app.sdk.harness.prompt_assembler import (
        build_static_shell,
        build_warm_context,
        invalidate_prompt_cache,
        assemble_prompt,
    )

    # 1. 清除缓存
    cleared = await invalidate_prompt_cache()
    print(f"\n  [Setup] Cleared {cleared} cache keys.")

    # 2. 第一次调用 — 预期 MISS
    t0 = time.monotonic()
    shell_1 = await build_static_shell("CodeAgent")
    t1 = time.monotonic()
    print(f"\n  [Call 1] build_static_shell('CodeAgent')")
    print(f"    Time:   {(t1-t0)*1000:.1f}ms")
    print(f"    Length: {len(shell_1)} chars")
    print(f"    Status: {'MISS (expected)' if (t1-t0) > 0.01 else 'HIT (unexpected)'}")

    # 3. 第二次调用 — 预期 HIT
    t2 = time.monotonic()
    shell_2 = await build_static_shell("CodeAgent")
    t3 = time.monotonic()
    print(f"\n  [Call 2] build_static_shell('CodeAgent')")
    print(f"    Time:   {(t3-t2)*1000:.1f}ms")
    print(f"    Length: {len(shell_2)} chars")
    print(f"    Status: {'HIT (expected)' if (t3-t2) < (t1-t0) * 0.5 else 'MISS (unexpected)'}")
    print(f"    Same?:  {shell_1 == shell_2}")

    # 4. Warm Context
    t4 = time.monotonic()
    warm_1 = await build_warm_context("CodeAgent")
    t5 = time.monotonic()
    warm_2 = await build_warm_context("CodeAgent")
    t6 = time.monotonic()
    print(f"\n  [Warm 1] Time: {(t5-t4)*1000:.1f}ms, Length: {len(warm_1)} chars")
    print(f"  [Warm 2] Time: {(t6-t5)*1000:.1f}ms, Same: {warm_1 == warm_2}")

    # 5. 完整组装
    sys1, usr1 = await assemble_prompt(
        agent_name="CodeAgent",
        task_instruction="Write a function to sort a list",
        blackboard={"t1": "Research shows quicksort is O(n log n)"},
    )
    sys2, usr2 = await assemble_prompt(
        agent_name="CodeAgent",
        task_instruction="Write a function to reverse a string",
        blackboard={"t1": "Research shows string slicing is fastest"},
    )

    print(f"\n  [Assemble] System Prompt 1: {len(sys1)} chars")
    print(f"  [Assemble] System Prompt 2: {len(sys2)} chars")
    print(f"  [Assemble] System Prompts identical: {sys1 == sys2}")
    print(f"  [Assemble] User Message 1: {len(usr1)} chars")
    print(f"  [Assemble] User Message 2: {len(usr2)} chars")
    print(f"  [Assemble] User Messages identical: {usr1 == usr2}")

    if sys1 == sys2:
        print(f"\n  ✅ System Prompt 稳定 — DeepSeek KV Cache 可以命中前 {len(sys1)} chars")
    else:
        print(f"\n  ❌ System Prompt 不稳定 — KV Cache 无法命中")

    return sys1


async def test_llm_cache(system_prompt: str):
    """测试 DeepSeek KV Cache 命中。"""
    print("\n" + "=" * 70)
    print("  TEST 2: DeepSeek KV Cache (API-side)")
    print("=" * 70)

    try:
        from app.core.config import settings
        from openai import AsyncOpenAI

        if not settings.LLM_API_KEY or settings.LLM_API_KEY == "sk-test":
            print("\n  ⚠️ LLM_API_KEY not configured. Skipping LLM cache test.")
            print("  Set a real API key in .env to test DeepSeek KV Cache.")
            return

        client = AsyncOpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )
        model = settings.LLM_MODEL

        print(f"\n  Model: {model}")
        print(f"  Base URL: {settings.LLM_BASE_URL}")
        print(f"  System Prompt: {len(system_prompt)} chars")

        # 第一次调用 — 预期 cache miss（冷启动）
        print(f"\n  [LLM Call 1] Sending request (cold start)...")
        t0 = time.monotonic()
        resp1 = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Write a Python function to sort a list using quicksort."},
            ],
            max_tokens=200,
            temperature=0.3,
        )
        t1 = time.monotonic()

        usage1 = resp1.usage
        cache_hit_1 = getattr(usage1, "prompt_cache_hit_tokens", None)
        cache_miss_1 = getattr(usage1, "prompt_cache_miss_tokens", None)

        # 兼容不同 API 格式
        if cache_hit_1 is None:
            details = getattr(usage1, "prompt_tokens_details", None)
            if details:
                cache_hit_1 = getattr(details, "cached_tokens", 0)

        print(f"    Latency:     {(t1-t0)*1000:.0f}ms")
        print(f"    Prompt tokens: {usage1.prompt_tokens}")
        print(f"    Cache HIT:   {cache_hit_1 or 'N/A'}")
        print(f"    Cache MISS:  {cache_miss_1 or 'N/A'}")
        print(f"    Output:      {usage1.completion_tokens} tokens")

        # 第二次调用 — 相同 system_prompt，不同 user message
        print(f"\n  [LLM Call 2] Sending request (same system prompt, different question)...")
        t2 = time.monotonic()
        resp2 = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Write a Python function to reverse a string efficiently."},
            ],
            max_tokens=200,
            temperature=0.3,
        )
        t3 = time.monotonic()

        usage2 = resp2.usage
        cache_hit_2 = getattr(usage2, "prompt_cache_hit_tokens", None)
        cache_miss_2 = getattr(usage2, "prompt_cache_miss_tokens", None)

        if cache_hit_2 is None:
            details = getattr(usage2, "prompt_tokens_details", None)
            if details:
                cache_hit_2 = getattr(details, "cached_tokens", 0)

        print(f"    Latency:     {(t3-t2)*1000:.0f}ms")
        print(f"    Prompt tokens: {usage2.prompt_tokens}")
        print(f"    Cache HIT:   {cache_hit_2 or 'N/A'}")
        print(f"    Cache MISS:  {cache_miss_2 or 'N/A'}")
        print(f"    Output:      {usage2.completion_tokens} tokens")

        # 分析
        print(f"\n  ── Analysis ──")
        if cache_hit_2 and int(cache_hit_2) > 0:
            hit_rate = int(cache_hit_2) / usage2.prompt_tokens * 100
            print(f"  ✅ KV Cache HIT: {cache_hit_2}/{usage2.prompt_tokens} tokens ({hit_rate:.1f}%)")
            print(f"  💰 Cost savings: ~{hit_rate * 0.8 / 100:.0f}% on input tokens")

            # 计算实际节省
            full_cost = usage2.prompt_tokens * 0.14 / 1_000_000
            cached_cost = (int(cache_hit_2) * 0.028 + (usage2.prompt_tokens - int(cache_hit_2)) * 0.14) / 1_000_000
            print(f"  💰 Per-request: ${full_cost*1000:.4f} → ${cached_cost*1000:.4f} (per 1K requests)")
        elif cache_hit_2 == 0 or cache_hit_2 is None:
            print(f"  ⚠️ KV Cache MISS on second call.")
            print(f"  Possible reasons:")
            print(f"    - Provider doesn't support prefix caching (check model docs)")
            print(f"    - System prompt too short for caching (need >1024 tokens typically)")
            print(f"    - Requests routed to different GPU instances")
        else:
            print(f"  ℹ️ Cache hit data not available in API response.")
            print(f"  This provider may not expose cache metrics.")

        # 延迟对比
        latency_diff = ((t1-t0) - (t3-t2)) / (t1-t0) * 100
        print(f"\n  ⏱️ Latency: Call 1 = {(t1-t0)*1000:.0f}ms, Call 2 = {(t3-t2)*1000:.0f}ms")
        if latency_diff > 10:
            print(f"  ✅ Call 2 is {latency_diff:.0f}% faster (cache effect on TTFT)")
        else:
            print(f"  ℹ️ Latency difference: {latency_diff:.0f}% (may vary by network)")

    except ImportError:
        print("\n  ❌ openai package not installed. Run: pip install openai")
    except Exception as e:
        print(f"\n  ❌ LLM test failed: {e}")


async def main():
    print("\n🧪 Three-Layer Prompt Cache Test\n")

    # Test 1: Redis cache
    system_prompt = await test_redis_cache()

    # Test 2: DeepSeek KV Cache
    await test_llm_cache(system_prompt)

    print("\n" + "=" * 70)
    print("  Test complete.")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
