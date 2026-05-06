# 🧠 Neo4j 赋能的 AI 治理体系

> 用知识图谱理解代码，让 CI/CD 从"规则检查"进化为"语义审计"

---

## 核心理念：让代码库本身成为知识图谱

```
传统 CI/CD：  代码 → 静态规则检查 → Pass/Fail
Neo4j CI/CD：  代码 → 图谱建模 → 语义推理 → 影响域感知 → 精准门禁
```

我们的 `Neo4jStore` + `GraphExtractor` 已经能提取实体关系。
现在我们正在将该能力升级为 **全域治理图谱 (Universal Governance Graph, UGG)**，参见 [DES-015: UGG 规格说明书](design/DES-015-governance-graph-spec.md)。

---

## 第一层：代码血缘与 AI 归因 (UGG) 建模

### 节点类型

| 节点 Label | 含义 | 示例 |
|:---|:---|:---|
| `:Module` | Python/TS 模块 | `app.services.knowledge.graph_extractor` |
| `:Function` | 函数/方法 | `GraphExtractor.extract_knowledge_graph` |
| `:AgentNode` | LangGraph 节点 | `scope_guardian_node` |
| `:Prompt` | Prompt 模板文件 | `prompts/agents/supervisor.yaml` |
| `:BuilderState` | Graph 状态字段 | `coverage_pct`, `next_step` |
| `:Skill` | Agent Skill | `SkillRegistry.order_query` |
| `:Test` | 测试用例 | `tests/unit/test_interview_node.py` |

### 边类型 (关系)

```cypher
(:Function)-[:CALLS]->(:Function)           // 函数调用链
(:AgentNode)-[:READS_STATE]->(:BuilderState) // 节点读取的状态字段
(:AgentNode)-[:WRITES_STATE]->(:BuilderState)// 节点写入的状态字段
(:AgentNode)-[:USES_PROMPT]->(:Prompt)       // 节点使用的 Prompt
(:Test)-[:COVERS]->(:Function)               // 测试覆盖关系
(:AgentNode)-[:TRANSITIONS_TO]->(:AgentNode) // 图中的边（路由关系）
(:Function)-[:DEPENDS_ON]->(:Module)         // 模块依赖
```

---

## 第二层：CI/CD 中的图谱应用

### 2.1 变更影响域分析 (Impact Analysis)

**触发**：每次 PR，解析 git diff 提取变更文件/函数。

```cypher
// 查询：某个 Prompt 被修改后，哪些 AgentNode 会受影响？
MATCH (p:Prompt {path: "prompts/agents/supervisor.yaml"})
<-[:USES_PROMPT]-(node:AgentNode)
-[:TRANSITIONS_TO*1..3]->(downstream:AgentNode)
RETURN node.name, downstream.name
```

**效果**：CI 不再傻傻跑全量测试，而是精准识别出"这个 PR 改了 `interview_node` 的 Prompt，
因此只需要重跑覆盖 `interview → scope_guardian → testset_creation` 链路的集成测试。"

---

### 2.2 State 字段孤儿检测 (Orphan Field Guard)

```cypher
// 查询：哪些 BuilderState 字段没有任何 AgentNode 读取？（死字段）
MATCH (s:BuilderState)
WHERE NOT (s)<-[:READS_STATE]-(:AgentNode)
RETURN s.name AS orphan_field
```

**CI 集成**：如果 AI 往 `BuilderState` 里新增了字段，但没有任何节点读取它，
图谱会立刻标记为 `ORPHAN_FIELD` 并在 PR 评论中告警：
```
⚠️ [Graph Guard] 新字段 `agent_persona` 已写入 State，但无节点读取。
   是否遗漏了对应的消费逻辑？
```

---

### 2.3 死循环风险检测 (Cycle Risk)

```cypher
// 检测图中的循环路径（排除 interview 回路这种合法的打回逻辑）
MATCH path = (n:AgentNode)-[:TRANSITIONS_TO*2..10]->(n)
WHERE n.name <> "interview"
RETURN [node IN nodes(path) | node.name] AS cycle
```

**CI 集成**：路由函数变更后，自动在 Neo4j 里更新边，并运行此查询。
发现非预期循环时，**硬阻断** PR 合并。

---

### 2.4 测试覆盖语义分析 (Semantic Coverage)

