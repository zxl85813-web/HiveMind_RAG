import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.agents.swarm import SwarmOrchestrator, AgentDefinition, SwarmState
from langchain_core.messages import HumanMessage, AIMessage

@pytest.fixture
def mock_swarm_orchestrator():
    orchestrator = SwarmOrchestrator()
    orchestrator._default_llm = MagicMock()
    # Mock prompt engine
    mock_prompt_engine = MagicMock()
    mock_prompt_engine.get_model_hint.return_value = "balanced"
    orchestrator._prompt_engine = mock_prompt_engine
    return orchestrator

def test_register_agent(mock_swarm_orchestrator):
    agent = AgentDefinition(name="test_agent", description="A test agent")
    mock_swarm_orchestrator.register_agent(agent)
    
    assert "test_agent" in mock_swarm_orchestrator._agents
    assert mock_swarm_orchestrator._agents["test_agent"].name == "test_agent"
    
def test_unregister_agent(mock_swarm_orchestrator):
    agent = AgentDefinition(name="test_agent", description="A test agent")
    mock_swarm_orchestrator.register_agent(agent)
    mock_swarm_orchestrator.unregister_agent("test_agent")
    
    assert "test_agent" not in mock_swarm_orchestrator._agents

@pytest.mark.asyncio
async def test_build_graph(mock_swarm_orchestrator):
    agent = AgentDefinition(name="test_agent", description="A test agent")
    mock_swarm_orchestrator.register_agent(agent)
    
    await mock_swarm_orchestrator.build_graph()
    
    assert mock_swarm_orchestrator._graph is not None

@pytest.mark.asyncio
async def test_supervisor_node(mock_swarm_orchestrator):
    mock_llm_response = MagicMock()
    mock_llm_response.content = '{"next_agent": "test_agent", "uncertainty": 0.1, "reasoning": "sure", "task_refinement": "refined task"}'
    
    mock_swarm_orchestrator._default_llm.ainvoke = AsyncMock(return_value=mock_llm_response)
    mock_swarm_orchestrator.prompt_engine.build_supervisor_prompt.return_value = "System Prompt"
    
    agent = AgentDefinition(name="test_agent", description="A test agent")
    mock_swarm_orchestrator.register_agent(agent)
    
    state = SwarmState(
        messages=[HumanMessage(content="Hello")],
        next_step="",
        agent_outputs={},
        uncertainty_level=0.0,
        current_task="",
        reflection_count=0,
        original_query="Hello"
    )
    
    result_state = await mock_swarm_orchestrator._supervisor_node(state)
    
    assert result_state["next_step"] == "test_agent"
    assert result_state["uncertainty_level"] == 0.1
    assert result_state["current_task"] == "refined task"
