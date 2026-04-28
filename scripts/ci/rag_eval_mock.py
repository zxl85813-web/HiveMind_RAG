#!/usr/bin/env python3
"""
RAG Evaluation Mock Runner
===========================
在不调用真实 LLM API 的情况下运行 RAG 评估流程，用于：
  - feature 分支 PR（快速反馈，零成本）
  - 预算超出时的降级模式
  - CI 环境调试

Mock 策略:
  - 使用预置的合成响应替代真实 LLM 生成
  - 评分使用关键词匹配而非 LLM grading
  - 始终通过（score=0.75），仅验证流程完整性

输出格式与 rag_eval_cicd.py 完全一致，确保报告结构兼容。
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
EVAL_SET_PATH = BASE_DIR / "backend" / "benchmarks" / "synthetic_eval_set.jsonl"
REPORT_PATH = BASE_DIR / "rag_eval_report.md"

# Mock 评分（固定值，仅验证流程）
MOCK_SCORE = 0.75
MOCK_CONFIDENCE = 0.60
MOCK_VERDICT = "MOCK_PASS"


def keyword_score(response: str, expected_facts: list[str]) -> float:
    """
    基于关键词匹配的轻量评分（不调用 LLM）。
    检查 expected_facts 中的关键词是否出现在 response 中。
    """
    if not response or not expected_facts:
        return MOCK_SCORE

    response_lower = response.lower()
    hits = 0
    for fact in expected_facts:
        # 提取 fact 中的关键词（长度 > 3 的词）
        keywords = [w.lower() for w in fact.split() if len(w) > 3]
        if keywords and any(kw in response_lower for kw in keywords):
            hits += 1

    return round(0.5 + 0.5 * (hits / len(expected_facts)), 2) if expected_facts else MOCK_SCORE


def run_mock_eval() -> None:
    print("[MockEval] Starting RAG Mock Evaluation (no LLM API calls)...")

    if not EVAL_SET_PATH.exists():
        print(f"[MockEval] Eval set not found at {EVAL_SET_PATH}, using synthetic data.")
        items = [
            {
                "query": "What is RAG?",
                "expected_facts": ["retrieval augmented generation", "knowledge base", "vector search"],
            },
            {
                "query": "How does the system handle authentication?",
                "expected_facts": ["JWT", "token", "authentication"],
            },
        ]
    else:
        items = []
        with open(EVAL_SET_PATH, encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    items.append(json.loads(line))
        items = items[:5]  # 与真实评估保持一致

    print(f"[MockEval] Evaluating {len(items)} scenarios (mock mode)...")

    results = []
    for i, item in enumerate(items):
        query = item["query"]
        expected_facts = item.get("expected_facts", [])

        # Mock 响应：直接拼接 expected_facts 作为"生成内容"
        mock_response = "Based on the knowledge base: " + ". ".join(expected_facts[:2])

        score = keyword_score(mock_response, expected_facts)
        print(f"  [{i+1}/{len(items)}] Query: {query[:50]}... → score={score} (mock)")

        results.append({
            "query": query,
            "score": score,
            "confidence": MOCK_CONFIDENCE,
            "verdict": MOCK_VERDICT,
            "mode": "mock",
        })

    avg_score = sum(r["score"] for r in results) / len(results)
    avg_confidence = sum(r["confidence"] for r in results) / len(results)

    report_md = f"""# 🎭 RAG Evaluation CI/CD Report (Mock Mode)
Generated at: {datetime.now().isoformat()}

> ⚠️ **Mock Mode**: This report was generated without real LLM API calls.
> Scores reflect keyword-matching heuristics, not actual RAG quality.
> Real evaluation runs on: `main` push, `release/*` PR, and `develop` push with RAG core changes.

## 📈 Quality Summary (Mock)
- **Average Score**: `{avg_score:.2f}` *(mock heuristic)*
- **Average Confidence**: `{avg_confidence:.2f}` *(fixed mock value)*
- **Status**: ✅ MOCK_PASS *(pipeline integrity verified)*

| Scenario | Score | Confidence | Verdict |
|----------|-------|------------|---------|
"""
    for r in results:
        report_md += f"| {r['query'][:40]}... | {r['score']} | {r['confidence']} | {r['verdict']} |\n"

    report_md += """
## ℹ️ Why Mock Mode?
This evaluation ran in mock mode because one of the following conditions was met:
- This is a feature branch PR (real eval runs on develop/main only)
- Daily LLM budget exceeded 80%
- No RAG core path changes detected in this push

To trigger a real evaluation, push to `develop` with changes in:
- `backend/app/services/evaluation/`
- `backend/app/services/generation/`
- `backend/app/prompts/`
- `benchmarks/`
"""

    REPORT_PATH.write_text(report_md, encoding="utf-8")
    print(f"[MockEval] ✅ Mock report generated at {REPORT_PATH}")
    print(f"[MockEval] Average score: {avg_score:.2f} (mock)")


if __name__ == "__main__":
    run_mock_eval()