传统的 pytest-cov 只能告诉你"第 42 行被执行了"。
图谱可以告诉你"**高风险的路由决策函数 `route_from_testset` 被哪些测试覆盖了**"：

```cypher
// 查询：核心路由函数的测试覆盖率
MATCH (f:Function {name: "route_from_testset"})
OPTIONAL MATCH (t:Test)-[:COVERS]->(f)
RETURN f.name, collect(t.path) AS covered_by, 
       CASE WHEN count(t) = 0 THEN "🔴 UNCOVERED" ELSE "🟢 COVERED" END AS status
```

**CI 报告**：在 GitHub Summary 中输出一张"关键路由函数覆盖热力图"，
一眼看出哪些 Agent 决策逻辑是测试盲区。

---

## 第三层：Review 的图谱增强

### 3.1 自动生成 PR 的"影响地图"

PR 创建时，GitHub Actions 触发图谱查询，在 PR Body 中自动注入：

```markdown
## 🗺️ 变更影响域分析 (Neo4j Graph)

**变更文件**: `backend/app/services/builder/nodes/guardian.py`

**直接影响**:
- AgentNode: `scope_guardian_node`
- 读取 State 字段: `next_step`, `scope_summary`
- 写入 State 字段: `next_step`

**下游传播**:
- → `context_injection_node` (通过 route_from_guardian)
- → `interview_node` (回退路径，发生 scope 冲突时)

**Prompt 依赖**:
- `prompts/builder/scope_guardian.yaml` (⚠️ 本次 PR 未修改，请确认兼容性)

**建议 Reviewer 重点关注**:
1. `route_from_guardian()` 的分支逻辑是否完整处理了所有 `next_step` 值？
2. 下游的 `context_injection_node` 是否能处理新的 State 输出？
```

---

### 3.2 Prompt-Code 漂移检测 (Drift Detection)

```cypher
// 查询：Prompt 最近被修改，但对应的 AgentNode 测试未运行
MATCH (p:Prompt)-[:USED_BY]->(n:AgentNode)<-[:COVERS]-(t:Test)
WHERE p.last_modified > n.last_tested
RETURN p.path AS drifted_prompt, n.name AS affected_node, 
       collect(t.path) AS stale_tests
```

**Review 规范**：任何修改 Prompt 的 PR，图谱会自动检测并要求 Reviewer
验证对应的黄金测试集（`backend/scripts/run_evaluation_v2.py`）是否通过。

---

## 第四层：实施路线图

### Phase 1：CKG 基础建设 (1-2周)
```
backend/scripts/evals/build_code_graph.py
```
- 解析 `backend/app/` 的 AST，提取 Function、Module 节点
- 解析 `backend/app/services/builder/graph.py`，提取 AgentNode 和路由边
- 解析 `BuilderState`，提取所有 TypedDict 字段
- 写入 Neo4j（复用现有 `Neo4jStore.import_subgraph`）

### Phase 2：CI 集成 (1周)
```yaml
# .github/workflows/develop-ci.yml 新增步骤
- name: 🧠 Graph Impact Analysis
  run: |
    python backend/scripts/evals/build_code_graph.py --diff-only
    python backend/scripts/evals/graph_guard.py --check=orphan,cycle,coverage
```

### Phase 3：PR Bot (1-2周)
- GitHub App 或 Actions Bot 在 PR 创建时查询图谱
- 自动生成影响域 Markdown 注入 PR 评论
- SonarQube + Neo4j 双轨质量报告

---

## 技术整合点

```python
# 复用现有 Neo4jStore，扩展新方法
class Neo4jStore:
    # 已有
    def import_subgraph(self, nodes, edges): ...
    def query(self, cypher, params): ...
    
    # 新增：专为 CI 场景设计
    def get_impact_domain(self, changed_files: list[str]) -> dict: ...
    def detect_orphan_state_fields(self) -> list[str]: ...
    def detect_cycles(self) -> list[list[str]]: ...
    def get_uncovered_routing_functions(self) -> list[str]: ...
```

---

## 相关文档

- [开发治理规范](DEV_GOVERNANCE.md)
- [Agent 治理架构](AGENT_GOVERNANCE.md)
- [Builder Graph 设计](design/DES-014-agent-builder-assistant.md)
- [Neo4j Store 实现](../backend/app/core/graph_store.py)
- [Graph Community Service](../backend/app/services/knowledge/graph_community.py)
