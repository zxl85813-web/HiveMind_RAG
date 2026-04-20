# HiveMind 知识图谱使用手册

> **版本**: 1.0 | **最后更新**: 2026-04-15  
> **图谱规模**: ~8000+ 节点 | ~12000+ 关系 | 10 个索引阶段 | 29 个索引方法

---

## 1. 概述

HiveMind 知识图谱是基于 Neo4j 的**系统认知图谱**，它将代码、架构、业务流程、数据模型、Agent 拓扑、可观测性、状态机、配置依赖、治理门禁和测试覆盖统一连接在一张图中。

### 核心价值

| 场景 | 图谱能回答的问题 |
|---|---|
| **变更影响分析** | "改了这个文件/配置/表，会影响哪些功能？" |
| **全链路追溯** | "用户点击按钮后，经过哪些 API、写了哪些表、触发了什么事件？" |
| **测试驱动** | "哪些 API 没有测试覆盖？这个状态转换有没有被测到？" |
| **故障影响** | "Redis 挂了，哪些事件会丢失？哪些功能会降级？" |
| **权限审计** | "user 角色能访问哪些页面？这个 API 需要什么权限？" |
| **架构理解** | "Swarm 的 LangGraph 拓扑是什么？Agent 有哪些工具？" |

---

## 2. 图谱架构

### 2.1 索引阶段

```
Phase 1: 结构索引       — Requirements, Designs, Files, AST, TODO
Phase 2: 工程流程       — GitHub PRs, Reviews, Releases
Phase 3: 派生智能       — Code Similarity, Developer Profiles
Phase 4: 业务流程       — Pages, Navigation, Access Control, Business Flows
Phase 5: 数据模型+API   — DB Tables, API Endpoints
Phase 6: Agent+Pipeline — Swarm Topology, Tools, Skills, LLM Tiers, Artifacts
Phase 7: 可观测性+事件   — Trace Types, Event Channels
Phase 8: 状态机         — 14 State Machines, 76 Transitions
Phase 9: 运维+治理+测试  — Config, External Services, Migrations, Gates, Tests
Phase 10: 测试完备性    — E2E Test Flows, API Schemas
Phase 11: 业务流定义    — Business Flow Definitions (YAML), Error Paths
Phase 12: 技术债识别    — Tech Debt (Mocks, Stubs, TODOs)
```

### 2.2 节点类型总览（~45 种）

| 层 | 节点类型 | 说明 |
|---|---|---|
| **代码结构** | `File`, `CodeEntity`, `UIElement`, `UI_State`, `UI_Store` | 源代码文件和 AST 结构 |
| **架构追溯** | `Requirement`, `Design`, `Commit`, `Person`, `Todo` | 需求-设计-代码追溯链 |
| **工程流程** | `PullRequest`, `Review`, `Release`, `DeveloperProfile` | GitHub 工程流程 |
| **业务流程** | `Page`, `Permission`, `Role`, `UserAction`, `BusinessFlow` | 前端页面和导航 |
| **数据模型** | `DBTable`, `DBColumn` | PostgreSQL 表结构 |
| **API 层** | `APIEndpoint`, `APISchema`, `SchemaField` | FastAPI 路由端点和请求/响应结构 |
| **Agent 系统** | `SwarmNode`, `NativeTool`, `SkillDef`, `LLMTier` | Swarm 拓扑和工具 |
| **Pipeline** | `PipelineStage`, `ArtifactType` | 批处理流水线 |
| **可观测性** | `TraceType`, `EventChannel`, `EventType` | 追踪和事件总线 |
| **状态机** | `StateMachine`, `EntityState` | 实体状态和转换 |
| **运维** | `ConfigKey`, `ExternalService`, `Migration` | 配置和外部依赖 |
| **治理** | `GateRule` | 权限、熔断器、限流器、质量门禁 |
| **测试** | `TestFile`, `TestFlow`, `TestStep` | 测试文件、E2E 流程和检查点 |
| **业务流** | `BusinessFlow`, `FlowStep`, `ErrorPath` | 从 YAML 定义的业务流程 |
| **技术债** | `TechDebt` | 扫描到的 Mock、Stub 和待办项 |

### 2.3 关系类型总览（~60 种）

<details>
<summary>点击展开完整关系列表</summary>

