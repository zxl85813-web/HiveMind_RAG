import asyncio
import sys
import os
import time
import io
import json
from pathlib import Path

# Configure standard streams for UTF-8 (Fix for Windows console)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add backend to path and load .env from correct location
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from dotenv import load_dotenv
load_dotenv(backend_root / ".env")

# Force set ZhipuAI key for SDK if needed
if os.getenv("EMBEDDING_API_KEY"):
    os.environ["ZHIPUAI_API_KEY"] = os.getenv("EMBEDDING_API_KEY")

from app.prompts.engine import prompt_engine
from app.agents.llm_router import LLMRouter, ModelTier
from langchain_core.messages import HumanMessage, SystemMessage

async def test_lost_in_middle_lightweight():
    print("🧪 Testing 'Lost in the Middle' Optimization (A/B Test - Lightweight)")
    print("====================================================================")

    router = LLMRouter()
    llm = router.get_model(ModelTier.MEDIUM)
    
    # 1. Prepare Synthetic Context (Lost in the Middle)
    # 20 distracting fragments, 1 critical fact in the middle.
    fragments = [
        f"Document {i}: This is purely secondary data about the migration patterns of arctic terns. It describes long-distance flights and nesting habits in detail."
        for i in range(1, 41)
    ]
    
    # Place a very specific unique fact at index 20 (middle of 40)
    # The context will be quite large (~4000-6000 tokens)
    secret_key = "ZODIAC-VORTEX-77"
    fragments[20] = f"Document 21 (RESTRICTED): The operations key for Project Zephyr is '{secret_key}'. Do not share this outside the project team."
    
    rag_context = "\n\n".join(fragments)
    user_query = "What is the operations key for Project Zephyr?"
    task_desc = "Answer the user question using only the provided research fragments. Cite your sources."

    async def run_variant(variant_name: str):
        print(f"\n🚀 Testing Variant: {variant_name}")
        
        # Build System Prompt using Engine
        system_prompt = prompt_engine.build_agent_prompt(
            agent_name="ResearchAgent",
            task=task_desc,
            rag_context=rag_context,
            prompt_variant=variant_name,
            language="zh-CN"
        )
        
        # Check if the "Tail Anchor" is actually there for head_tail_v1
        if variant_name == "head_tail_v1":
            if "Final Guardrails (Tail Anchor)" in system_prompt:
                print("✅ Found Tail Anchor in generated prompt.")
            else:
                print("❌ WARNING: Head/Tail optimization missing in engine output!")

        start_time = time.time()
        try:
            # Call LLM
            response = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_query)
            ])
            duration = time.time() - start_time
            
            content = response.content
            found = secret_key in content
            print(f"Latency: {duration:.2f}s")
            print(f"--- Response ---")
            print(content)
            print(f"----------------")
            print(f"Result: {'✅ SUCCESS - RECALLED MIDDLE FACT' if found else '❌ FAILURE - LOST IN THE MIDDLE'}")
            return found, content
        except Exception as e:
            print(f"❌ Error during LLM call: {e}")
            return False, str(e)

    # A/B Test Execution
    results = {}
    
    # 1. Default Baseline
    success_def, out_def = await run_variant("default")
    results["default"] = {"success": success_def, "output": out_def}
    
    # 2. Optimized (Head/Tail Anchoring)
    success_opt, out_opt = await run_variant("head_tail_v1")
    results["head_tail_v1"] = {"success": success_opt, "output": out_opt}

    # Summary
    print("\n" + "="*60)
    print("📋 EXPERIMENT SUMMARY")
    print(f"Context Fragments: {len(fragments)}")
    print(f"Default Variant:    {'✅ PASS' if success_def else '❌ FAIL'}")
    print(f"Head/Tail Variant:  {'✅ PASS' if success_opt else '❌ FAIL'}")
    print("="*60)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(test_lost_in_middle_lightweight())
