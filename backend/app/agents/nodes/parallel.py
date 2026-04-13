"""
[RULE-B001]: Swarm Parallel and Consensus Nodes.
Extracted from swarm.py.
"""

import asyncio
from loguru import logger
from langchain_core.messages import AIMessage, SystemMessage
from app.agents.schemas import SwarmState, ModelTier

async def parallel_node(orchestrator, state: SwarmState) -> dict:
    """
    [M4.2.5] 并行协作节点。
    """
    agents_to_invoke = state.get("parallel_agents", [])
    if not agents_to_invoke:
        return {"next_step": "FINISH", "status_update": "⚠️ 并行节点未分配任务"}

    logger.info(f"⚡ [M4.2.5] Parallel execution triggered for: {agents_to_invoke}")

    tasks = []
    for agent_name in agents_to_invoke:
        agent_def = orchestrator._agents.get(agent_name)
        if agent_def:
            node_func = orchestrator._create_agent_node(agent_def)
            tasks.append(node_func(state))
        else:
            logger.warning(f"Unknown agent in parallel list: {agent_name}")

    if not tasks:
        return {"next_step": "supervisor"}

    results = await asyncio.gather(*tasks, return_exceptions=True)

    merged_outputs = state.get("agent_outputs", {}).copy()
    merged_msgs = []

    for i, res in enumerate(results):
        agent_name = agents_to_invoke[i]
        if isinstance(res, Exception):
            logger.error(f"❌ Parallel Agent {agent_name} failed: {res}")
            merged_outputs[agent_name] = f"Error: {res}"
        else:
            merged_outputs.update(res.get("agent_outputs", {}))
            merged_msgs.extend(res.get("messages", []))

    next_step = "consensus" if len(agents_to_invoke) > 1 else "reflection_decision"

    return {
        "agent_outputs": merged_outputs,
        "messages": merged_msgs,
        "next_step": next_step,
        "status_update": f"⚡ 并行协作完成：{', '.join(agents_to_invoke)}",
        "thought_log": f"⚡ 并行执行器聚合了 {len(agents_to_invoke)} 个智体的响应",
    }

async def consensus_node(orchestrator, state: SwarmState) -> dict:
    """
    [M4.2.5] 共识合成节点。
    """
    agent_outputs = state.get("agent_outputs", {})
    original_query = state.get("original_query", "")
    task = state.get("current_task", "")

    debate_buffer = []
    for name, output in agent_outputs.items():
        if name in state.get("parallel_agents", []):
            debate_buffer.append(f"【{name} 的观点】:\n{output}")

    debate_text = "\n\n".join(debate_buffer)

    system_prompt = f"""
    You are the Swarm Consensus Synthesizer.
    Original User Query: {original_query}
    Current Sub-task: {task}
    
    --- AGENT DEBATE ---
    {debate_text}
    --- END DEBATE ---
    
    Final Synthesized Answer (Markdown):
    """

    llm = orchestrator.router.get_model(ModelTier.REASONING)
    response = await llm.ainvoke([SystemMessage(content=system_prompt)])

    return {
        "messages": [AIMessage(content=response.content)],
        "agent_outputs": {"consensus": str(response.content)},
        "next_step": "reflection_decision",
        "status_update": "⚖️ 多智体共识合成完成",
        "thought_log": "⚖️ 已综合多个智体的独立见解，解决潜在冲突并形成最终一致性结论",
    }