| 类别 | 关系 | 方向 |
|---|---|---|
| 代码依赖 | `CONTAINS`, `CALLS`, `DEPENDS_ON`, `DEFINES_COMPONENT`, `RENDERS` | File/CodeEntity 之间 |
| 架构追溯 | `ADDRESSES`, `IMPLEMENTED_BY`, `COMMITTED`, `AUTHORED_BY`, `MODIFIED` | Design/Requirement/File |
| 代码质量 | `SIMILAR_TO` | File/CodeEntity 之间 |
| 工程流程 | `AUTHORED_PR`, `HAS_REVIEW`, `REVIEWED`, `MODIFIES`, `INCLUDES_PR`, `PUBLISHED`, `HAS_PROFILE` | Person/PR/Release |
| 业务流程 | `NAVIGATES_TO`, `HAS_AI_ACTION`, `HAS_ACTION`, `REQUIRES_PERMISSION`, `GRANTS`, `CONTAINS_STEP` | Page/Role/Permission |
| 数据模型 | `DEFINES_MODEL`, `HAS_COLUMN`, `FOREIGN_KEY` | File/DBTable/DBColumn |
| API | `HANDLED_BY`, `OPERATES_ON`, `CALLS_API`, `GUARDED_BY` | APIEndpoint/File/DBTable/GateRule |
| Agent | `ROUTES_TO`, `USES_LLM`, `CONFIGURES`, `FEEDS_INTO` | SwarmNode/LLMTier |
| 可观测性 | `STORED_IN`, `HAS_SPAN_TYPE`, `EMITS_TRACE`, `PRODUCES_TRACE` | TraceType/DBTable/File |
| 事件总线 | `CARRIES`, `PUBLISHES_TO`, `SUBSCRIBES_TO`, `BACKED_BY` | EventChannel/EventType/File |
| 状态机 | `HAS_STATE_MACHINE`, `HAS_STATE`, `INITIAL_STATE`, `TRANSITIONS_TO` | DBTable/StateMachine/EntityState |
| 运维 | `DEPENDS_ON_CONFIG`, `CONFIGURED_BY`, `HOSTED_ON`, `DEPENDS_ON_MIGRATION`, `MODIFIES_TABLE` | File/ConfigKey/ExternalService |
| 治理 | `PROTECTS`, `IMPLEMENTS_GATE` | GateRule/ExternalService/File |
| **测试** | `COVERS_ENDPOINT`, `COVERS_PAGE`, `TESTS_STATE`, `IS_TEST` | TestFile/APIEndpoint/Page |
| **业务流** | `CONTAINS_STEP`, `HAS_ERROR_PATH` | BusinessFlow 组成部分 |
| **技术债** | `HAS_DEBT`, `AFFECTED_BY_DEBT` | File/API/Flow 与 TechDebt 关联 |

</details>

---

## 3. 运行索引

### 3.1 前置条件

- Neo4j 数据库运行中
- Python 虚拟环境已激活
- `backend/.env` 中配置了 `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- （可选）`GITHUB_TOKEN` + `GITHUB_REPO_OWNER` + `GITHUB_REPO_NAME` 用于 PR/Release 索引

### 3.2 运行完整索引

```bash
# 使用 skills/ 版本（推荐，无 tree-sitter 依赖）
cd <project_root>
python skills/architectural-mapping/scripts/index_architecture.py

# 或使用 .agent/ 版本（需要 tree-sitter-typescript）
python .agent/skills/architectural-mapping/scripts/index_architecture.py
```

### 3.3 运行单个阶段

```python
from index_architecture import ArchitectureIndexer

indexer = ArchitectureIndexer(uri, user, password)

# 只跑状态机
indexer.index_state_machines()

# 只跑 API 端点
indexer.index_api_endpoints()

# 只跑治理门禁
indexer.index_governance_gates()

indexer.close()
```

### 3.4 索引耗时参考

| 阶段 | 耗时（远程 Neo4j） |
|---|---|
| Phase 1-4 | ~3 分钟 |
| Phase 5 (DB + API) | ~1 分钟 |
| Phase 6-7 | ~30 秒 |
| Phase 8 (状态机) | ~45 秒 |
| Phase 9 (配置+门禁+测试) | ~2 分钟 |
| **总计** | **~7 分钟** |

---

## 4. 常用查询手册

### 4.1 全链路追溯

```cypher
-- 知识库页面的完整 API 链路
MATCH (pg:Page {path: '/knowledge'})
WITH pg
MATCH (ep:APIEndpoint) WHERE ep.module = 'knowledge'
OPTIONAL MATCH (ep)-[:OPERATES_ON]->(t:DBTable)
RETURN ep.method AS method, ep.path AS api, collect(DISTINCT t.table_name) AS tables
ORDER BY ep.path
```

```cypher
-- 从前端页面到数据库状态变更的完整链路
MATCH (pg:Page)-[:NAVIGATES_TO]->(target:Page)
WHERE pg.path = '/'
WITH target
MATCH (ep:APIEndpoint) WHERE ep.module = target.key
OPTIONAL MATCH (ep)-[:OPERATES_ON]->(t:DBTable)-[:HAS_STATE_MACHINE]->(sm:StateMachine)
OPTIONAL MATCH (sm)-[:INITIAL_STATE]->(init:EntityState)
RETURN target.path, ep.method, ep.path, t.table_name, sm.name, init.value
```

### 4.2 状态机查询

```cypher
-- 某个实体的所有合法状态转换
MATCH (sm:StateMachine {entity: 'KnowledgeBaseDocumentLink'})-[:HAS_STATE]->(s:EntityState)
OPTIONAL MATCH (s)-[t:TRANSITIONS_TO]->(next:EntityState)
RETURN s.value AS from_state, t.trigger AS trigger, next.value AS to_state
ORDER BY s.value

