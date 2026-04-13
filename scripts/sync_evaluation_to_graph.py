"""
评估体系 → Neo4j 图谱同步脚本

将评估体系的组件关系同步到 Neo4j，建立以下节点和关系:

节点类型:
  - EvalFramework: 评估框架 (RAG / Agent)
  - EvalLayer: 评估层级 (L1~L4)
  - EvalGrader: 评估器 (Faithfulness / Relevance / ...)
  - EvalMetric: 评估指标
  - EvalDocument: 评估文档
  - EvalAssertion: 硬规则断言

关系类型:
  - CONTAINS_LAYER: 框架包含层级
  - USES_GRADER: 层级使用评估器
  - PRODUCES_METRIC: 评估器产出指标
  - ENFORCED_BY: 评估器受硬规则约束
  - DOCUMENTED_IN: 组件的文档位置
  - IMPLEMENTED_IN: 组件的代码位置
  - FEEDS_INTO: 评估结果流向 (L3 失败 → L4 反思)
"""

import asyncio
import os
import sys
from pathlib import Path

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(project_root, "backend"))

from app.sdk.core.graph_store import get_graph_store


# ─── 评估体系节点定义 ─────────────────────────────────────────────────────

RAG_FRAMEWORK = {
    "id": "EVAL-RAG",
    "name": "RAG 评估框架",
    "version": "v2.0",
    "description": "三层分层评测 + LLM-as-Judge + 硬规则断言",
}

AGENT_FRAMEWORK = {
    "id": "EVAL-AGENT",
    "name": "Agent 评估框架",
    "version": "v1.0",
    "description": "四层分层评测 (L1~L4) + 过程完整性审计",
}

RAG_LAYERS = [
    {
        "id": "RAG-L1",
        "name": "L1: Retriever 独立评测",
        "scope": "检索侧",
        "method": "脱离生成，单独压测召回能力",
    },
    {
        "id": "RAG-L2",
        "name": "L2: Generator 独立评测",
        "scope": "生成侧",
        "method": "注入标准上下文，消除检索噪音",
    },
    {
        "id": "RAG-L3",
        "name": "L3: 端到端评测",
        "scope": "全链路",
        "method": "完整 RAG 链路 + 6 维度独立 Grader",
    },
]

AGENT_LAYERS = [
    {
        "id": "AGENT-L1",
        "name": "L1: 单 Agent 评测",
        "scope": "单体能力",
        "method": "工具调用准确性、输出格式合规、响应延迟",
    },
    {
        "id": "AGENT-L2",
        "name": "L2: 协作评测",
        "scope": "多 Agent 协作",
        "method": "路由决策质量、并行协调效率、共识达成质量",
    },
    {
        "id": "AGENT-L3",
        "name": "L3: 智体能力评测",
        "scope": "高阶认知",
        "method": "推理能力、指令遵从、代码智能、安全边界",
    },
    {
        "id": "AGENT-L4",
        "name": "L4: 过程完整性审计",
        "scope": "推理链结构",
        "method": "证据链路、批判性摩擦、逻辑一致性、指令遵从",
    },
]

GRADERS = [
    {
        "id": "GRADER-FAITH",
        "name": "FaithfulnessGrader",
        "dimension": "faithfulness",
        "method": "逐句 claim 验证",
        "code_path": "app/services/evaluation/graders/faithfulness.py",
        "layer": "RAG-L3",
    },
    {
        "id": "GRADER-RELEV",
        "name": "RelevanceGrader",
        "dimension": "answer_relevance",
        "method": "逆向问题生成 + 语义相似度",
        "code_path": "app/services/evaluation/graders/relevance.py",
        "layer": "RAG-L3",
    },
    {
        "id": "GRADER-CORRECT",
        "name": "CorrectnessGrader",
        "dimension": "answer_correctness",
        "method": "GT 事实对比 (TP/FN/FP)",
        "code_path": "app/services/evaluation/graders/correctness.py",
        "layer": "RAG-L3",
    },
    {
        "id": "GRADER-CTX-PREC",
        "name": "ContextPrecisionGrader",
        "dimension": "context_precision",
        "method": "检索信噪比评估",
        "code_path": "app/services/evaluation/graders/context.py",
        "layer": "RAG-L3",
    },
    {
        "id": "GRADER-CTX-REC",
        "name": "ContextRecallGrader",
        "dimension": "context_recall",
        "method": "信息覆盖度评估",
        "code_path": "app/services/evaluation/graders/context.py",
        "layer": "RAG-L3",
    },
    {
        "id": "GRADER-MULTI",
        "name": "MultiGraderEval",
        "dimension": "composite",
        "method": "6 维度独立评分 + 硬规则联动",
        "code_path": "app/services/evaluation/multi_grader.py",
        "layer": "AGENT-L3",
    },
]

