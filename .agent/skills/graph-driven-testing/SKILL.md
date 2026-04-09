---
name: graph-driven-testing
description: 基于 Neo4j 架构图谱的测试盲区诊断、自动化用例生成与 Trace 闭环验证技能。每当用户询问“系统测试是否完整”、“如何补齐覆盖率”、“目前的盲区在哪里”或提到代码与需求的对齐关系时，必须使用此技能进行图谱诊断。
---

# 🧪 图谱驱动测试技能 (Graph-Driven Testing Skill)

> **核心理念**: 测试不再是盲目的覆盖率游戏，而是基于 **Digital Twin (Neo4j)** 的精准补全。每个测试必须关联一个需求节点 `REQ` 和一个架构节点 `AAA`。

## 🕸️ Graph Ontology Integration
本技能依赖于以下图谱关系：
- `(REQ:Requirement)-[:IMPLEMENTED_BY]->(AAA:ArchitecturalAsset)`
- `(TST:TestCase)-[:VERIFIES]->(REQ)`
- `(TST)-[:EXERCISES]->(AAA)`
- `(TST)-[:LOGS_TRACE]->(TRC:Trace)`

## 🛠️ Execution Patterns (Inspired by SkillHub)

### Pattern 1: 侦察与盲区分析 (Reconnaissance)
**目的**: 找出哪些代码或需求处于“全裸”状态。
```powershell
# 运行脚本找出没有任何测试关联的需求
python .agent/skills/graph-driven-testing/scripts/gap_analyzer.py --mode requirements
```

### Pattern 2: 验证式生成 (Validated Generation)
**目的**: 自动生成测试并自愈。
1. 使用 `prompts/test-gen.j2` 生成代码。
2. 运行 `scripts/test_validator.py`。
3. 如果失败（Stderr 包含 ImportError 或 AssertionError），自动将错误反馈给提示词重新生成。

### Pattern 3: 影响驱动回测 (Impact Runner)
**目的**: 修改 A 文件，只跑 B, C, D 测试。
```powershell
# 根据图谱依赖关系，找出受影响的测试用例并执行
python .agent/skills/graph-driven-testing/scripts/impact_runner.py --changed-file backend/app/sdk/core/token_service.py
```

## 📝 落地流程
1. **Query**: 查询 Neo4j 确定测试目标。
2. **Scaffold**: 生成带 `pytest` 标记的测试文件。
3. **Execute**: 运行 `hm_test.py` 采集覆盖率。
4. **Sync**: 运行 `scripts/index_architecture.py` 将新的 `TST` 节点及其 TraceID 回填进图谱。

## 🛡️ 验收准则
- **内聚性**: 每个生成的测试必须包含 `@pytest.mark.graph(req="REQ-XXX")`。
- **准确性**: 必须通过变异测试 (Mutation Test) 的初步筛选。
- **可验证性**: 测试必须生成一份包含 TraceID 的 HTML 报告存入 `logs/testing/`。