-- 找出所有终态（无出边的状态）
MATCH (sm:StateMachine)-[:HAS_STATE]->(s:EntityState)
WHERE s.is_terminal = true
RETURN sm.name AS machine, s.value AS terminal_state

-- 检测非法转换（两个状态之间没有定义转换）
MATCH (sm:StateMachine {id: 'SM:kb_document_link'})-[:HAS_STATE]->(a:EntityState)
MATCH (sm)-[:HAS_STATE]->(b:EntityState)
WHERE a <> b AND NOT (a)-[:TRANSITIONS_TO]->(b)
RETURN a.value AS from, b.value AS to
```

### 4.3 测试覆盖分析

```cypher
-- 没有测试覆盖的写操作 API（测试盲区）
MATCH (ep:APIEndpoint)
WHERE ep.method IN ['POST','PUT','DELETE']
  AND NOT EXISTS { MATCH (:TestFile)-[:COVERS_ENDPOINT]->(ep) }
RETURN ep.method, ep.path
ORDER BY ep.path

-- E2E 测试覆盖了哪些页面
MATCH (t:TestFile)-[:COVERS_PAGE]->(pg:Page)
RETURN t.name AS test, pg.path AS page

-- 哪些页面没有 E2E 覆盖
MATCH (pg:Page)
WHERE pg.show_in_menu = true
  AND NOT EXISTS { MATCH (:TestFile)-[:COVERS_PAGE]->(pg) }
RETURN pg.path, pg.category
```

### 4.4 权限与门禁

```cypher
-- 某个角色能访问哪些页面
MATCH (role:Role {id: 'admin'})-[:GRANTS]->(perm:Permission)<-[:REQUIRES_PERMISSION]-(pg:Page)
RETURN pg.path, perm.name

-- 某个角色不能访问的页面
MATCH (pg:Page)-[:REQUIRES_PERMISSION]->(perm:Permission)
WHERE NOT EXISTS { MATCH (:Role {id: 'user'})-[:GRANTS]->(perm) }
RETURN pg.path, perm.name

-- API 端点的权限守卫
MATCH (ep:APIEndpoint)-[:GUARDED_BY]->(g:GateRule)
WHERE ep.module = 'knowledge'
RETURN ep.method, ep.path, g.value AS permission

-- 所有熔断器及其保护的服务
MATCH (g:GateRule {gate_type: 'circuit_breaker'})-[:PROTECTS]->(svc:ExternalService)
RETURN g.name, svc.name
```

### 4.5 故障影响分析

```cypher
-- Redis 断连的爆炸半径
MATCH (svc:ExternalService {name: 'Redis'})
OPTIONAL MATCH (ch:EventChannel)-[:BACKED_BY]->(svc)
OPTIONAL MATCH (ch)-[:CARRIES]->(evt:EventType)
OPTIONAL MATCH (f:File)-[:PUBLISHES_TO]->(ch)
RETURN collect(DISTINCT ch.name) AS channels,
       collect(DISTINCT evt.name) AS events_lost,
       collect(DISTINCT f.id) AS publishers_affected

-- 改某个配置项影响哪些文件
MATCH (c:ConfigKey {name: 'LLM_API_KEY'})<-[:DEPENDS_ON_CONFIG]-(f:File)
RETURN f.id AS affected_file

-- 某个外部服务的完整依赖链
MATCH (svc:ExternalService {name: 'Elasticsearch'})
OPTIONAL MATCH (svc)<-[:PROTECTS]-(cb:GateRule)
OPTIONAL MATCH (svc)<-[:CONFIGURED_BY]-(c:ConfigKey)<-[:DEPENDS_ON_CONFIG]-(f:File)
RETURN cb.name AS circuit_breaker, collect(DISTINCT f.id) AS dependent_files
```

### 4.6 数据库 ER 查询

```cypher
-- 某张表的完整外键关联
MATCH (t:DBTable {table_name: 'knowledge_bases'})-[r:FOREIGN_KEY]-(related:DBTable)
RETURN t.table_name, type(r), related.table_name, r.source_column

