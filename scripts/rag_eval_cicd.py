import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Adjust path to include backend
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR / "backend"))

from app.services.generation.pipeline import get_generation_service
from app.services.evaluation.multi_grader import MultiGraderEval

EVAL_SET_PATH = BASE_DIR / "backend" / "benchmarks" / "synthetic_eval_set.jsonl"
REPORT_PATH = BASE_DIR / "rag_eval_report.md"
CHEATSHEET_PATH = BASE_DIR / "docs" / "evaluation" / "METRICS_CHEATSHEET.md"

async def run_cicd_eval():
    print(f"Starting RAG CI/CD Evaluation Gate...")
    
    if not EVAL_SET_PATH.exists():
        print(f"Error: Eval set not found at {EVAL_SET_PATH}")
        return

    pipeline = get_generation_service()
    grader = MultiGraderEval()
    
    items = []
    with open(EVAL_SET_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                items.append(json.loads(line))

    # Limit items for CI speed if needed, here we take first 5
    test_items = items[:5]
    print(f"Evaluating {len(test_items)} scenarios...")

    results = []
    for i, item in enumerate(test_items):
        query = item["query"]
        expected_facts = item["expected_facts"]
        
        print(f"   [{i+1}/{len(test_items)}] Query: {query[:50]}...")
        
        # 1. Pipeline Execution
        ctx = await pipeline.run(query, kb_ids=[], user_id="cicd_runner")
        response = ctx.draft_content
        
        # 2. Robust Grading (n=3)
        context_for_grader = "EXPECTED FACTS:\n" + "\n".join(f"- {f}" for f in expected_facts)
        eval_result = await grader.evaluate(query, response, context=context_for_grader, n=3)
        
        results.append({
            "query": query,
            "score": eval_result.composite_score,
            "confidence": eval_result.confidence_score,
            "verdict": eval_result.verdict,
            "opinions": eval_result.opinions
        })

    # --- Generate Report ---
    avg_score = sum(r["score"] for r in results) / len(results)
    avg_confidence = sum(r["confidence"] for r in results) / len(results)
    
    report_md = f"""# 🛡️ RAG Evaluation CI/CD Report
Generated at: {datetime.now().isoformat()}

## 📈 Quality Summary
- **Average Score**: `{avg_score:.2f}`
- **Average Confidence**: `{avg_confidence:.2f}`
- **Status**: {"✅ PASS" if avg_score >= 0.7 else "❌ FAIL"}

| Scenario | Score | Confidence | Verdict |
|----------|-------|------------|---------|
"""
    for r in results:
        report_md += f"| {r['query'][:40]}... | {r['score']} | {r['confidence']} | {r['verdict']} |\n"

    report_md += "\n## 🔍 Top Bad Cases\n"
    bad_cases = [r for r in results if r['score'] < 0.7]
    for bc in bad_cases:
        report_md += f"### Query: {bc['query']}\n"
        report_md += f"- **Score**: {bc['score']}\n"
        report_md += "- **Issues**:\n"
        for op in bc['opinions']:
            if op.score < 0.7:
                report_md += f"  - **{op.aspect}** ({op.score}): {op.reasoning}\n"
        
    # --- Append Cheatsheet for Diagnostic ---
    if CHEATSHEET_PATH.exists():
        with open(CHEATSHEET_PATH, "r", encoding="utf-8") as f:
            cheatsheet_content = f.read()
            report_md += "\n\n---\n\n## 💡 Diagnostic Toolkit (Quick Reference)\n"
            report_md += "> 当分值较低时，请参考以下指南进行优化。\n\n"
            report_md += cheatsheet_content

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(report_md)
    
    print(f"✅ Report generated at {REPORT_PATH}")
    
    # Exit with error if score is too low
    if avg_score < 0.7:
        print("❌ Quality gate failed: Score < 0.7")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_cicd_eval())
