import pytest


@pytest.mark.asyncio
async def test_user_memory_isolation(mock_llm, clean_test_db):
    """
    Angles:
    1. User A runs swarm -> Memory populated
    2. User B runs swarm -> Check that User A's memory is NOT in historical context
    """
    # 1. User A: Populate memory
    # We can manually seed or run a dummy swarm
    from app.services.agents.memory_bridge import SwarmMemoryBridge
    bridge_a = SwarmMemoryBridge(user_id="USER-A")
    await bridge_a.persist_successful_outcome(
        query="Secret Project X details",
        context={"T1": "Project X is in Area 51."}
    )

    # 2. User B: Run swarm and check recall
    bridge_b = SwarmMemoryBridge(user_id="USER-B")

    # MOCK MemoryService.get_context to return something for USER-A but not USER-B?
    # Actually, MemoryService(user_id="USER-B") should handle isolation.
    # Let's verify the bridge calls
    context_b = await bridge_b.load_historical_context("Area 51")

    assert "Project X" not in context_b
    print("\n✅ Security: User-based memory isolation verified.")