-- 被最多 API 操作的表（代码热点）
MATCH (ep:APIEndpoint)-[:OPERATES_ON]->(t:DBTable)
RETURN t.table_name, count(ep) AS api_count
ORDER BY api_count DESC LIMIT 10

-- 某张表的所有列
MATCH (t:DBTable {table_name: 'documents'})-[:HAS_COLUMN]->(c:DBColumn)
RETURN c.name, c.col_type, c.is_primary_key, c.is_index
ORDER BY c.is_primary_key DESC, c.name
```

### 4.7 Agent/Swarm 查询

```cypher
-- Swarm LangGraph 拓扑
MATCH (sn:SwarmNode)
OPTIONAL MATCH (sn)-[:ROUTES_TO]->(target)
RETURN sn.name, sn.is_entry_point, collect(target.name) AS routes_to

-- Agent 可用工具清单
MATCH (t:NativeTool)
RETURN t.name, t.description

-- 技能包列表
MATCH (s:SkillDef)
RETURN s.name, s.description, s.version, s.has_tools
```

### 4.8 业务流程查询

```cypher
-- 预定义的业务流程
MATCH (bf:BusinessFlow)-[s:CONTAINS_STEP]->(pg:Page)
RETURN bf.name AS flow, pg.path AS step, s.seq AS seq
ORDER BY bf.name, s.seq

-- 从某个页面出发的所有导航路径
MATCH path = (start:Page {path: '/knowledge'})-[:NAVIGATES_TO*1..3]->(target:Page)
RETURN [n IN nodes(path) | n.path] AS flow
```

---

## 5. 全流程测试生成指南

### 5.1 用图谱生成测试骨架

以"知识库全生命周期"为例，通过图谱查询自动生成测试步骤：

```cypher
-- Step 1: 获取业务流程步骤
MATCH (bf:BusinessFlow {name: '知识库生命周期'})-[s:CONTAINS_STEP]->(pg:Page)
RETURN pg.path AS step, s.seq AS order
ORDER BY s.seq

-- Step 2: 获取每个步骤涉及的 API
MATCH (bf:BusinessFlow {name: '知识库生命周期'})-[s:CONTAINS_STEP]->(pg:Page)
WITH pg, s.seq AS seq
MATCH (ep:APIEndpoint) WHERE ep.module = pg.key AND ep.method IN ['POST','PUT','DELETE']
RETURN seq, pg.path, ep.method, ep.path
ORDER BY seq

-- Step 3: 获取每个 API 的状态变更
MATCH (ep:APIEndpoint)-[:OPERATES_ON]->(t:DBTable)-[:HAS_STATE_MACHINE]->(sm:StateMachine)
WHERE ep.module = 'knowledge'
MATCH (sm)-[:HAS_STATE]->(s:EntityState)-[tr:TRANSITIONS_TO]->(next:EntityState)
RETURN ep.path, sm.entity, s.value AS before, tr.trigger, next.value AS after

-- Step 4: 获取权限要求
MATCH (ep:APIEndpoint)-[:GUARDED_BY]->(g:GateRule)
WHERE ep.module = 'knowledge'
RETURN ep.method, ep.path, g.value AS required_permission
```

### 5.2 测试用例模板

基于图谱查询结果，可以自动生成如下测试骨架：

```python
# 自动生成的测试骨架（基于图谱）
class TestKnowledgeBaseLifecycle:
    """
    业务流程: 知识库生命周期
    步骤: / → /knowledge → /evaluation → /kb-analytics
    """

    async def test_step1_create_kb(self):
        """POST /api/v1/knowledge → writes knowledge_bases, kb_permissions"""
        # 权限: kb:create
        # 前置: 用户已登录
        # 断言: response.status == 200, knowledge_bases 新增一行

    async def test_step2_upload_document(self):
        """POST /api/v1/knowledge/documents → writes documents (status=pending)"""
        # 权限: kb:upload
        # 前置: KB 已创建
        # 断言: documents.status == 'pending'

    async def test_step3_link_and_index(self):
        """POST /api/v1/knowledge/{kb_id}/documents/{doc_id}"""
        # 状态转换: pending → processing → indexed
        # 事件: document_linked → Redis
        # 断言: knowledge_base_documents.status == 'indexed'

    async def test_step3_low_confidence(self):
        """异常路径: 低置信度 → pending_review"""
        # 状态转换: processing → pending_review
        # 断言: obs_hitl_tasks 新增一行

    async def test_step4_search(self):
        """POST /api/v1/knowledge/{kb_id}/search"""
        # 前置: 文档已 indexed
        # 断言: 返回相关结果
