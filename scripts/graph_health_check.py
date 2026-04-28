#!/usr/bin/env python3
"""
Graph Health Check — M9.6.1
============================
自动诊断 Neo4j 图谱中的孤立节点、断边和缺失覆盖。

输出 Markdown 报告，可接入 CI 作为架构健康门禁。

用法:
    python scripts/graph_health_check.py [--enforce] [--max-orphans 10]

退出码:
    0 — 所有检查通过
    1 — 存在超出阈值的问题（--enforce 模式）
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# 确保 backend 在 path 中
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))


# ── 诊断查询定义 ──────────────────────────────────────────────────────────────

DIAGNOSTICS = [
    {
        "id": "ORPHAN-001",
        "name": "没有订阅者的事件通道",
        "severity": "medium",
        "cypher": """
            MATCH (ec:EventChannel)
            WHERE NOT (ec)<-[:SUBSCRIBES_TO]-()
            RETURN ec.name as name, ec.id as id
        """,
    },
    {
        "id": "ORPHAN-002",
        "name": "没有测试覆盖的 API 端点",
        "severity": "medium",
        "cypher": """
            MATCH (ep:APIEndpoint)
            WHERE NOT (ep)<-[:COVERS_ENDPOINT]-(:TestFile)
            RETURN ep.path as name, ep.method as method
        """,
    },
    {
        "id": "ORPHAN-003",
        "name": "没有 Gate 保护的 API 端点",
        "severity": "high",
        "cypher": """
            MATCH (ep:APIEndpoint)
            WHERE NOT (ep)-[:GUARDED_BY]->(:GateRule)
            RETURN ep.path as name, ep.method as method
        """,
    },
    {
        "id": "ORPHAN-004",
        "name": "没有 GOVERNED_BY 关系的 SwarmNode",
        "severity": "medium",
        "cypher": """
            MATCH (sn:SwarmNode)
            WHERE NOT (sn)-[:GOVERNED_BY]->(:HarnessPolicy)
            RETURN sn.name as name
        """,
    },
    {
        "id": "ORPHAN-005",
        "name": "有 CognitiveDirective 但没有 SPAWNED HarnessPolicy",
        "severity": "high",
        "cypher": """
            MATCH (cd:CognitiveDirectiveNode)
            WHERE NOT (cd)-[:SPAWNED]->(:HarnessPolicy)
            RETURN cd.id as name, cd.topic as topic
        """,
    },
    {
        "id": "ORPHAN-006",
        "name": "没有 APPLIES_TO 任何 SwarmNode 的 HarnessPolicy",
        "severity": "low",
        "cypher": """
            MATCH (hp:HarnessPolicy)
            WHERE hp.agent_scope <> 'all'
              AND NOT (:SwarmNode)-[:GOVERNED_BY]->(hp)
            RETURN hp.name as name, hp.agent_scope as scope
        """,
    },
    {
        "id": "ORPHAN-007",
        "name": "没有 publisher 的事件通道",
        "severity": "low",
        "cypher": """
            MATCH (ec:EventChannel)
            WHERE NOT ()-[:PUBLISHES_TO]->(ec)
            RETURN ec.name as name
        """,
    },
    {
        "id": "HEALTH-001",
        "name": "HarnessCheck 24h 拦截率",
        "severity": "info",
        "cypher": """
            MATCH (hc:HarnessCheck)
            WHERE hc.created_at > timestamp() - 86400000
            RETURN count(hc) as total,
                   sum(CASE WHEN hc.passed THEN 0 ELSE 1 END) as blocked,
                   CASE WHEN count(hc) > 0
                        THEN round(100.0 * sum(CASE WHEN hc.passed THEN 0 ELSE 1 END) / count(hc), 1)
                        ELSE 0 END as block_rate_pct
        """,
    },
]


async def run_diagnostics(enforce: bool = False, max_orphans: int = 10) -> str:
    """运行所有诊断查询，生成 Markdown 报告。"""
    from app.sdk.core.graph_store import get_graph_store

    store = get_graph_store()
    if not store.driver:
        return "# ❌ Graph Health Check\n\nNeo4j not available. Skipping all checks.\n"

    report_lines = [
        "# 🏥 Graph Health Check Report",
        f"\nGenerated: {datetime.utcnow().isoformat()}Z\n",
    ]

    total_issues = 0
    high_issues = 0

    for diag in DIAGNOSTICS:
        try:
            results = await store.execute_query(diag["cypher"])
        except Exception as e:
            report_lines.append(f"## ⚠️ {diag['id']}: {diag['name']}")
            report_lines.append(f"\nQuery failed: {e}\n")
            continue

        count = len(results) if results else 0

        # 对于 info 类型的统计查询，特殊处理
        if diag["severity"] == "info" and results:
            row = results[0]
            report_lines.append(f"## ℹ️ {diag['id']}: {diag['name']}")
            report_lines.append(f"\n| Metric | Value |")
            report_lines.append(f"|---|---|")
            for k, v in row.items():
                report_lines.append(f"| {k} | {v} |")
            report_lines.append("")
            continue

        icon = "✅" if count == 0 else ("🔴" if diag["severity"] == "high" else "🟡")
        report_lines.append(f"## {icon} {diag['id']}: {diag['name']}")
        report_lines.append(f"\n**Severity**: {diag['severity']} | **Found**: {count}\n")

        if count > 0:
            total_issues += count
            if diag["severity"] == "high":
                high_issues += count

            # 显示前 10 个
            report_lines.append("| # | Name | Details |")
            report_lines.append("|---|---|---|")
            for i, row in enumerate(results[:10]):
                name = row.get("name", "?")
                details = " | ".join(f"{k}={v}" for k, v in row.items() if k != "name")
                report_lines.append(f"| {i+1} | {name} | {details} |")
            if count > 10:
                report_lines.append(f"| ... | +{count - 10} more | |")
            report_lines.append("")

    # 汇总
    report_lines.append("---")
    report_lines.append(f"\n## Summary")
    report_lines.append(f"\n- **Total issues**: {total_issues}")
    report_lines.append(f"- **High severity**: {high_issues}")
    report_lines.append(f"- **Threshold**: max_orphans={max_orphans}")

    passed = total_issues <= max_orphans
    report_lines.append(f"- **Result**: {'✅ PASS' if passed else '❌ FAIL'}")

    report = "\n".join(report_lines)

    # 写入文件
    report_path = BASE_DIR / "backend" / "logs" / "graph_health_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(f"Report written to: {report_path}")

    if enforce and not passed:
        print(f"\n❌ Graph health check FAILED: {total_issues} issues (max: {max_orphans})")
        sys.exit(1)

    return report


def main():
    parser = argparse.ArgumentParser(description="Graph Health Check")
    parser.add_argument("--enforce", action="store_true", help="Exit with code 1 if issues exceed threshold")
    parser.add_argument("--max-orphans", type=int, default=10, help="Maximum allowed orphan count")
    args = parser.parse_args()

    # 需要加载 .env
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / "backend" / ".env")

    report = asyncio.run(run_diagnostics(enforce=args.enforce, max_orphans=args.max_orphans))
    print(report)


if __name__ == "__main__":
    main()
