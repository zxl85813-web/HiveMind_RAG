---
description: Neo4j 图谱开发规范 — 编辑图谱相关文件时自动加载
inclusion: fileMatch
fileMatchPattern: "**/graph_store.py,**/graph_index.py,**/graph_*.py,**/index_architecture.py,**/graph_health_check.py,**/sync_*_to_graph.py,**/assembler.py,**/event_subscribers.py"
---

# Neo4j 知识图谱开发规范

编辑图谱相关代码时，必须遵守以下规范。

## 图谱架构手册（完整参考）
#[[file:docs/architecture/KNOWLEDGE_GRAPH_MANUAL.md]]

## 图谱数据流转
#[[file:docs/architecture/neo4j_data_flow.md]]

## 图谱驱动治理
#[[file:docs/architecture/DEC-005-GRAPH_DRIVEN_GOVERNANCE.md]]

## 核心约束速查

### 连接与访问
- 统一通过 `get_graph_store()` 工厂方法获取 `Neo4jStore` 实例，禁止直接实例化
- 配置项: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`（从 `app.sdk.core.config.settings` 读取）
- Neo4j 不可用时所有方法必须静默降级返回空，不得干扰主业务

### 异步安全
- 所有 Neo4j 阻塞调用必须用 `run_in_executor` 包裹，禁止在 async 函数中直接调用同步驱动
- 优先使用 `AsyncGraphDatabase` 异步驱动（`backend/app/sdk/core/graph_store.py`）

### 图谱本体（四大核心域）
- 🟢 **IntelligenceNode（智体域）**: Agent, Skill, Supervisor — 记录"谁在做"
- 🔵 **CognitiveAsset（资源域）**: Requirement, Design, Doc — 记录"根据什么做"
- 📜 **CodePrimitive（代码域）**: Class, Method, Component — 记录"改了什么代码"
- 📊 **MetricNode（度量域）**: HMER 得分, 质量探针 — 记录"做得好不好"

### 节点写入规范
- 所有节点必须有 `id` 字段（唯一标识）
- 写入时必须注入元数据: `path`（来源路径）和 `created_at`（时间戳）
- 使用 `MERGE` 而非 `CREATE` 防止重复节点
- 新增节点类型必须先更新 `KNOWLEDGE_GRAPH_MANUAL.md` 的节点类型总览

### 关系写入规范
- 关系类型使用 `UPPER_SNAKE_CASE`（如 `DEPENDS_ON`, `MAPPED_TO_CODE`）
- 新增关系类型必须先更新 `KNOWLEDGE_GRAPH_MANUAL.md` 的关系类型总览
- 关系必须携带 `description` 属性说明语义

### 索引阶段（12 阶段体系）
新增索引逻辑必须归入已有的 12 个阶段之一，禁止随意新建阶段：
1. 结构索引 | 2. 工程流程 | 3. 派生智能 | 4. 业务流程
5. 数据模型+API | 6. Agent+Pipeline | 7. 可观测性+事件 | 8. 状态机
9. 运维+治理+测试 | 10. 测试完备性 | 11. 业务流定义 | 12. 技术债识别

### 记忆分层（Tier-2 图谱层）
- Tier-2 `GraphIndex` 负责从文本提取实体三元组写入 Neo4j
- 提取使用 LLM 生成 JSON（nodes + edges），再调用 `import_subgraph` 批量写入
- 查询使用 `get_neighborhood()` 做 1 跳关系跳跃，返回自然语言描述

### Harness 图谱集成（M8）
- `:HarnessPolicy` 节点通过 `GOVERNED_BY` 关联到 `SwarmNode`
- `:HarnessCheck` 节点通过 `CHECKED_BY` / `ENFORCED_BY` 记录检查链路
- Feedforward 规则从图谱加载注入 system prompt
- Steering Loop 从高频失败自动生成新约束
