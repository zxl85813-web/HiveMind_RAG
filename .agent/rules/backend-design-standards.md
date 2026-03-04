# ⚙️ 后端模块设计规范 (Backend Module Design Standards)

> 关联文档: [`.agent/rules/project-structure.md`](project-structure.md) (宏观目录划分)

在 FastAPI + SQLModel 体系下，如何写好一个具体的后端模块（Service、API、Util），必须遵守本微观设计规范。

---

## 0. 已确认的架构级决策 (Architecture Decisions)

以下是本项目经过讨论已经确认的架构方向，**不得随意更改**，如需调整必须提 ADR：

| 决策主题 | 已确认方案 | 备注 |
|---|---|---|
| 用户体系 | 单组织 (Single-Org) | 不做多租户 SaaS，无需 `org_id` |
| ID 策略 | UUID4 (Python 层生成) | 全表统一，禁止自增 Int |
| 软删除 | 全局软删除 (`is_deleted`) | 所有核心业务表必须有此字段 |
| 时间戳 | Python 层处理 + SQLAlchemy Event Hook | `updated_at` 自动维护，不依赖 DB dialect |
| 审计字段 | `created_by` / `updated_by` 必填 | API 层从 `current_user` 注入 |
| 异步任务 | FastAPI `BackgroundTasks` (近期) | 量大后迁移至 ARQ (Redis) |
| 记忆体系 | 三层分级 + 渐进式归纳 | 见下方"记忆架构"章节 |

---

## 1. 后端五层流水线架构 (5-Layer Pipeline)

所有代码必须严格属于以下其中一层，禁止跨层污染：

| 层级 | 目录 | 职责 | 输入 | 输出 |
|---|---|---|---|---|
| **路由层** | `api/routes/` | 接收请求、做参数初验、调 Service | Pydantic Schema | `ApiResponse` |
| **服务层** | `services/` | 核心业务逻辑、跨模块编排 | 原子参数 | ORM Model |
| **智能层** | `agents/`, `rag/` | LLM 推理、向量检索 | 业务 Context | 结构化结果 |
| **基础设施层** | `core/`, `auth/` | DB 连接、JWT 校验、配置 | 系统级调用 | 资源句柄 |
| **数据层** | `models/`, `schemas/` | ORM 映射、API 契约 | 字段定义 | 行记录 / JSON |

### 模块调用边界（违反下表的代码将在 Review 中被 Reject）

| 模块 | 可以调用 | 禁止调用 |
|---|---|---|
| `api/routes/` | `services/`, `auth/`, `schemas/`, `common/` | `agents/`, `models/`, `llm/` 直接 |
| `services/` | `agents/`, `auth/`, `audit/`, `models/`, `common/` | `api/` |
| `agents/` | `llm/`, `memory/`, `rag/`, `mcp/`, `skills/` | `api/`, `services/` |
| `auth/` | `models/`, `core/`, `common/` | `agents/`, `services/` |
| `common/` | `core/` 仅 | 任何业务模块 |
| `core/` | 无外部依赖 | — |

---

## 2. 函数命名规范 (Naming Conventions)

Service 方法名必须遵守动词前缀约定，方便 AI 和人类快速理解意图：

| 操作 | 方法名前缀 | 示例 |
|---|---|---|
| 获取单个 | `get_` | `get_knowledge_base(kb_id)` |
| 获取列表 | `list_` | `list_documents(kb_id, page)` |
| 创建 | `create_` | `create_document(...)` |
| 修改 | `update_` | `update_document_meta(...)` |
| 软删除 | `remove_` | `remove_knowledge_base(kb_id)` |
| 内部校验 | `_check_` / `_validate_` | `_check_kb_access(user_id, kb_id)` |
| 内部构建 | `_build_` | `_build_retrieval_context(...)` |

---

## 3. Controller / Route 层职责

`api/routes/xxx.py` 是控制层，**绝对不允许包含复杂的业务逻辑**。

