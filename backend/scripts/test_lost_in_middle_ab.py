import asyncio
import sys
import os
import time
import io
from pathlib import Path

# Configure standard streams for UTF-8 (Fix for Windows console)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.swarm import SwarmOrchestrator, AgentDefinition
from langchain_core.messages import HumanMessage

async def test_lost_in_middle():
    print("🧪 Testing 'Lost in the Middle' Optimization (A/B Test)")
    print("==========================================================")

    orchestrator = SwarmOrchestrator()
    
    # 1. Register a ResearchAgent (Mock)
    research_agent = AgentDefinition(
        name="ResearchAgent",
        description="Handles knowledge retrieval",
        model_hint="balanced"
    )
    orchestrator.register_agent(research_agent)
    await orchestrator.build_graph()

    # 2. Prepare Synthetic Context
    # We want a context that is long enough to trigger 'Lost in the Middle'
    # and has a critical fact buried in the middle.
    
    distractors = [
        f"Fragment {i}: This is irrelevant information about the history of cheese making in the 14th century. It discusses various textures and aging processes."
        for i in range(1, 21)
    ]
    
    critical_fact = "Fragment 11 (CRITICAL): The secret code for the vault is 'ALPHA-99-BETA'. This is the only way to open the vault."
    
    # Inject the fact in the middle
    distractors[10] = critical_fact
    
    rag_context = "\n\n".join(distractors)
    query = "What is the secret code for the vault?"

    # 3. Test Function
    async def run_test(variant: str):
        print(f"\n🚀 Running variant: '{variant}'")
        
        # We manually construct the state to bypass the full graph retrieval for this test
        # and directly test the agent node with provided context.
        state = {
            "messages": [HumanMessage(content=query)],
            "original_query": query,
            "current_task": f"Answer the user's question based on the retrieved knowledge: {query}",
            "context_data": rag_context,
            "prompt_variant": variant,
            "language": "zh-CN",
            "agent_outputs": {},
            "reflection_count": 0,
            "uncertainty_level": 0.0,
            "conversation_id": "test_ab_lost",
            "kb_ids": [],
            "retrieval_trace": [],
            "retrieved_docs": []
        }
        
        # We call the agent node directly
        agent_node = orchestrator._create_agent_node(research_agent)
        
        start = time.time()
        result = await agent_node(state)
        duration = time.time() - start
        
        output = result.get("agent_outputs", {}).get("ResearchAgent", "ERROR: No Output")
        
        print(f"Time: {duration:.2f}s")
        print(f"Response Snippet: {output[:100]}...")
        
        success = "ALPHA-99-BETA" in output
        print(f"Result: {'✅ FOUND CODE' if success else '❌ MISSED CODE'}")
        
        return success, output

    # 4. Compare
    results = {}
    
    # Run DEFAULT
    success_def, out_def = await run_test("default")
    results["default"] = {"success": success_def, "output": out_def}
    
    # Run HEAD_TAIL_V1
    success_opt, out_opt = await run_test("head_tail_v1")
    results["head_tail_v1"] = {"success": success_opt, "output": out_opt}

    # 5. Summary
    print("\n" + "="*50)
    print("📊 A/B TEST SUMMARY")
    print(f"Default Variant:    {'PASS' if success_def else 'FAIL'}")
    print(f"Head/Tail Variant:  {'PASS' if success_opt else 'FAIL'}")
    print("="*50)

if __name__ == "__main__":
    # Ensure environment variables are loaded
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(test_lost_in_middle())
