
import asyncio
import json
import os
import sys
import uuid
from datetime import datetime

sys.path.append(os.getcwd())

from app.core.llm import get_llm_service
from app.services.memory.episodic_service import episodic_memory_service
from app.services.evaluation.multi_grader import MultiGraderEval
from app.core.database import async_session_factory
from sqlalchemy import text

# === Configurations ===
DATASET_FILE = "benchmarks/synthetic_eval_set.jsonl"
NUM_EPISODES_TO_GENERATE = 10
USER_ID = "eval_bench_user"

async def get_memories():
    async with async_session_factory() as session:
        # Get raw memories to use as context for synthesis
        res = await session.execute(text("SELECT summary, topics FROM episodic_memories LIMIT 50"))
        return res.fetchall()

async def synthesize_eval_item(memory_summary, topics):
    llm = get_llm_service()
    
    prompt = f"""
    You are an expert Evaluator for RAG systems. 
    Based on the following past conversation summary, generate a difficult but fair User Query that would require recalling this specific memory to answer correctly.
    
    Memory Summary: {memory_summary}
    Topics: {topics}
    
    Return ONLY a JSON object:
    {{
        "query": "The question the user might ask",
        "expected_facts": ["fact 1", "fact 2"],
        "difficulty": 1-5
    }}
    """
    
    try:
        resp = await llm.chat_complete([{"role": "user", "content": prompt}], json_mode=True)
        return json.loads(resp)
    except Exception as e:
        print(f"Error synthesizing item: {e}")
        return None

async def run_synthesis():
    print(f"🧬 Starting Synthetic Evaluation Set Generation...")
    memories = await get_memories()
    if not memories:
        print("❌ No memories found to synthesize from.")
        return

    os.makedirs("benchmarks", exist_ok=True)
    
    items_count = 0
    with open(DATASET_FILE, "w", encoding="utf-8") as f:
        for mem in memories[:NUM_EPISODES_TO_GENERATE]:
            summary, topics = mem
            item = await synthesize_eval_item(summary, topics)
            if item:
                item["reference_memory"] = summary
                item["generated_at"] = datetime.utcnow().isoformat()
                f.write(json.dumps(item) + "\n")
                items_count += 1
                print(f"   [+] Generated item: {item['query'][:50]}...")

    print(f"✅ Created {items_count} synthetic evaluation items in {DATASET_FILE}")

if __name__ == "__main__":
    asyncio.run(run_synthesis())