### 3.1 职责边界
- **做**: 解析参数、检查基础权限、调用 Service 方法、将返回值包装为 `ApiResponse`、抛出适当的 HTTP 状态。
- **不做**: 拼接复杂 SQL、调用外部大模型、组装复杂的数据结构。

### 3.2 依赖注入原则
强制使用 `Depends` 注入数据会话 (Session) 和业务服务 (Service)，方便未来的单元测试 Mock 替换。

```python
# ✅ 正确示范
@router.post("/", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends()
):
    try:
        user = await user_service.create_user(session, request, created_by=current_user.id)
        return ApiResponse.success(data=user)
    except UserAlreadyExistsError as e:
        raise AppException(code=40001, message=str(e), status_code=400)
```

---

## 4. Service 层设计模式

`services/` 是业务的核心执行层。

### 4.1 依赖与传参
- **数据库 Session**: 必须通过方法参数显式传入，不要在 Service 内部强绑定全局 Session。
- **审计字段**: `create_xxx` 和 `update_xxx` 方法必须接受 `created_by` / `updated_by` 参数，并写入模型字段。
- **Service 聚合**: A Service 需要调用 B Service 时，通过 `__init__` 构造函数注入，避免循环依赖。

### 4.2 Service 返回 Model，Route 负责转换 Schema
- **规则**: Service 返回 ORM Model 对象，由 Route 层负责序列化为 Schema/ApiResponse。
- **理由**: 返回 Model 允许后续调用者继续使用关联数据 (Lazy Load)。

### 4.3 事务控制 (Transaction boundaries)
- 底层写入方法只做 `session.add(obj)` 和 `session.flush()`。
- 最外层的 Service 方法负责执行 `session.commit()`，保证事务原子性。

### 4.4 异步任务触发
- 耗时的副作用 (如文档向量化、记忆归纳) 在 Service 方法中**不能同步执行**。
- 必须使用 `BackgroundTasks.add_task(...)` 投递到后台，让 HTTP 立即返回 `202 Accepted`。

---

## 5. 分层记忆架构 (Layered Memory System)

> 记忆是 RAG 系统的核心竞争力。记忆的内部状态对用户不可见，但会主动暴露产出价值。

### 5.0 实际存储栈（从代码得出，非假设）

| 存储目的 | 生产环境 | 本地开发 | 测试 |
|---|---|---|---|
| 关系数据 (用户/知识库/会话) | **PostgreSQL** | SQLite | SQLite in-memory |
| 向量存储 (语义检索) | **Elasticsearch 8.x** (kNN dense_vector + BM25 Hybrid) | **ChromaDB** (轻量) | MockVectorStore |
| 知识图谱 | **Neo4j** | 同左 | 同左 |
| 工作记忆 | **Redis** (TTL 管理，计划迁移) | Python dict | Python dict |
| Embedding 提供商 | **智谱 AI (embedding-3, 2048维)** | 同左 | Mock |

> **重要**: `core/vector_store.py` 中已实现统一抽象接口 `BaseVectorStore`，所有对向量存储的调用**必须通过 `get_vector_store()` 工厂方法**获取实例，禁止直接实例化 `ElasticVectorStore` 或 `ChromaVectorStore`。

### 5.1 三层记忆结构

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1: Working Memory — 工作记忆                              │
│  存储: Python dict (现阶段) / Redis TTL (生产升级目标)            │
│  scope: 单次会话生命周期                                          │
│  内容: 当前 Context Window + Agent 临时推理状态                   │
└──────────┬──────────────────────────┬────────────────────────────┘
           │ 会话结束 →               │ 实时产出 (用户可见 API)
           ▼ BackgroundTask           ▼
