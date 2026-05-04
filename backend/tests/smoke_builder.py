"""
Smoke Test for Agent Builder Assistant.
Covers core nodes, graph logic, and sandbox evaluation.
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent))

from app.services.builder.graph import build_builder_graph
from app.services.builder.state import BuilderState
from app.services.builder.nodes.interview import interview_node
from app.services.builder.nodes.guardian import scope_guardian_node
from app.services.builder.harness_service import HarnessService
from langchain_core.messages import HumanMessage, AIMessage

async def test_node_interview():
    print("Testing [interview_node]...")
    state: BuilderState = {
        "messages": [HumanMessage(content="I want a support bot for my coffee shop.")],
        "confirmed_fields": {},
        "coverage_pct": 0,
        "missing_dimensions": ["core_role", "tools"]
    }
    result = await interview_node(state)
    print(f"   - Response: {result['messages'][0].content[:100]}...")
    print(f"   - Coverage: {result.get('coverage_pct', 0)}")
    assert len(result["messages"]) > 0
    print("Interview node passed.")

async def test_node_guardian():
    print("Testing [scope_guardian_node] (Anti-Sycophancy)...")
    state: BuilderState = {
        "messages": [
            HumanMessage(content="I want it to make coffee, fly a drone, and also write my emails."),
            AIMessage(content="I've added coffee making. Anything else?")
        ],
        "added_features_count": 2,
    }
    result = await scope_guardian_node(state)
    if "scope_warning" in result and result["scope_warning"]:
        print(f"   - Detected Bloat: {result['scope_warning']}")
    print("Scope Guardian node passed.")

async def test_harness_service():
    print("Testing [HarnessService] Evaluation...")
    harness = HarnessService()
    agent_config = {
        "name": "CoffeeBot",
        "system_prompt": "You are a coffee shop assistant.",
        "tools": []
    }
    test_cases = [
        {"question": "What's on the menu?", "expected_outcome": "List of coffee and pastries."}
    ]
    
    results = await harness.run_evaluation(agent_config, test_cases)
    print(f"   - Score: {results[0].score}")
    print(f"   - Verdict: {results[0].verdict}")
    assert results[0].score >= 0
    print("Harness Service passed.")

async def test_full_graph_e2e():
    print("Running E2E Graph Flow...")
    graph = build_builder_graph()
    
    # 1. Initial State
    state: BuilderState = {
        "session_id": "test_e2e",
        "user_id": "tester",
        "messages": [HumanMessage(content="Build me a technical documentation writer.")],
        "confirmed_fields": {},
        "coverage_pct": 0,
        "missing_dimensions": [],
        "discovered_context": {},
        "added_features_count": 0,
        "golden_dataset": [],
        "next_step": "continue"
    }
    
    # 2. Run first step (Discovery -> Interview)
    # We set recursion limit to 5 because without human input it will loop interview->guardian.
    try:
        final_state = await graph.ainvoke(state, config={"recursion_limit": 5})
        print(f"   - Next Step: {final_state.get('next_step')}")
    except Exception as e:
        if "Recursion limit" in str(e):
            print("   - Graph entered the expected interaction loop (awaiting human input).")
        else:
            raise e
    
    print("E2E Graph Flow basic check passed.")

async def main():
    print("=== Agent Builder Assistant Smoke Test ===")
    try:
        await test_node_interview()
        print("-" * 20)
        await test_node_guardian()
        print("-" * 20)
        await test_harness_service()
        print("-" * 20)
        await test_full_graph_e2e()
        print("\nALL SMOKE TESTS PASSED!")
    except Exception as e:
        print(f"\nSMOKE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
