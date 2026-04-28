
import asyncio
import json
import os
import sys
import time
from datetime import datetime

sys.path.append(os.getcwd())

from app.services.generation.pipeline import get_generation_service
from app.services.evaluation.multi_grader import MultiGraderEval

EVAL_SET_PATH = "benchmarks/synthetic_eval_set.jsonl"
RESULTS_PATH = "benchmarks/eval_results_v2.jsonl"
USER_ID = "eval_bench_user"

async def run_evaluation():
    if not os.path.exists(EVAL_SET_PATH):
        print(f"❌ Eval set not found at {EVAL_SET_PATH}")
        return

    pipeline = get_generation_service()
    grader = MultiGraderEval()
    
    items = []
    with open(EVAL_SET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))

    print(f"[START] Running Evaluation on {len(items)} items...")
    
    results = []
    for i, item in enumerate(items):
        query = item["query"]
        expected_facts = item["expected_facts"]
        
        print(f"   [{i+1}/{len(items)}] Query: {query[:60]}...")
        
        start_time = time.time()
        # 1. Run the system
        ctx = await pipeline.run(query, kb_ids=[], user_id=USER_ID)
        response = ctx.draft_content
        latency = time.time() - start_time
        
        # 2. Grade it
        # We pass expected facts as 'context' to the grader so it knows what to look for
        context_for_grader = "EXPECTED FACTS TO CHECK:\n" + "\n".join(f"- {f}" for f in expected_facts)
        eval_result = await grader.evaluate(query, response, context=context_for_grader)
        
        # 3. Store result
        # Handle non-serializable response (DesignResult)
        serializable_response = response
        if hasattr(response, "model_dump"):
            serializable_response = response.model_dump()

        res_item = {
            "query": query,
            "response": serializable_response,
            "expected_facts": expected_facts,
            "score": eval_result.composite_score,
            "verdict": eval_result.verdict,
            "latency": round(latency, 2),
            "opinions": [o.model_dump() if hasattr(o, "model_dump") else o for o in eval_result.opinions],
            "timestamp": datetime.utcnow().isoformat()
        }
        results.append(res_item)
        
        with open(RESULTS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(res_item) + "\n")
        
        print(f"      Result: {eval_result.verdict} (Score: {eval_result.composite_score})")

    avg_score = sum(r["score"] for r in results) / len(results)
    print(f"\n[DONE] Evaluation Finished! Average Score: {avg_score:.2f}")
    print(f"[INFO] Full results saved to {RESULTS_PATH}")

if __name__ == "__main__":
    asyncio.run(run_evaluation())
