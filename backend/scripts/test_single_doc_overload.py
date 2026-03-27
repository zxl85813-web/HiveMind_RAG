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

# Add backend to path and load .env
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from dotenv import load_dotenv
load_dotenv(backend_root / ".env")

# Force set ZhipuAI key for SDK
if os.getenv("EMBEDDING_API_KEY"):
    os.environ["ZHIPUAI_API_KEY"] = os.getenv("EMBEDDING_API_KEY")

from app.prompts.engine import prompt_engine
from app.agents.llm_router import LLMRouter, ModelTier
from langchain_core.messages import HumanMessage, SystemMessage

async def test_single_doc_overload():
    print("🧠 Single-Document Long-Context Stress Test")
    print("============================================")
    
    router = LLMRouter()
    llm = router.get_model(ModelTier.MEDIUM)
    
    # 1. Generate one massive block of text (~30k characters)
    distractor_para = "This is a detailed paragraph about aerodynamic stability in high-altitude gliders, discussing wing-loading, Reynolds numbers, and boundary layer separation in extreme conditions. " * 5
    distractor_block = "\n\n".join([distractor_para for _ in range(30)]) # ~25,000 - 30,000 chars total
    
    secret_key = "ZEPHYR-OMEGA-999"
    needle = f" [IMPORTANT NOTE: The system emergency override key is '{secret_key}'. Always remember this.] "
    
    # 2. Position the needle in the ABSOLUTE MIDDLE of the massive block
    mid_point = len(distractor_block) // 2
    context_one_big_doc = distractor_block[:mid_point] + needle + distractor_block[mid_point:]
    
    query = "What is the system emergency override key?"
    task_desc = "Answer the user question using ONLY the provided document. If you cannot find it, say you don't know."

    async def run_pass(variant: str):
        print(f"🚀 Testing Variant: {variant}...", end="", flush=True)
        
        system_prompt = prompt_engine.build_agent_prompt(
            agent_name="ResearchAgent",
            task=task_desc,
            rag_context=context_one_big_doc,
            prompt_variant=variant,
            language="zh-CN"
        )
        
        start_time = time.time()
        try:
            response = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=query)
            ])
            duration = time.time() - start_time
            content = str(response.content)
            success = secret_key in content
            print(f" {'✅' if success else '❌'} ({duration:.1f}s)")
            print(f"--- Response ---")
            print(content[:500] + "...")
            print(f"----------------")
            return success, content
        except Exception as e:
            print(f" ⚠️ ERROR: {e}")
            return False, str(e)

    # Comparison
    print("\n--- Test Results (15k Chars Single Block) ---")
    s1, o1 = await run_pass("default")
    s2, o2 = await run_pass("head_tail_v1")
    
    print("\n" + "="*50)
    print("📈 ANALYSIS")
    if s1 and s2:
        print("Both variants passed. The model handles 15k chars well even without anchors.")
    elif not s1 and s2:
        print("Tail Anchor variant RECOVERED the fact that the default lost! (Success)")
    elif s1 and not s2:
        print("Warning: Default passed but Tail Anchor variant failed. Possible prompt explosion.")
    else:
        print("Both failed! The context might be too dense or too long for this model tier.")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(test_single_doc_overload())