┌───────────────────────────┐   ┌────────────────────────────────┐
│ LAYER 2: Episodic Memory  │   │  📤 Session Insights API       │
│ 情景记忆                   │   │  GET /api/v1/sessions/{id}/insights│
│ 存储: PostgreSQL (摘要)    │   │  ├── proposed_kb_entries (待入库)│
│       + ES (向量索引)      │   │  ├── extracted_todos (行动清单)  │
│ 每会话 → LLM归纳摘要 →     │   │  └── key_conclusions (结论摘要) │
│ 打分类标签入库             │   └────────────────────────────────┘
└──────────┬────────────────┘
           │ 积累到阈值 → 渐进式批量归纳
           ▼ BackgroundTask (阈值触发 / 定时调度)
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 3: Semantic Memory — 语义记忆                             │
│  存储: Elasticsearch 8.x (production) / ChromaDB (local)        │
│  collection: memory_semantic_<user_id>                          │
│  内容: 从情景记忆精炼的通用知识, 自动提议注入知识库              │
│  检索策略: 分层检索 Working → Episodic → Semantic               │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 记忆归纳原则 (Distillation Rules)
- **小归纳 (会话级)**: 对话结束 → `BackgroundTask` → LLM 生成摘要 → 分类打标签 → 存入情景记忆。
- **大总结 (批量级)**: 情景记忆条数超过阈值（如 50 条） → 渐进式批量归纳 → 提炼知识注入语义记忆。
- **知识提议**: 归纳出的知识不直接写入知识库，而是进入"待确认"队列，通过 `proposed_kb_entries` API 暴露，由用户确认后才正式入库。
- **TODO 提取**: 对话中出现的计划、承诺、行动项，由 Agent 抽取并存入 `SharedMemoryManager._todos`，通过 `GET /api/v1/memory/todos` 暴露。

### 5.3 `SharedMemoryManager` 当前状态与开发方向
- 已有框架 (`memory/manager.py`)，多数方法为 `TODO` 占位符。
- 实现时按以下顺序优先:
  1. `store_episode` + `recall_episodes` (情景记忆的核心)
  2. `add_todo` 持久化到 PostgreSQL (当前仅存内存)
  3. `learn` + `recall_knowledge` (语义记忆，依赖向量存储)
  4. Working Memory → Redis 迁移 (Redis 到位后再做)

---

## 6. 异常处理 (Exception Handling)

不要在 Service 中返回 tuple 或特殊字符串来表示错误。

### 6.1 异常的层次
在 `app.core.exceptions` 下建立应用的自定义异常基类：
```python
class DocumentTooLargeError(Exception):
    pass

class UnauthorizedKnowledgeAccessError(Exception):
    pass
```

### 6.2 向上冒泡与转换
```python
# main.py 中的全局处理器
@app.exception_handler(DocumentTooLargeError)
async def doc_large_handler(request, exc):
    return JSONResponse(
        status_code=413,
        content={"success": False, "code": 41300, "message": "Document exceeds 50MB"}
    )
```

---

## 7. 日志记录原则 (Logging)

统一使用 `loguru.logger`，绝对禁止使用 `print()` 或原生的 `logging`。
- **INFO**: 重要业务节点（"用户 {user_id} 开始索引文档 {doc_id}"）。
- **WARNING**: 可恢复的异常，如调用外部 API 超时但成功重试。
- **ERROR**: 必须配合 `logger.exception("...")` 使用，自动记录完整 Traceback。
- **DEBUG**: 函数入参、SQL 片段（生产环境默认关闭）。

每条日志应包含关联上下文，便于追踪（例如 `request_id`, `user_id`）。

---

## 8. 设计文档 (DES-NNN) 编写强制项
在书写后端改造的设计文档时，必须明确写出：
1. **层级归属**: 新代码属于哪一层（Route / Service / Agent）？
2. **依赖关系图**: 新 Service 会调用哪些现有模块？
3. **异步边界**: 哪些操作是 BackgroundTask？会触发记忆归纳吗？
4. **例外清单**: 会抛出哪些自定义 Exception？

---

> 💡 **可扩展性与规则豁免**:
> 本文档定义的是标准场景下的通用规范。如果在极其特殊的业务或性能要求下必须突破这些规则，请参见 [`design-and-implementation-methodology.md`](design-and-implementation-methodology.md) 中的"特例豁免机制"。
