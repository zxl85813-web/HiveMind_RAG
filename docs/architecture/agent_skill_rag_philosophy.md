# 🧬 HiveMind RAG — Agent × Skill × RAG 架构哲学与工程设计

> **本文档是 HiveMind 整体智能架构的灵魂文件。**
> 它回答一个根本问题：如何用传统软件工程的成熟范式来驯服 AI 的不确定性？

---

## 一、核心理念三元组 (The Three Pillars)

```
┌─────────────────────────────────────────────────────────────────┐
│                    HiveMind 架构哲学三元组                        │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │  理念 1       │  │  理念 2       │  │  理念 3               │  │
│  │  纯函数/副作用 │  │  服务治理     │  │  分层架构             │  │
│  │  Skill=Pure   │  │  Data Gov    │  │  Enterprise          │  │
│  │  Agent=Effect │  │  ≈ ServiceGov│  │  Architecture        │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                  │                     │              │
│         └─── Functional ───┴─── Governance ──────┘              │
│                 Programming       Engineering                   │
└─────────────────────────────────────────────────────────────────┘
```

### 理念 1：Agent 是副作用函数，Skill 是纯函数

| 属性 | Skill (纯函数) | Agent (副作用函数) |
|------|----------------|-------------------|
| **确定性** | 给定输入 → 确定输出 | 输出取决于环境状态 |
| **副作用** | 无（不修改任何外部状态） | 有（读写 Memory、调用 API、触发流程） |
| **可测试** | 极高，单元测试友好 | 需要 Mock 环境，集成测试 |
| **可组合** | 自由组合，如管道拼接 | 需要 Orchestrator 协调 |
| **生命周期** | 无状态，随用随丢 | 有状态，需要初始化/销毁 |
| **类比** | `map`, `filter`, `reduce` | `fetch`, `fs.write`, `db.query` |

```
                    纯函数 vs 副作用函数

    Skill (Pure)                    Agent (Effect)
    ┌──────────┐                    ┌──────────────┐
    │ Input    ├───→ Deterministic  │ Input        │
    │          │     Transform ───→ │ + Context    │
    │ Output ← ┤                   │ + Memory     │
    └──────────┘                   │ + Tools      │
    No side effects                │ + LLM State  │
    ✅ Referential transparency     │ Output ← ─ ─ ┤
                                   └──────────────┘
                                   Side effects everywhere
                                   ❌ Non-deterministic
```

**工程启示：**

1. **Skill 是 Agent 的弹药库**：Agent 自身不做"计算"，它只负责**决策** (routing) 和**编排** (orchestration)，实际的数据处理能力全部封装在 Skills 中
2. **Skill 的纯度保障可测试性**：每个 Skill 模块可以脱离 Agent 独立测试，这是质量的基石
3. **Agent 的副作用被严格管理**：所有 I/O 操作（Memory 读写、LLM 调用、外部 API）都通过标准化接口进行，可被拦截、审计、Mock

### 理念 2：ARAG 数据治理 ≈ 微服务的服务治理

| 微服务治理概念 | RAG 数据治理映射 | HiveMind 实现 |
|---------------|-----------------|---------------|
| **服务注册/发现** | 知识库注册/发现 | `KnowledgeBase` 模型 + `KnowledgeBaseSelector` 路由 |
| **服务网关** | RAG Gateway | `RetrievalPipeline` — 统一检索入口 |
| **负载均衡** | 知识库路由 | 多 KB 选择器 + 查询路由 |
| **熔断器** | 检索降级 | Tier-1 Radar → Tier-2 Graph → Tier-3 Vector 级联降级 |
| **限流** | Token 预算控制 | `LLMRouter` 分级调度 |
| **链路追踪** | RAG Trace | `RetrievalContext.trace_log` + LangFuse |
| **健康检查** | KB 健康度 | M5 评估指标 (Faithfulness / Relevance) |
| **灰度发布** | Pipeline 灰度 | 可配置 Pipeline Step 组合 |
| **数据契约** | Chunk Schema | `VectorDocument` + `RetrievalContext` 协议 |
| **服务版本管理** | Pipeline 版本 | `PipelineConfig` 模板系统 |