ASSERTIONS = [
    {
        "id": "ASSERT-CITE-001",
        "rule_id": "CITE-001",
        "description": "有上下文时必须包含 [N] 引用标记",
        "penalty": 0.2,
        "code_path": "app/services/evaluation/rag_assertion_grader.py",
    },
    {
        "id": "ASSERT-CITE-002",
        "rule_id": "CITE-002",
        "description": "无上下文时必须声明未找到",
        "penalty": 0.1,
        "code_path": "app/services/evaluation/rag_assertion_grader.py",
    },
    {
        "id": "ASSERT-TOOL-001",
        "rule_id": "TOOL-001",
        "description": "禁止危险工具调用 (rm -rf, DROP TABLE)",
        "penalty": 1.0,
        "code_path": "app/agents/nodes/reflection.py",
    },
    {
        "id": "ASSERT-SAFE-001",
        "rule_id": "SAFE-001",
        "description": "禁止泄露敏感信息",
        "penalty": 1.0,
        "code_path": "app/agents/nodes/utils.py",
    },
]

DOCUMENTS = [
    {
        "id": "DOC-RAG-FRAMEWORK",
        "name": "RAG 评测综合指南",
        "path": "docs/evaluation/RAG_EVALUATION_FRAMEWORK.md",
        "framework": "EVAL-RAG",
    },
    {
        "id": "DOC-AGENT-FRAMEWORK",
        "name": "Agent 评测综合指南",
        "path": "docs/evaluation/AGENT_EVALUATION_FRAMEWORK.md",
        "framework": "EVAL-AGENT",
    },
    {
        "id": "DOC-AUDIT-REPORT",
        "name": "评估体系审计报告",
        "path": "docs/evaluation/EVALUATION_SYSTEM_AUDIT.md",
        "framework": "EVAL-RAG",
    },
    {
        "id": "DOC-RAG-CHEAT",
        "name": "RAG 指标速查表",
        "path": "docs/evaluation/METRICS_CHEATSHEET.md",
        "framework": "EVAL-RAG",
    },
    {
        "id": "DOC-AGENT-CHEAT",
        "name": "Agent 指标速查表",
        "path": "docs/evaluation/AGENT_METRICS_CHEATSHEET.md",
        "framework": "EVAL-AGENT",
    },
    {
        "id": "DOC-L3-BOARD",
        "name": "L3 质量看板",
        "path": "docs/evaluation/L3_QUALITY_BOARD.md",
        "framework": "EVAL-AGENT",
    },
    {
        "id": "DOC-L4-REPORT",
        "name": "L4 完整性报告",
        "path": "docs/evaluation/L4_INTEGRITY_REPORT.md",
        "framework": "EVAL-AGENT",
    },
]

# 数据流关系: 评估结果如何驱动系统进化
DATA_FLOWS = [
    ("RAG-L3", "AGENT-L3", "FEEDS_INTO", "L3 RAG 评分注入 Agent 反思节点"),
    ("AGENT-L3", "AGENT-L4", "FEEDS_INTO", "L3 失败触发 L4 过程审计"),
    ("AGENT-L4", "SELF-LEARNING", "FEEDS_INTO", "L4 审计结果驱动自进化反思"),
]


