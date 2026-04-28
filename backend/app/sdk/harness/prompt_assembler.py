"""
Three-Layer Prompt Assembler — KV Cache Optimized
==================================================
按变化频率将图谱数据分成三层，最大化 DeepSeek V4 的 prefix caching 命中率。

Layer 1 (Static Shell)  — System Prompt 前半段，TTL 24h，缓存命中率 ~99%
Layer 2 (Warm Context)  — System Prompt 后半段，TTL 1h，缓存命中率 ~90%
Layer 3 (Hot Context)   — User Message，每次不同，不期望缓存

组装结果:
  system_prompt = Layer 1 + Layer 2  ← DeepSeek KV Cache 缓存区
  user_message  = Layer 3            ← 每次变化，不影响前缀缓存

成本效果 (DeepSeek V4):
  缓存命中: $0.028/M (原价 $0.14/M，省 80%)
  预期命中率: 90-95%（同一 Agent 在 1h 内的多次调用）
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from loguru import logger

# ── Redis 缓存 Key 前缀 ──────────────────────────────────────────────────────
_SHELL_PREFIX = "harness:prompt:shell"   # Layer 1, TTL 24h
_WARM_PREFIX = "harness:prompt:warm"     # Layer 2, TTL 1h

_SHELL_TTL = 86400   # 24 hours
_WARM_TTL = 3600     # 1 hour


async def _get_redis():
    """获取异步 Redis 客户端，不可用时返回 None。"""
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings

        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        return client
    except Exception:
        return None


# ── Layer 1: Static Shell ─────────────────────────────────────────────────────

async def build_static_shell(agent_name: str) -> str:
    """
    构建 Layer 1 静态外壳。

    内容（几乎不变）:
      - Agent 角色定义
      - 全局 HarnessPolicy (feedforward, agent_scope='all')
      - 输出格式要求

    缓存: Redis TTL 24h
    """
    cache_key = f"{_SHELL_PREFIX}:{agent_name}"

    # 1. 查 Redis 缓存
    redis = await _get_redis()
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                await redis.aclose()
                logger.debug(f"[PromptAssembler] Shell HIT for {agent_name} ({len(cached)} chars)")
                return cached
        except Exception:
            pass

    logger.debug(f"[PromptAssembler] Shell MISS for {agent_name}, building from graph...")

    # 2. 从图谱查询全局 feedforward 规则
    global_rules = await _query_global_policies()

    # 3. 组装 Shell
    lines = [
        f"You are {agent_name}, a specialized HiveMind Agent.",
        "",
        _get_agent_role_description(agent_name),
        "",
    ]

    if global_rules:
        lines.append("### SYSTEM CONSTRAINTS (Global)")
        for rule in global_rules:
            severity = rule.get("severity", "warning")
            directive = rule.get("directive", "")
            prefix = "⛔ MUST" if severity == "error" else "⚠️ SHOULD"
            lines.append(f"- {prefix}: {directive}")
        lines.append("")

    lines.extend([
        "### OUTPUT RULES",
        "- Return well-structured, complete output.",
        "- Do NOT include TODO, FIXME, or placeholder code.",
        "- Do NOT use subprocess, eval(), exec(), or pty.",
        "- Use async I/O (asyncio/httpx), never time.sleep() or requests.get().",
        "",
    ])

    shell = "\n".join(lines)

    # 4. 写入 Redis 缓存
    if redis:
        try:
            await redis.set(cache_key, shell, ex=_SHELL_TTL)
            await redis.aclose()
        except Exception:
            pass

    return shell


# ── Layer 2: Warm Context ─────────────────────────────────────────────────────

async def build_warm_context(agent_name: str) -> str:
    """
    构建 Layer 2 温热上下文。

    内容（低频变化）:
      - Agent 绑定的 HarnessPolicy
      - 活跃的 CognitiveDirective 教训
      - 该 Agent 最近被拦截的原因摘要

    缓存: Redis TTL 1h
    """
    cache_key = f"{_WARM_PREFIX}:{agent_name}"

    # 1. 查 Redis 缓存
    redis = await _get_redis()
    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                await redis.aclose()
                logger.debug(f"[PromptAssembler] Warm HIT for {agent_name} ({len(cached)} chars)")
                return cached
        except Exception:
            pass

    logger.debug(f"[PromptAssembler] Warm MISS for {agent_name}, building from graph...")

    parts: list[str] = []

    # 2. Agent 绑定的 feedforward 规则
    agent_rules = await _query_agent_policies(agent_name)
    if agent_rules:
        parts.append(f"### CONSTRAINTS FOR {agent_name}")
        for rule in agent_rules:
            severity = rule.get("severity", "warning")
            directive = rule.get("directive", "")
            prefix = "⛔ MUST" if severity == "error" else "⚠️ SHOULD"
            parts.append(f"- {prefix}: {directive}")
        parts.append("")

    # 3. 活跃的 CognitiveDirective 教训
    directives = await _query_active_directives()
    if directives:
        parts.append("### LEARNED LESSONS (From Past Failures)")
        for d in directives:
            topic = d.get("topic", "")
            directive = d.get("directive", "")
            parts.append(f"- [{topic}] {directive}")
        parts.append("")

    # 4. 最近被拦截的原因
    recent_blocks = await _query_recent_blocks(agent_name)
    if recent_blocks:
        parts.append("### RECENT ISSUES (Avoid Repeating)")
        for b in recent_blocks:
            parts.append(f"- {b}")
        parts.append("")

    warm = "\n".join(parts)

    # 5. 写入 Redis 缓存
    if redis:
        try:
            await redis.set(cache_key, warm, ex=_WARM_TTL)
            await redis.aclose()
        except Exception:
            pass

    return warm


# ── Layer 3: Hot Context ──────────────────────────────────────────────────────

def build_hot_context(
    *,
    task_instruction: str,
    blackboard: dict[str, Any] | None = None,
    rag_context: str = "",
    extra_context: str = "",
) -> str:
    """
    构建 Layer 3 热上下文（每次不同，放在 User Message 中）。

    内容:
      - 当前 task instruction
      - Blackboard（其他 Agent 的输出）
      - RAG 检索结果
      - 额外上下文
    """
    parts = [f"### TASK\n{task_instruction}"]

    if blackboard:
        bb_lines = []
        for tid, output in blackboard.items():
            if tid.startswith("__"):
                continue  # 跳过内部字段
            snippet = str(output)[:500]
            bb_lines.append(f"--- {tid} ---\n{snippet}")
        if bb_lines:
            parts.append("### CONTEXT FROM OTHER AGENTS\n" + "\n".join(bb_lines))

    if rag_context:
        parts.append(f"### RETRIEVED KNOWLEDGE\n{rag_context}")

    if extra_context:
        parts.append(f"### ADDITIONAL CONTEXT\n{extra_context}")

    return "\n\n".join(parts)


# ── 完整组装入口 ──────────────────────────────────────────────────────────────

async def assemble_prompt(
    *,
    agent_name: str,
    task_instruction: str,
    blackboard: dict[str, Any] | None = None,
    rag_context: str = "",
    extra_context: str = "",
) -> tuple[str, str]:
    """
    组装三层 Prompt。

    Returns:
        (system_prompt, user_message)
        system_prompt = Layer 1 + Layer 2（缓存友好，放在 DeepSeek KV Cache 区）
        user_message  = Layer 3（每次不同）
    """
    # Layer 1: 静态外壳（Redis 24h）
    shell = await build_static_shell(agent_name)

    # Layer 2: 温热上下文（Redis 1h）
    warm = await build_warm_context(agent_name)

    # 拼成 System Prompt
    system_prompt = shell
    if warm.strip():
        system_prompt += "\n" + warm

    # Layer 3: 热上下文
    user_message = build_hot_context(
        task_instruction=task_instruction,
        blackboard=blackboard,
        rag_context=rag_context,
        extra_context=extra_context,
    )

    return system_prompt, user_message


# ── 缓存失效 ─────────────────────────────────────────────────────────────────

async def invalidate_prompt_cache(agent_name: str | None = None) -> int:
    """
    清除 Harness prompt 缓存。

    在以下场景调用:
      - Steering Loop 生成新规则后
      - Feature Flag 变更后
      - 手动触发

    Args:
        agent_name: 指定 Agent，None 则清除全部

    Returns:
        清除的 key 数量
    """
    redis = await _get_redis()
    if not redis:
        return 0

    try:
        if agent_name:
            keys = [
                f"{_SHELL_PREFIX}:{agent_name}",
                f"{_WARM_PREFIX}:{agent_name}",
            ]
        else:
            shell_keys = []
            warm_keys = []
            cursor = 0
            while True:
                cursor, batch = await redis.scan(cursor, match=f"{_SHELL_PREFIX}:*", count=100)
                shell_keys.extend(batch)
                if cursor == 0:
                    break
            cursor = 0
            while True:
                cursor, batch = await redis.scan(cursor, match=f"{_WARM_PREFIX}:*", count=100)
                warm_keys.extend(batch)
                if cursor == 0:
                    break
            keys = shell_keys + warm_keys

        if keys:
            await redis.delete(*keys)
            logger.info(f"[PromptAssembler] Invalidated {len(keys)} cache keys.")

        await redis.aclose()
        return len(keys)
    except Exception as e:
        logger.debug(f"[PromptAssembler] Cache invalidation failed: {e}")
        return 0


# ── 图谱查询辅助函数 ──────────────────────────────────────────────────────────

async def _query_global_policies() -> list[dict[str, Any]]:
    """查询全局 feedforward HarnessPolicy。"""
    try:
        from app.sdk.core.graph_store import get_graph_store

        store = get_graph_store()
        if not store.driver:
            return []

        return await store.execute_query(
            "MATCH (hp:HarnessPolicy {type: 'feedforward', is_active: true, agent_scope: 'all'}) "
            "RETURN hp.directive as directive, hp.severity as severity "
            "ORDER BY hp.severity DESC LIMIT 10"
        ) or []
    except Exception:
        return []


async def _query_agent_policies(agent_name: str) -> list[dict[str, Any]]:
    """查询 Agent 绑定的 feedforward HarnessPolicy。"""
    try:
        from app.sdk.core.graph_store import get_graph_store

        store = get_graph_store()
        if not store.driver:
            return []

        return await store.execute_query(
            "MATCH (hp:HarnessPolicy {type: 'feedforward', is_active: true}) "
            "WHERE hp.agent_scope = $agent "
            "RETURN hp.directive as directive, hp.severity as severity "
            "ORDER BY hp.severity DESC LIMIT 5",
            {"agent": agent_name},
        ) or []
    except Exception:
        return []


async def _query_active_directives() -> list[dict[str, Any]]:
    """查询活跃的 CognitiveDirective（通过图谱中的 SPAWNED 关系）。"""
    try:
        from app.sdk.core.graph_store import get_graph_store

        store = get_graph_store()
        if not store.driver:
            return []

        return await store.execute_query(
            "MATCH (cd:CognitiveDirectiveNode)-[:SPAWNED]->(hp:HarnessPolicy {is_active: true}) "
            "RETURN cd.topic as topic, hp.directive as directive "
            "ORDER BY hp.created_at DESC LIMIT 5"
        ) or []
    except Exception:
        return []


async def _query_recent_blocks(agent_name: str) -> list[str]:
    """查询该 Agent 最近 1h 被拦截的原因。"""
    try:
        from app.sdk.core.graph_store import get_graph_store

        store = get_graph_store()
        if not store.driver:
            return []

        results = await store.execute_query(
            "MATCH (hc:HarnessCheck {agent_name: $agent, passed: false}) "
            "WHERE hc.created_at > timestamp() - 3600000 "
            "RETURN hc.task_id as task_id, hc.error_count as errors "
            "ORDER BY hc.created_at DESC LIMIT 3",
            {"agent": agent_name},
        )

        return [
            f"Task {r.get('task_id', '?')} blocked ({r.get('errors', 0)} errors)"
            for r in (results or [])
        ]
    except Exception:
        return []


def _get_agent_role_description(agent_name: str) -> str:
    """返回 Agent 的角色描述（静态，不查图谱）。"""
    descriptions = {
        "CodeAgent": (
            "You are an expert in Python, TypeScript and Systems Architecture. "
            "You generate production-grade, clean, well-commented code."
        ),
        "ResearchAgent": (
            "You are an expert in retrieving, synthesizing and verifying knowledge. "
            "You provide evidence-backed research with proper citations."
        ),
        "HVM-Reviewer": (
            "You are a hyper-critical auditor specialized in code review, "
            "logic validation, and cross-viewpoint security analysis."
        ),
        "HVM-Supervisor": (
            "You are the HVM-Supervisor, an expert in Recursive Multi-Agent Coordination. "
            "You plan, delegate, and verify complex multi-step tasks."
        ),
    }
    return descriptions.get(agent_name, f"You are {agent_name}, a HiveMind specialized agent.")