### 理念 3：用传统分层架构驯服 AI 不确定性

```
═══════════════════════════════════════════════════════════════
                   HiveMind 六层架构
═══════════════════════════════════════════════════════════════

  ┌───────────────────────────────────────────────────────┐
  │                 L6: 交互层 (Interface)                │
  │        React UI / SSE / WebSocket / REST API          │
  │        ───── 确定性：高 ─────                          │
  └───────────────────────┬───────────────────────────────┘
                          │
  ┌───────────────────────▼───────────────────────────────┐
  │                 L5: 编排层 (Orchestration)            │
  │        SwarmOrchestrator / LangGraph StateGraph       │
  │        Supervisor → Agent → Reflection → FINISH      │
  │        ───── 确定性：中低（LLM 路由决策） ─────         │
  └───────────────────────┬───────────────────────────────┘
                          │
  ┌───────────────────────▼───────────────────────────────┐
  │                 L4: 智能层 (Intelligence)             │
  │        LLM Router / Prompt Engine / Agent Nodes       │
  │        ───── 确定性：低（LLM 推理） ─────              │
  └───────┬───────────────┼───────────────────────────────┘
          │               │
  ┌───────▼──────┐ ┌──────▼──────────────────────────────┐
  │  L3: 技能层   │ │         L3: 检索层 (Retrieval)       │
  │  (Skill)     │ │  RetrievalPipeline + Steps           │
  │  Pure Func   │ │  Query → Recall → Rerank → Expand    │
  │  ─ 确定性：  │ │  ───── 确定性：中 ─────               │
  │    高 ─────  │ └──────┬──────────────────────────────┘
  └───────┬──────┘        │
          │               │
  ┌───────▼───────────────▼───────────────────────────────┐
  │                 L2: 数据层 (Data Fabric)              │
  │  Memory Service / Knowledge Service / Indexing        │
  │  ───── 确定性：高 ─────                                │
  └───────────────────────┬───────────────────────────────┘
                          │
  ┌───────────────────────▼───────────────────────────────┐
  │                 L1: 基础设施层 (Infrastructure)       │
  │  PostgreSQL │ Redis │ ChromaDB │ Neo4j │ MinIO        │
  │  ───── 确定性：极高 ─────                              │
  └───────────────────────────────────────────────────────┘
```

---

## 二、Agent × Skill × RAG 关系模型

### 2.1 三角协作模型

```
                        ┌─────────────┐
                        │   Agent     │
                        │ (Decision   │
                        │  + Effect)  │
                        └──────┬──────┘
                    ┌──────────┼──────────┐
                    │          │          │
               调用 Skill  读写 Memory  调用 RAG
                    │          │          │
              ┌─────▼────┐  ┌──▼──┐  ┌───▼────────┐
              │  Skill    │  │ Mem │  │ RAG        │
              │ Registry  │  │ Svc │  │ Pipeline   │
              │ (纯函数库) │  │     │  │ (检索引擎) │
              └──────────┘  └─────┘  └────────────┘
                  ↕              ↕          ↕
              可独立测试     有状态管理    有状态管理
              无副作用        副作用       副作用
```

### 2.2 详细交互流程

