# 🎯 HiveMind 架构映射与测试覆盖率闭环计划 (Implementation Plan)

> **目标**: 实现“代码-设计-业务-测试”的 Neo4j 全量映射，并基于图谱关系驱动测试用例生成与覆盖率百分比审计。

---

## 🟢 第一阶段：Neo4j 数据深度全量录入 (Data Ingestion)

这一步是将原本孤立的文件、代码、设计、业务流程全部“神经联通”。

### 1.1 资产全扫描 (Current Action)
-   **脚本**: `python .agent/skills/architectural-mapping/scripts/index_architecture.py`
-   **节点类型**:
    -   `Requirement`: `docs/requirements/REQ-*.md`
    -   `Design`: `docs/architecture/*.md` 和 `docs/design/*.md`
    -   `File`: 所有 `.py`, `.ts`, `.tsx` 源码。
    -   `Todo`: `TODO.md` 中的业务任务。
-   **关系建立**:
    -   使用正则表达式提取 `SPECIFIES` (涵盖的文件路径) 和 `ADDRESSES` (针对的需求 ID) 关系。

### 1.2 AST 深度关联
-   解析后端 Python 代码的 `ast`，提取 Class/Function 调用关系 `[:CALLS]`。
-   将 `DatabaseModel` 与 `File` 关联 `[:DEFINES_MODEL]`。

---

## 🔵 第二阶段：基于图谱制作测试用例 (Test Generation)

这一步变“盲目写测试”为“按图索骥写业务测试”。

### 2.1 路径发现 (Impact Analysis)
-   当我们针对 `REQ-001` (知识库上传) 制作测试时。
-   **操作**: 运行 `query_architecture.py --req REQ-001`。
-   **输出**: 图谱会吐出该需求关联的所有 `Design` 文档、前端组件路径、后端 Service 路径。
-   **Case 制作**: 生成一份 **“跨层串联 Case”**。
    -   前端模拟录入 -> API 捕获 -> 后端模型入库验证。

### 2.2 智体辅助 Case 生成
-   利用现有 `generate-tests` 技能。
-   **逻辑**: 输入不仅是单个文件，而是 **“Neo4j 路径上下文”**（即：告诉 AI 这个文件在业务流中的位置），让生成的测试 Case 具备业务语境。

---

## 🟡 第三阶段：基于 Neo4j 的覆盖率审计 (Coverage Audit)

这一步解决“我们到底测全了吗”的问题。

### 3.1 定义“业务覆盖率”
区别于传统的代码行覆盖率，我们定义 **“架构覆盖率 (Arch-Coverage)”**：
-   公式：`测过的业务节点 / 总业务节点 = 架构覆盖率 %`

### 3.2 覆盖率看板生成
我们将编写一个新的工具 `audit_architecture_coverage.py`，执行以下 Cypher：
```cypher
// 查找所有没有被 Test 节点指向的 Requirement
MATCH (r:Requirement)
WHERE NOT (r)<-[:VALIDATES_REQ|ADDRESSES]-(:Test)
RETURN r.id as untested_requirement
```

### 3.3 仪表盘展示
在 `ArchitectureLabPage` (/architecture-lab) 页面中：
-   实时拉取 Neo4j 的覆盖率统计。
-   红色标记未被测试覆盖的设计节点。
-   绿色标记已完成“业务串联测试”的节点。

---

## 🛠️ 后续执行步骤清单
1. [ ] **完善索引脚本**: 将 `Test` 节点的识别逻辑加入 `index_architecture.py`。
2. [ ] **开发审计工具**: 编写 `audit_architecture_coverage.py` 输出未测清单。
3. [ ] **集成前端**: 在 `/architecture-lab` 页面增加“图谱覆盖率”统计卡片。
4. [ ] **建立闭环**: 要求每次 PR 提交前，必须运行索引脚本并确保“业务节点覆盖率”没有下降。