async def sync_evaluation_graph():
    """将评估体系同步到 Neo4j 图谱。"""
    store = get_graph_store()

    if not store.driver:
        print("⚠️ Neo4j not available, skipping graph sync.")
        return

    print("🎯 Syncing Evaluation System to Neo4j Graph...")

    # 1. 创建框架节点
    for fw in [RAG_FRAMEWORK, AGENT_FRAMEWORK]:
        await store.execute_query(
            "MERGE (f:EvalFramework {id: $id}) "
            "SET f.name = $name, f.version = $version, "
            "f.description = $description, f.last_sync = timestamp()",
            fw,
        )
        print(f"  ✅ Framework: {fw['name']}")

    # 2. 创建层级节点 + 关联框架
    for layer in RAG_LAYERS:
        await store.execute_query(
            "MERGE (l:EvalLayer {id: $id}) "
            "SET l.name = $name, l.scope = $scope, l.method = $method "
            "WITH l "
            "MATCH (f:EvalFramework {id: 'EVAL-RAG'}) "
            "MERGE (f)-[:CONTAINS_LAYER]->(l)",
            layer,
        )
        print(f"  ✅ RAG Layer: {layer['name']}")

    for layer in AGENT_LAYERS:
        await store.execute_query(
            "MERGE (l:EvalLayer {id: $id}) "
            "SET l.name = $name, l.scope = $scope, l.method = $method "
            "WITH l "
            "MATCH (f:EvalFramework {id: 'EVAL-AGENT'}) "
            "MERGE (f)-[:CONTAINS_LAYER]->(l)",
            layer,
        )
        print(f"  ✅ Agent Layer: {layer['name']}")

    # 3. 创建评估器节点 + 关联层级
    for grader in GRADERS:
        await store.execute_query(
            "MERGE (g:EvalGrader {id: $id}) "
            "SET g.name = $name, g.dimension = $dimension, "
            "g.method = $method, g.code_path = $code_path "
            "WITH g "
            "MATCH (l:EvalLayer {id: $layer}) "
            "MERGE (l)-[:USES_GRADER]->(g)",
            grader,
        )
        print(f"  ✅ Grader: {grader['name']}")

    # 4. 创建断言节点 + 关联评估器
    for assertion in ASSERTIONS:
        await store.execute_query(
            "MERGE (a:EvalAssertion {id: $id}) "
            "SET a.rule_id = $rule_id, a.description = $description, "
            "a.penalty = $penalty, a.code_path = $code_path",
            assertion,
        )
        # 关联到所有 Grader（硬规则是全局的）
        await store.execute_query(
            "MATCH (a:EvalAssertion {id: $id}), (g:EvalGrader) "
            "MERGE (g)-[:ENFORCED_BY]->(a)",
            {"id": assertion["id"]},
        )
        print(f"  ✅ Assertion: {assertion['rule_id']}")

    # 5. 创建文档节点 + 关联框架
    for doc in DOCUMENTS:
        await store.execute_query(
            "MERGE (d:EvalDocument {id: $id}) "
            "SET d.name = $name, d.path = $path "
            "WITH d "
            "MATCH (f:EvalFramework {id: $framework}) "
            "MERGE (f)-[:DOCUMENTED_IN]->(d)",
            doc,
        )
        print(f"  ✅ Document: {doc['name']}")

    # 6. 创建数据流关系
    for src, dst, rel_type, desc in DATA_FLOWS:
        await store.execute_query(
            f"MATCH (s {{id: $src}}), (d {{id: $dst}}) "
            f"MERGE (s)-[r:{rel_type}]->(d) "
            f"SET r.description = $desc",
            {"src": src, "dst": dst, "desc": desc},
        )
        print(f"  ✅ Flow: {src} → {dst}")

    # 7. 关联到现有代码节点（如果存在）
    code_links = [
        ("GRADER-FAITH", "EvaluationService", "PART_OF"),
        ("GRADER-RELEV", "EvaluationService", "PART_OF"),
        ("GRADER-CORRECT", "EvaluationService", "PART_OF"),
        ("GRADER-CTX-PREC", "EvaluationService", "PART_OF"),
        ("GRADER-CTX-REC", "EvaluationService", "PART_OF"),
        ("GRADER-MULTI", "SwarmOrchestrator", "USED_BY"),
    ]
    for grader_id, service_name, rel in code_links:
        await store.execute_query(
            f"MATCH (g:EvalGrader {{id: $gid}}) "
            f"OPTIONAL MATCH (s) WHERE s.id CONTAINS $sname OR s.name CONTAINS $sname "
            f"FOREACH (x IN CASE WHEN s IS NOT NULL THEN [s] ELSE [] END | "
            f"  MERGE (g)-[:{rel}]->(x))",
            {"gid": grader_id, "sname": service_name},
        )

    print("\n🎯 Evaluation Graph Sync Complete!")
    print(f"   Frameworks: {len([RAG_FRAMEWORK, AGENT_FRAMEWORK])}")
    print(f"   Layers: {len(RAG_LAYERS) + len(AGENT_LAYERS)}")
    print(f"   Graders: {len(GRADERS)}")
    print(f"   Assertions: {len(ASSERTIONS)}")
    print(f"   Documents: {len(DOCUMENTS)}")


if __name__ == "__main__":
    asyncio.run(sync_evaluation_graph())