```
用户提问
    │
    ▼
┌──────────────────────────────────────────────────────────────┐
│ L6 交互层: POST /chat/completions (SSE)                     │
└──────────────┬───────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ L5 编排层: SwarmOrchestrator.invoke_stream()                │
│                                                              │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐              │
│   │Supervisor│───→│retrieval │───→│Supervisor│              │
│   │(意图路由) │    │(拉取上下文)│    │(二次路由) │              │
│   └──────────┘    └──────────┘    └─────┬────┘              │
│                                         │                    │
│                 ┌───────────────────────┼─────────────┐      │
│                 │                       │             │      │
│           ┌─────▼────┐           ┌─────▼────┐  ┌─────▼────┐│
│           │RAG Agent │           │Code Agent│  │Web Agent ││
│           │          │           │          │  │          ││
│           └─────┬────┘           └─────┬────┘  └─────┬────┘│
│                 │                       │             │      │
│                 └───────────────────────┼─────────────┘      │
│                                         │                    │
│                                   ┌─────▼────┐              │
│                                   │Reflection│              │
│                                   │(质量自检) │              │
│                                   └──────────┘              │
└──────────────────────────────────────────────────────────────┘
               │ Agent 内部调用
               ▼
┌──────────────────────────────────────────────────────────────┐
│ L4 智能层: Agent Node 执行                                   │
│                                                              │
│   Agent 内部 ReAct 循环 (最多 3 轮):                          │
│                                                              │
│   1. LLM 推理 → 决策是否调用工具                               │
│   2. 调用 Tool（来自 Skill / MCP / Native）                   │
│   3. 获取工具结果 → 继续推理                                   │
│                                                              │
│   ┌─────────────────────────────────────────────────┐       │
│   │  可用工具池 = Native Tools                        │       │
│   │               + MCP Tools (外部系统)              │       │
│   │               + Skill Tools (纯函数能力)          │       │
│   └─────────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ L3 技能层 + 检索层 (并行存在)                                  │
│                                                              │
│  ┌─────────────────────────┐ ┌──────────────────────────┐   │
│  │    Skill Registry       │ │   Retrieval Pipeline     │   │
│  │  ┌───────┐ ┌──────────┐ │ │  ┌─────────────────────┐ │   │
│  │  │Ingest │ │Generation│ │ │  │QueryPreProcessing   │ │   │
│  │  │Skill  │ │Skill     │ │ │  │  ↓                  │ │   │
│  │  ├───────┤ ├──────────┤ │ │  │GraphRetrieval       │ │   │
│  │  │Graph  │ │MCP       │ │ │  │  ↓                  │ │   │
│  │  │Skill  │ │Builder   │ │ │  │HybridRetrieval      │ │   │
│  │  ├───────┤ ├──────────┤ │ │  │  ↓                  │ │   │
│  │  │Skill  │ │Skill     │ │ │  │AclFilter            │ │   │
│  │  │Creator│ │Creator   │ │ │  │  ↓                  │ │   │
│  │  └───────┘ └──────────┘ │ │  │Reranking            │ │   │
│  │                         │ │  │  ↓                  │ │   │
│  │  纯函数，无状态          │ │  │ParentChunkExpansion │ │   │
│  │  可独立测试              │ │  │  ↓                  │ │   │
│  └─────────────────────────┘ │  │PromptInjectionFilter│ │   │
│                              │  └─────────────────────┘ │   │
│                              └──────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ L2 数据层                                                    │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │Memory    │  │Knowledge │  │Indexing  │  │Audit     │    │
│  │Service   │  │Service   │  │Service   │  │Service   │    │
│  │(3层记忆)  │  │(KB CRUD) │  │(入库流水线)│  │(操作审计) │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
└──────────────────────────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────────────┐
│ L1 基础设施层                                                │
│                                                              │
│  PostgreSQL (结构化) │ ChromaDB (向量) │ Neo4j (图谱)         │
│  Redis (缓存/队列)   │ MinIO (对象存储) │ LangFuse (观测)     │
└──────────────────────────────────────────────────────────────┘
```

---

## 三、核心组件设计

### 3.1 Skill — 纯函数能力包

> **设计准则：Skill 必须是无状态的纯函数。任何需要状态的操作都应该委托给 Agent 执行。**

#### Skill 契约 (Contract)

```python
# 每个 Skill 工具函数必须满足：
#
# 1. 幂等性 (Idempotent)
#    同样的输入一定得到同样的输出
#
# 2. 无副作用 (No Side Effects)
#    不直接操作数据库/文件系统/网络
#
# 3. 可序列化输入输出 (Serializable I/O)
#    方便缓存、重放、审计
#
# 4. 自描述 (Self-Documenting)
#    SKILL.md 声明能力边界
```

