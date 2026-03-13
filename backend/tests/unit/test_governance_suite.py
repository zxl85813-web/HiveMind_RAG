from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.swarm import SwarmOrchestrator, SwarmState
from app.core.algorithms.alignment import AlignmentDecision, TruthAlignmentService
from app.core.algorithms.memory_governance import (
    ValueDensityScore,
    memory_governance_service,
)
from app.services.cache_service import CacheService


@pytest.mark.asyncio
async def test_truth_alignment_detection(mock_llm_service):
    # Mock a contradiction
    graph_facts = "The capital of France is Paris."
    vector_content = "According to recent reports, the capital of France has been moved to Lyon."

    # Configure mock for instructor call (ConsistencyCheck)
    mock_res = MagicMock()
    mock_res.has_contradiction = True
    mock_res.conflicts = ["Capital of France mismatch: Paris vs Lyon"]
    mock_res.reinforcements = []
    mock_res.analysis = "Contradiction found."
    mock_llm_service.client.chat.completions.create.return_value = mock_res

    svc = TruthAlignmentService()
    report = await svc.align(graph_facts, vector_content)

    assert report is not None
    assert report.is_consistent is False
    assert len(report.conflicts) > 0

@pytest.mark.asyncio
async def test_memory_governance_density(mock_llm_service):
    # Mock for high value
    mock_llm_service.client.chat.completions.create.return_value = ValueDensityScore(
        score=0.85, 
        tier_recommendation="GRAPH", 
        reasoning="High architectural value.", 
        keywords=["Neo4j"]
    )

    high_val = "In project X, we decided to use Neo4j for the graph layer to support multi-hop reasoning."
    high_score = await memory_governance_service.evaluate_density(high_val)
    assert high_score.score > 0.6
    assert high_score.tier_recommendation == "GRAPH"

    # Mock for low value - just set return_value again or use side_effect correctly
    mock_llm_service.client.chat.completions.create.return_value = ValueDensityScore(
        score=0.1, 
        tier_recommendation="VECTOR", 
        reasoning="Noise.", 
        keywords=[]
    )

    low_val = "Hi there, how are you? Just checking in."
    low_score = await memory_governance_service.evaluate_density(low_val)
    assert low_score.score < 0.4
    assert low_score.tier_recommendation == "VECTOR"


@pytest.mark.asyncio
async def test_jit_route_cache():
    query = "How do I create a knowledge base?"
    target = "open_modal:create_kb"

    await CacheService.set_cached_route(query, target)

    # Test direct hit
    hit = await CacheService.get_cached_route(query)
    assert hit == target

    # Test semantic hit
    semantic_query = "Help me make a new KB"
    semantic_hit = await CacheService.get_cached_route(semantic_query)
    assert semantic_hit == target

@pytest.mark.asyncio
async def test_routing_watchdog_escalation():
    # Mocking SwarmOrchestrator reflection node logic
    orchestrator = SwarmOrchestrator()

    # Create a state with a conflict warning
    state: SwarmState = {
        "messages": [AsyncMock(content="Paris is Lyon.")], # Contradictory response
        "context_data": "⚠️ CONFLICT: Fact mismatch detected.",
        "original_query": "What is the capital of France?",
        "force_reasoning_tier": False,
        "reflection_count": 0,
        "next_step": "",
        "user_id": "test_user",
        "auth_context": None,
        "retrieval_trace": [],
        "retrieved_docs": []
    }

    # We need to mock MultiGraderEval to return a low consistency score
    with patch("app.services.evaluation.multi_grader.MultiGraderEval.evaluate") as mock_eval:
        mock_eval.return_value = AsyncMock(
            verdict="REVISE",
            composite_score=0.3,
            opinions=[AsyncMock(aspect="consistency", score=0.2)]
        )

        result = await orchestrator._reflection_node(state)
        assert result["force_reasoning_tier"] is True
        assert result["next_step"] == "supervisor"
