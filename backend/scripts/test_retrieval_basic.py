import asyncio
import sys
from pathlib import Path

# Paths
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path: sys.path.insert(0, str(backend_dir))

from app.services.memory.memory_service import MemoryService

async def test_retrieval():
    print("Testing Minimal Retrieval for Eval Dataset...")
    mem_svc = MemoryService(user_id="eval_judge_user")
    
    query = "Senior Management WFH policy"
    results = await mem_svc.search_memory(query, limit=3)
    
    print(f"\n[RETRIEVED {len(results)} FRAGMENTS]")
    for r in results:
        print(f"--- Fragment ---\n{r[:300]}...\n")
    
    if not results:
        print("\n🚨 RETRIEVAL RETURNED ZERO FRAGMENTS. Check ChromaDB collection 'agent_memories'.")

if __name__ == "__main__":
    from app.core.logging import setup_script_context
    setup_script_context("test_retrieval")
    asyncio.run(test_retrieval())