### 3.2 Agent — 副作用协调器

> **设计准则：Agent 是唯一允许产生副作用的组件。核心职责 = Decision + Orchestration。**

#### Agent 分类体系

| Agent | LLM Tier | 使用 Skill | I/O 类型 | 副作用 |
|-------|----------|-----------|---------|--------|
| Supervisor | FAST | 无 | Read State → 决策 | 低 |
| RAG Agent | BALANCED | Retrieval, Generation | Read KB → 答案 | 中 |
| Code Agent | REASONING | Generation, Sandbox | Read/Write File/Exec | 高 |
| Web Agent | BALANCED | Web Search | HTTP → 数据 | 中 |
| Reflection | BALANCED | 无 | Read State → 评分 | 低 |
| Learning | FAST | Graph, Ingestion | Read Web → Knowledge | 中 |

#### Agent 内部三个合法动作

1. **DECIDE** — 用 LLM 做决策（选择哪个 Skill/Tool）
2. **INVOKE** — 调用 Skill Tool（纯函数，无副作用）
3. **EFFECT** — 执行副作用（Memory 写入 / API 调用 / 文件操作）

### 3.3 RAG Pipeline — 微服务治理化的数据流

#### Pipeline Step 治理清单

每个 Pipeline Step 必须实现：

1. **Contract (契约)** — 输入/输出 Schema + 副作用申报
2. **Observability (可观测)** — trace_log + 耗时 + Token 消耗
3. **Resilience (韧性)** — try/except + 降级策略 + 超时
4. **Configurability (可配置)** — 启用/禁用 + 参数可定制

### 3.4 Memory — 三层级联 + 服务治理

```
Tier-1 Hot Radar  (内存)    → CDN 缓存  / < 1ms   / 标签碰撞路由
Tier-2 Graph      (Neo4j)  → Service Mesh / 10-50ms / 关系跳跃
Tier-3 Deep Vector(Chroma) → 数据仓库  / 50-200ms / 语义精排
```

---

## 四、设计原则总结

### 从函数式编程学到的

| 原则 | 体现 |
|------|-----|
| 纯函数优先 | Skill Tools 无副作用 |
| 副作用隔离 | 所有 I/O 只在 Agent Node 内 |
| 不可变数据 | RetrievalContext 只追加不删改 |
| 函数组合 | Pipeline Steps 可自由组合 |
| 惰性求值 | Memory 三层级联 |

### 从微服务治理学到的

| 治理模式 | 体现 |
|----------|-----|
| 服务注册 | Skill / Agent / Step Registry |
| 服务发现 | Semantic Skill Discovery |
| 熔断器 | Pipeline Step 失败不阻塞 |
| 限流 | LLM Token Budget |
| 链路追踪 | Trace Log + DAG + LangFuse |
| 数据契约 | Pydantic Schema (Context/State/Document) |
| 灰度发布 | Pipeline 可配置化 |
| 健康检查 | KB 健康度评分 |

### 从分层架构学到的

| 原则 | 体现 |
|------|-----|
| 单一职责 | 每层只做自己的事 |
| 依赖倒转 | 上层依赖抽象接口 |
| 开闭原则 | 新增组件只需注册 |
| 接口隔离 | Agent 只看到 tool.invoke() |
| 禁止跨层 | Agent ≠ DB / Skill ≠ Agent |

---

> **核心洞察：** 用 **Skill 的确定性** 对冲 **Agent 的不确定性**，用 **Pipeline 的可观测性** 驯服 **RAG 的黑盒性**，用 **传统软件工程的治理模式** 管理 **AI 原生系统的复杂度**。

> 详细版本见: [artifact](../../.gemini/antigravity/brain/86f5a95c-ba4c-4a7d-a8ba-20c745eafea9/agent_skill_rag_architecture.md)
