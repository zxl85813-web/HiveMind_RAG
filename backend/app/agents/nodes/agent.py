"""
[RULE-B001]: Swarm Agent Node.
Extracted from swarm.py.
"""

import asyncio
import time as _time
import uuid
from loguru import logger
from langchain_core.messages import AIMessage
from app.agents.schemas import SwarmState, AgentDefinition
from app.core.token_service import TokenService
from app.core.config import settings
from app.agents.agentic_search import SEARCH_TOOLS
from app.agents.tools import NATIVE_TOOLS
from app.services.swarm_observability import record_swarm_span
from app.models.observability import TraceStatus

def create_agent_node(orchestrator, agent_def: AgentDefinition):
    """Factory for agent execution nodes with tool calling capability."""

    async def agent_node(state: SwarmState) -> dict:
        # --- Scoped State Filtering (M5.1.1) ---
        from app.agents.swarm import ScopedStateView
        scoped_state = ScopedStateView.filter(state, agent_def.name)

        task = scoped_state.get("current_task", "")
        conv_id = scoped_state.get("conversation_id", "")
        logger.info(f"🤖 Agent [{agent_def.name}] working on: {task[:80]}")

        # --- Phase 5: Task Progress Tracking (Persistent) ---
        from app.models.agents import TodoStatus

        if conv_id:
            todos = await orchestrator.memory.get_todos(status=TodoStatus.PENDING)
            for todo in todos:
                if todo.source_conversation_id == conv_id and todo.assigned_to == agent_def.name:
                    await orchestrator.memory.update_todo(todo.id, status=TodoStatus.IN_PROGRESS)
                    logger.debug(f"📉 Task '{todo.title}' marked as IN_PROGRESS")

        # 1. Prepare Tools
        available_tools = list(agent_def.tools)
        if agent_def.name != "supervisor":
            # 1.1 Add mandatory native tools
            mandatory_tools = [t for t in NATIVE_TOOLS if getattr(t, "_hive_meta", None) and t._hive_meta.always_load]
            available_tools.extend(mandatory_tools)

            if task:
                logger.debug(f"🔍 [Tool Discovery] Filtering specialized tools for task: {task[:50]}...")
                await orchestrator.tool_index.initialize_embeddings()
                available_tools.extend(await orchestrator.tool_index.asearch(task, limit=5))

                mcp_tools = await orchestrator.mcp.discover_tools(task, limit=10)
                available_tools.extend(mcp_tools)

                discovered_skills = orchestrator.skills.discover(task, limit=5)
                for skill in discovered_skills:
                    available_tools.extend(skill.tools)

                if any(kw in task.lower() for kw in ["search", "find", "who", "what", "how", "搜索", "查找"]):
                    available_tools.extend(SEARCH_TOOLS)
            else:
                available_tools.extend(SEARCH_TOOLS[:2])

        # 2. Prepare Memory Context
        memory_context = ""
        user_id = state.get("user_id")
        if user_id:
            from app.services.memory.memory_service import MemoryService
            mem_svc = MemoryService(user_id=user_id)
            role_id = state["auth_context"].role if state.get("auth_context") else None
            memory_context = await mem_svc.get_context(query=task, role_id=role_id)

        rag_context = state.get("context_data", "")
        prompt_variant = state.get("prompt_variant", "default")

        # --- Token Governance ---
        rag_budget = int(settings.CONTEXT_WINDOW_LIMIT * settings.BUDGET_RAG_RATIO)
        mem_budget = int(settings.CONTEXT_WINDOW_LIMIT * settings.BUDGET_MEMORY_RATIO)

        rag_context = TokenService.truncate_to_budget(rag_context, rag_budget)
        memory_context = TokenService.truncate_to_budget(memory_context, mem_budget)

        system_prompt = orchestrator.prompt_engine.build_agent_prompt(
            agent_name=agent_def.name,
            task=task,
            rag_context=rag_context,
            memory_context=memory_context,
            tools_available=[t.name for t in available_tools if hasattr(t, "name")],
            prompt_variant=prompt_variant,
            language=state.get("language", "zh-CN"),
        )

        # 3. Get LLM
        llm = orchestrator._get_llm_for_agent(agent_def)
        if available_tools:
            llm = llm.bind_tools(available_tools)

        # --- Context Compaction ---
        state["messages"] = await orchestrator._compact_messages(
            state["messages"],
            user_id=state.get("user_id"),
            conversation_id=state.get("conversation_id"),
            pinned_messages=state.get("pinned_messages")
        )

        # 4. Invoke Engine
        execution_variant = state.get("execution_variant", "monolithic")
        updates = await orchestrator.engine.stream_and_broadcast(
            conversation_id=conv_id,
            user_id=user_id or "",
            agent_def=agent_def,
            llm=llm,
            available_tools=available_tools,
            system_prompt=system_prompt,
            state=scoped_state,
        )

        session_thinking_times = updates.get("thinking_time_ms", [])
        session_tool_times = updates.get("tool_time_ms", [])
        new_messages = updates.get("messages", [])
        final_content = updates.get("agent_outputs", {}).get(agent_def.name, "")

        # --- Output Sanitization ---
        from app.services.security.sanitizer import SecuritySanitizer
        final_content = SecuritySanitizer.mask_text(str(final_content))

        node_id = f"{agent_def.name}_{uuid.uuid4().hex[:6]}"

        if conv_id:
            todos = await orchestrator.memory.get_todos(status=TodoStatus.IN_PROGRESS)
            for todo in todos:
                if todo.source_conversation_id == conv_id and todo.assigned_to == agent_def.name:
                    await orchestrator.memory.update_todo(todo.id, status=TodoStatus.COMPLETED)
                    logger.info(f"✅ Task '{todo.title}' marked as COMPLETED by {agent_def.name}")

        # --- 🔒 RECORD TRACE SPAN ---
        trace_id = state.get("swarm_trace_id")
        if trace_id:
            logger.debug(f"🛰️ Recording SwarmSpan for {agent_def.name} on trace {trace_id}")
            # Add retrieval trace if this agent performed retrieval (or just related memories)
            asyncio.create_task(record_swarm_span(
                trace_id=trace_id,
                agent_name=agent_def.name,
                instruction=task,
                output=str(final_content),
                latency_ms=sum(session_thinking_times) + sum(session_tool_times),
                status=TraceStatus.SUCCESS,
                details={
                    "thinking_time_ms": session_thinking_times,
                    "tool_time_ms": session_tool_times,
                    "num_tool_calls": len(session_tool_times),
                    "execution_variant": execution_variant
                }
            ))

        return {
            "messages": new_messages,
            "agent_outputs": {agent_def.name: str(final_content)},
            "last_node_id": node_id,
            "thinking_time_ms": session_thinking_times,
            "tool_time_ms": session_tool_times,
            "status_update": f"✅ {agent_def.name} finished.",
        }

    return agent_node
