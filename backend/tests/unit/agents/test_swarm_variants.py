import asyncio
from unittest.mock import AsyncMock, MagicMock

from app.agents.swarm import AgentDefinition, SwarmOrchestrator, SwarmState


def test_invoke_passes_variants_into_initial_state():
    orchestrator = SwarmOrchestrator()

    fake_graph = AsyncMock()
    fake_graph.ainvoke = AsyncMock(return_value={"messages": []})
    orchestrator._graph = fake_graph

    asyncio.run(
        orchestrator.invoke(
            "hello",
            context={
                "knowledge_base_ids": ["kb_1"],
                "prompt_variant": "head_tail_v1",
                "retrieval_variant": "ab_no_graph",
            },
            conversation_id="conv_test",
        )
    )

    called_state = fake_graph.ainvoke.call_args.args[0]
    assert called_state["prompt_variant"] == "head_tail_v1"
    assert called_state["retrieval_variant"] == "ab_no_graph"


def test_agent_node_forwards_prompt_variant_to_prompt_engine():
    orchestrator = SwarmOrchestrator()

    agent_def = AgentDefinition(name="supervisor", description="test supervisor agent", tools=[])
    orchestrator.register_agent(agent_def)
    node = orchestrator._create_agent_node(agent_def)

    orchestrator.prompt_engine.build_agent_prompt = MagicMock(return_value="system prompt")

    mock_llm = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.tool_calls = []
    mock_resp.content = "ok"
    mock_llm.ainvoke = AsyncMock(return_value=mock_resp)

    orchestrator._get_llm_for_agent = MagicMock(return_value=mock_llm)

    state: SwarmState = {
        "messages": [],
        "next_step": "rag",
        "agent_outputs": {},
        "uncertainty_level": 0.0,
        "current_task": "task",
        "conversation_id": "",
        "reflection_count": 0,
        "original_query": "q",
        "context_data": "ctx",
        "kb_ids": [],
        "prompt_variant": "head_tail_v1",
        "retrieval_variant": "default",
        "last_node_id": "",
        "retrieval_trace": [],
        "retrieved_docs": [],
        "status_update": None,
        "thought_log": None,
        "user_id": None,
    }

    asyncio.run(node(state))

    kwargs = orchestrator.prompt_engine.build_agent_prompt.call_args.kwargs
    assert kwargs["prompt_variant"] == "head_tail_v1"
