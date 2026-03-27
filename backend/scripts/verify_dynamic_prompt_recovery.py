import asyncio
import sys
import os
import time
import io
import json
from pathlib import Path
from loguru import logger

# Configure standard streams for UTF-8 (Fix for Windows console)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend to path and load .env from project root or backend/
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from dotenv import load_dotenv
load_dotenv(backend_root / ".env")

# Force set ZhipuAI key for SDK
if os.getenv("EMBEDDING_API_KEY"):
    os.environ["ZHIPUAI_API_KEY"] = os.getenv("EMBEDDING_API_KEY")

from app.agents.swarm import SwarmOrchestrator, AgentDefinition
from langchain_core.messages import HumanMessage

async def verify_dynamic_recovery():
    print("🎯 Verification: Dynamic Prompt Recovery Loop")
    print("=============================================")
    
    orchestrator = SwarmOrchestrator()
    
    # 🧩 Register RAG Agent (Production-like setup)
    orchestrator.register_agent(
        AgentDefinition(
            name="rag_agent",
            description="Specialist for processing provided documents. Route here if the 'Context Information (RAG)' block already contains documents or data needed to answer.",
            model_hint="balanced",
        )
    )
    # Ensure graph is built with the new agent
    await orchestrator.build_graph()
    
    # 🧪 SCENARIO: Massive single-block document with a buried key.
    # We deliberately use a huge block to confuse the initial 'default' mode.
    distractor = "This is a recurring technical document about solar panel efficiency in variable cloud cover. " * 50
    distractor_block = "\n\n".join([distractor for _ in range(25)]) # ~20,000 characters
    
    # Buried key in the middle
    secret_key = "DYNAMIC-RECOVERY-KEY-42"
    mid_point = len(distractor_block) // 2
    context_data = distractor_block[:mid_point] + f" [NOTE: The recovery master key is '{secret_key}'. Access restricted to level 5.] " + distractor_block[mid_point:]
    
    query = "Find the specific system recovery master key in the documents and tell me what it is. I need the exact string."
    conv_id = f"test_{int(time.time())}"
    
    # We call invoke_stream to see the intermediate nodes and state changes
    print(f"🚀 Sending query: '{query}' with {len(context_data)} characters of context...")
    
    start_time = time.time()
    
    # Use context dictionary to pass the knowledge to the orchestrator
    test_context = {
        "context_data": context_data,
        "language": "zh-CN",
        "prompt_variant": "default", 
        "conversation_id": conv_id,
    }
    
    found_recovery = False
    reflections = 0
    final_output = ""
    
    # Wrap in a way we can see the node transitions
    async for output in orchestrator.invoke_stream(query, context=test_context, conversation_id=conv_id):
        for node_name, state_delta in output.items():
            print(f"📍 Visiting Node: {node_name}")
            
            if "thought_log" in state_delta and state_delta["thought_log"]:
                print(f"   💭 Thought: {state_delta['thought_log']}")
                
            if "prompt_variant" in state_delta:
                print(f"   🔄 Prompt Variant Update: {state_delta['prompt_variant']}")
                if state_delta['prompt_variant'] == "head_tail_v1":
                    found_recovery = True
            
            if "reflection_count" in state_delta:
                reflections = state_delta["reflection_count"]
                print(f"   🪞 Reflection count: {reflections}")
            
            if "agent_outputs" in state_delta:
                for agent_name, out in state_delta["agent_outputs"].items():
                    print(f"   🤖 Agent '{agent_name}' Response: {out[:100]}...")
                    final_output = out

    duration = time.time() - start_time
    print("\n" + "="*50)
    print("🏁 VERIFICATION RESULT")
    print(f"Total Reflections: {reflections}")
    print(f"Recovery Triggered: {'✅ YES' if found_recovery else '❌ NO'}")
    print(f"Key Found: {'✅ YES' if secret_key in final_output else '❌ NO'}")
    print(f"Total Time: {duration:.2f}s")
    print("="*50)
    
    if found_recovery and secret_key in final_output:
        print("🎉 SUCCESS: The Dynamic Feedback Loop successfully detected a failure and recovered using High-recall prompting!")
    else:
        print("⚠️ FAILURE: The dynamic recovery didn't work as expected.")

if __name__ == "__main__":
    asyncio.run(verify_dynamic_recovery())