```

---

## 6. 14 个状态机速查表

| 状态机 | 实体 | 状态 | 初始 → 终态 |
|---|---|---|---|
| KB Document Link | KnowledgeBaseDocumentLink | pending, processing, indexed, pending_review, failed | pending → indexed/failed |
| Document | Document | pending, processing, parsed, failed, stale | pending → parsed/failed |
| File Trace | FileTrace | pending, running, success, failed, pending_review, approved, rejected | pending → success/failed |
| Bad Case | BadCase | pending, reviewed, fixed, added_to_dataset | pending → added_to_dataset |
| Eval Report | EvaluationReport | pending, running, completed, failed | pending → completed/failed |
| Cognitive Directive | CognitiveDirective | pending, approved, rejected | pending → approved/rejected |
| Prompt Definition | PromptDefinition | draft, active, deprecated, rollback | draft → active → deprecated |
| Sync Task | SyncTask | idle, running, error | idle → idle (循环) |
| Document Review | DocumentReview | pending, approved, rejected, needs_revision | pending → approved/rejected |
| Fine-tuning Item | FineTuningItem | pending_review, verified, exported | pending_review → exported |
| Swarm Todo | TodoItem | pending, in_progress, waiting_user, completed, cancelled | pending → completed/cancelled |
| Batch Task | TaskUnit | pending, queued, running, success, failed, cancelled, retry_wait | pending → success/failed |
| Batch Job | BatchJob | created, running, completed, partial, failed, cancelled | created → completed/failed |
| Agent Worker | AgentWorker | idle, planning, executing, reflecting, done, failed | idle → done/failed |

---

## 7. 外部服务依赖图

```
PostgreSQL ← 39 张表 ← 所有 CRUD API
Redis ← WriteEventBus + Blackboard + Celery
Neo4j ← 知识图谱 + 图谱检索步骤
Elasticsearch ← 向量检索 + BM25 混合搜索
SiliconFlow ← 主 LLM 提供商 (DeepSeek V3)
Moonshot/Kimi ← 推理模型 (kimi-k2.5)
Volcengine ARK ← 备用 LLM
Zhipu ← Embedding 模型
GitHub API ← 学习服务 + Issue 同步
Celery ← 异步文档索引任务
```

每个外部服务都有对应的 `ConfigKey` 和（部分有）`GateRule` 熔断器保护。

---

## 8. 治理门禁清单

### 权限门禁（11 个）
`chat:send`, `chat:view`, `chat:delete`, `kb:create`, `kb:view`, `kb:delete`, `kb:upload`, `agent:view`, `agent:config`, `user:manage`, `system:config`, `audit:view`

### 熔断器（5 个）
- LLM Circuit Breaker → 保护 SiliconFlow
- ES Circuit Breaker → 保护 Elasticsearch
- Neo4j Circuit Breaker → 保护 Neo4j
- Swarm Ingestion CB → 保护文档索引流程
- RAG Gateway CB → 保护检索网关

### 限流器（4 个）
- API: 60 req/min（全局）
- Chat: 20 req/min（LLM 调用）
- Upload: 10 req/min（文件上传）
- Governance: per-route 动态限流

### 质量门禁（4 个）
- L3 Intelligence Gate: Agent 质量分 ≥ 0.60
- L4 Process Integrity Gate: 审计链完整性
- HMER Phase Gate: 架构演进阶段准出
- L5 Scoping Gate: 查询范围评估

---

## 9. 维护与更新

### 增量更新
索引器支持增量模式（MERGE 语义），重复运行不会产生重复数据。建议在以下时机重新运行：

- 新增/修改了 API 路由
- 新增/修改了数据库模型
- 新增了前端页面或导航
- 修改了状态转换逻辑
- 新增了测试文件

### 清理重建
```cypher
-- 清除所有架构节点（保留 Tier-2 动态提取的实体）
MATCH (n:ArchNode) DETACH DELETE n
```

### 健康检查
```cypher
-- 检查图谱完整性
MATCH (n) WITH labels(n) AS lbls UNWIND lbls AS lbl
RETURN lbl, count(*) AS cnt ORDER BY cnt DESC

-- 检查孤岛节点（没有任何关系的节点）
MATCH (n:ArchNode) WHERE NOT (n)--() RETURN labels(n), count(n)
```
