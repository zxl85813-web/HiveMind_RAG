"""
[RULE-B001]: Swarm Supervisor Node.
Extracted from swarm.py.
"""

import asyncio
import json
from loguru import logger
from langchain_core.messages import SystemMessage
from app.agents.schemas import SwarmState, ModelTier
from app.services.cache_service import CacheService
from app.core.algorithms.routing import vector_agent_router
from app.services.swarm_observability import record_swarm_span
from app.models.observability import TraceStatus

async def supervisor_node(orchestrator, state: SwarmState) -> dict:
    """
    The Supervisor Node: The "Brain" of the swarm.
    Routes to the correct expert agent based on user query.
    """
    messages = state["messages"]
    user_query = str(state.get("original_query", "") or (messages[-1].content if messages else ""))

    # === Fast Path: JIT Route Cache (GOV-004) ===
    cached_route = await CacheService.get_cached_route(user_query)
    if cached_route:
        logger.info(f"⚡ [JIT Route Cache] Hit: {user_query[:30]} -> {cached_route}")
        return {
            "next_step": cached_route,
            "uncertainty_level": 0.0,
            "current_task": "Restored from route cache.",
            "last_node_id": "supervisor_cache",
            "thought_log": f"⚡ JIT 缓存命中: 直接跳转到 {cached_route}",
        }

    # === Fast Path: Keyword-based Platform Action Detection ===
    PLATFORM_INTENTS = [
        (
            ["创建知识库", "新建知识库", "create knowledge base", "create kb"],
            "open_modal:create_kb",
            '好的，现在为您打开**创建知识库**向导。\n[ACTION: {"type": "open_modal", "target": "create_kb", "label": "立刻创建", "variant": "primary"}]',
        ),
        (
            ["上传文档", "上传文件", "upload document", "upload file"],
            "navigate:/knowledge",
            '我来帮您跳转到**知识库管理**页面，在那里您可以上传文档。\n[ACTION: {"type": "navigate", "target": "/knowledge", "label": "去上传文档", "variant": "primary"}]',
        ),
        (
            ["去评测", "运行评测", "run evaluation", "跳转到评测"],
            "navigate:/evaluation",
            '好的，现在为您跳转到**评测中心**。\n[ACTION: {"type": "navigate", "target": "/evaluation", "label": "前往评测中心", "variant": "primary"}]',
        ),
    ]

    for keywords, action, reply_template in PLATFORM_INTENTS:
        if any(kw.lower() in user_query.lower() for kw in keywords):
            logger.info(f"[Supervisor Fast Path] Detected platform intent: {action}")
            return {
                "next_step": "PLATFORM_ACTION",
                "uncertainty_level": 0.0,
                "current_task": action,
                "context_data": reply_template,
                "last_node_id": "supervisor_fast",
                "thought_log": f"⚡ 快速匹配: 检测到平台操作指令 '{keywords[0]}'",
            }

    # === Mid Path: Vector-based Agent Routing ===
    vector_route = await vector_agent_router.route(user_query)
    if vector_route and vector_route in orchestrator._agents:
        logger.info(f"⚡ [Vector Router] Matched → '{vector_route}'")
        return {
            "next_step": vector_route,
            "uncertainty_level": 0.25,
            "current_task": f"向量路由 → {vector_route}",
            "last_node_id": "supervisor_vector",
            "thought_log": f"⚡ 向量路由命中: 直接分配给 {vector_route}",
        }

    # === Regular Path: Use LLM for routing ===
    agents_info = [{"name": name, "description": a.description} for name, a in orchestrator._agents.items()]
    agents_info.append({"name": "retrieval", "description": "Knowledge Retrieval System."})

    system_prompt = orchestrator.prompt_engine.build_supervisor_prompt(
        agents=agents_info,
        rag_context=state.get("context_data", ""),
        memory_context="",
        language=state.get("language", "zh-CN"),
    )

    tier = ModelTier.REASONING if state.get("force_reasoning_tier") else ModelTier.SIMPLE
    llm = orchestrator.router.get_model(tier)
    final_prompt = [SystemMessage(content=system_prompt), *messages]

    response = await llm.ainvoke(final_prompt)
    decision = orchestrator._parse_routing_decision(response.content)

    result = {
        "next_step": decision.next_agent,
        "uncertainty_level": decision.uncertainty,
        "current_task": decision.reasoning,
        "thought_log": f"👨‍✈️ 决策路径: {decision.reasoning}",
        "parallel_agents": decision.parallel_agents,
    }
    
    # --- 🔒 RECORD TRACE SPAN ---
    trace_id = state.get("swarm_trace_id")
    if trace_id:
        import asyncio
        asyncio.create_task(record_swarm_span(
            trace_id=trace_id,
            agent_name="supervisor",
            instruction=user_query,
            output=f"Routing to {decision.next_agent}",
            latency_ms=0.0, # TODO
            status=TraceStatus.SUCCESS,
            details={
                "decision": decision.model_dump(),
                "uncertainty": decision.uncertainty
            }
        ))

    return result
