<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/node-18+-green?logo=node.js&logoColor=white" alt="Node.js" />
  <img src="https://img.shields.io/badge/FastAPI-latest-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-18+-61DAFB?logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/LangGraph-Agent_Orchestration-7C3AED" alt="LangGraph" />
  <img src="https://img.shields.io/badge/license-Private-red" alt="License" />
</p>

# 🐝 HiveMind — Intelligence Swarm & Cognitive Engine

> *蜂群不是靠一只蜜蜂来运转的。*
> *每一滴蜂蜜，都是千万次分工协作的结晶。*

---

## 🚀 系统全景

**HiveMind 不仅仅是一个 RAG 平台。**

传统的 RAG 只是“检索并生成”，而 HiveMind 是一个**以智体蜂巢 (Agent Swarm) 为核心的认知操作系统**。我们像经营蜂巢一样管理知识与智能：

- **花粉 (数据)**: 原始文档被视为待提炼的原始素材。
- **蜂群 (Agent Swarm)**: 自主集群飞入知识库，进行多触角、多维度的解析与对齐。
- **酿蜜 (知识编译)**: 知识不再只是存储，而是被“编译”为三层记忆：抽象索引、Neo4j 图谱、向量语义库。
- **核心逻辑**: 当用户提问，系统通过 **IntentManager (意图感知器)** 预判需求，指挥 **Supervisor Agent** 精准调用蜂群技能。

这套体系打破了“搜索”的边界，实现了从“数据存储”到“主动智能”的范式跃迁。

---

## 蜂群的五层体系

HiveMind 的设计围绕四个相互支撑的治理体系 + 一个贯穿全局的共学体系展开：

### 🧭 Agent 治理 — 蜂群的指挥系统

Supervisor Agent 是整个系统的大脑。它解析用户意图、分配任务给专属 Worker、通过 Reflection Agent 对结果进行质量把关，不合格则打回重做。这套 Agent Swarm 基于 **LangGraph StateGraph** 构建，支持状态持久化与多步骤推理。

→ 详见 [Agent 治理体系](docs/architecture/README.md#1-智能体与技能协议-agentic-protocols)

### 🍯 数据治理 — 知识的酿造过程

数据入库不是简单的切块+向量化。每一份文档经过 Agent 调度的多 Skill Pipeline 处理：解析原始内容、为每个分块注入上下文背景（Contextual Retrieval）、抽取实体和关系写入知识图谱。最终形成**三层可检索的记忆结构**——抽象索引、Neo4j 图谱、pgvector 向量库。

→ 详见 [数据治理体系](docs/architecture/README.md#2-数据治理与存储引擎-data--storage)

### 🏭 开发治理 — 蜂巢的生产规范

凡是蜂巢，必有规则。`.agent/` 目录是 HiveMind 的研发治理体系，约束人类开发者与 AI Agent 的每一次代码提交：标准化工作流 SOP、Git Hooks 门禁、AI 编码规范、质量检查脚本。**这套体系本身也是 Agent 可读、可执行的**。

→ 详见 [开发治理规范](docs/architecture/GOV-001-DEVELOPMENT_GOVERNANCE.md)

### 🛡️ 架构治理 — 软件大脑与资产防腐

真正的智能不只在于模型够大，更在于**生态的韧性**。HiveMind 实现了 **HiveDispatcher (蜂群调度器)**，通过 15 维度意图判定，在 Eco 与 Premium 模型间动态切分。同时，系统建立了 **分层检索矩阵 (Tiered Retrieval Matrix)**：

- **🔥 热路 (Hot Path)**：利用 `SmartGrep` + `ChromaDB` 实现本地用户会话的秒级精准召回（个人隐私安全）。
- **❄️ 冷路 (Cold Path)**：集成 `Elasticsearch (ES)` 实现对全局技术文档、百万级历史数据的惰性按需检索。
- **🧠 记忆图谱**：内置基于 Neo4j 的 **软件大脑 (Arch-Graph)**，通过 AST 解析与 Git 提交分析，提供上帝视角的代码逻辑拓扑空间，已优化百万级节点的实时导入效率。

→ 详见 [架构图谱文档](docs/architecture/ARCH-GRAPH.md)

### 📡 可观测性治理 — 蜂巢的神经系统

HiveMind 严守“**无监控，不交付**”的原则。通过统一的 `UnifiedLog` 协议，将前端交互、API 路由、Agent 决策及底层存储操作全线串联：

- **⛓️ 全链路追踪**: 每一个请求/决策流均携带 `trace_id`，支持使用 `trace_analyzer.py` 进行逻辑回溯。
- **📊 遥测收口**: 集成 MonitorService 遥测网关，支持 `keepalive` 与 `sendBeacon` 双重保障，确保关键执行轨迹 100% 留痕。
- **🛡️ 审计门禁**: 建立 RAG 安全审计机制（RAG-SECURITY），定期生成风险报告，覆盖数据投毒与隐私泄露防护。

→ 详见 [全链路可观测性标准](docs/architecture/unified_observability_standard.md)

### 🧬 共学体系 — 蜂群的集体进化系统

**蜜蜂发现花源不会独享，它跳起摇摆舞让整个蜂群受益。** HiveMind 将「自主查漏补缺反省」和「团队互相借鉴学习」融合为三个互锁的循环飞轮：

- **🪞 自省循环**：每日系统扫描 + Reflection Agent 质检 + 差距识别（GAP / ISSUE / INSIGHT 三类） + 7 日行动路线
- **🤝 互学循环**：四视角 Code Review + PR 知识注释 + Issue 驱动协作 + 差距互补配对（A 的盲区恰好是 B 的经验 → 精准配对）
- **🌍 共进循环**：通用模式结晶为 Skill → 注册到 REGISTRY → 学习路径更新 → 多厂商对标实验 → 正向飞轮加速

三阶段飞轮通过 `SwarmMemoryBridge` 实现知识持久化，确保 Agent Swarm 的每一次协作都能转化为系统的 L3 向量记忆。

→ 详见 [共学体系文档](docs/guides/COLLABORATIVE_LEARNING.md)
---

## 系统全局图

```mermaid
graph TD
    User((👤 用户)) --> UI["⚛️ React Copilot UI\n伴随式 ChatPanel"]
    UI -->|SSE 流式| API["🌐 FastAPI Gateway"]

    subgraph "🧭 Agent 治理层 — 指挥系统"
        API --> Router["⚖️ LLM Router\n智能路由 / 熔断降级"]
        Router --> Supervisor["🧠 Supervisor\n意图路由 & 任务分发"]
        Supervisor --> RAG["📚 RAG Agent"]
        Supervisor --> Code["💻 Code Agent"]
        Supervisor --> Web["🌐 Web Agent"]
        RAG & Code --> Reflection["🪞 Reflection Agent\n质量评审 & 自省纠错"]
    end

    subgraph "📡 观测与神经中枢"
        UnifiedLog["🧾 UnifiedLog\n结构化日志流"]
        Telemetry["📡 MonitorService\n生命周期遥测"]
        Analyzer["🔍 Trace Analyzer\n全链路回溯工具"]
        UI -.-> Telemetry
        API -.-> UnifiedLog
        Supervisor -.-> UnifiedLog
        UnifiedLog --> Analyzer
    end

    subgraph "🍯 数据治理层 — 酿蜜系统"
        RAG --> T1["Tier 1\n抽象索引"]
        RAG --> T2["Tier 2\nNeo4j 知识图谱"]
        RAG --> T3["Tier 3\npgvector + BM25 + Reranker"]
        Ingestion["📥 全量/增量文档接入\n(Queue / Batch)"] --> Dispatcher["⚡ 任务粉碎与分发网关\n(Celery/Redis)"]
        Dispatcher --> JobMgr["🧠 分布式 Ingestion Swarm\n(原生 LangGraph StateGraph)"]
        JobMgr --> Parse["动态 Agent Nodes\n(Code/Doc/Data/Critic)"]
        Parse --> Enrich["知识融合算子\n(人工复核 / 经验黑板)"]
        Enrich --> T2
        Enrich --> T3
    end

    subgraph "🏭 开发治理层 — 生产规范"
        AgentRules[".agent/ 规则体系"]
        Workflows["标准化 Workflows"]
        GitHooks["Git Hooks 门禁"]
        AgentRules --- Workflows
        AgentRules --- GitHooks
    end

    subgraph "🧬 共学体系 — 集体进化"
        SelfReflect["🪞 自省循环\n每日扫描 · 差距识别 · 行动路线"]
        MutualLearn["🤝 互学循环\n四视角 Review · 差距配对"]
        CoEvolve["🌍 共进循环\n知识结晶 · 多源对标 · 正向飞轮"]
        SelfReflect -->|差距输出| MutualLearn
        MutualLearn -->|洞见沉淀| CoEvolve
        CoEvolve -->|路径更新| SelfReflect
        Reflection -.->|ReflectionEntry| SelfReflect
    end
```

---

## 快速开始

### 环境要求

| 依赖 | 版本 | 备注 |
|:---|:---|:---|
| Python | 3.11+ | 后端运行时 |
| Node.js | 18+ | 前端构建 |
| PostgreSQL | 14+ | 需启用 pgvector 扩展 |
| Redis | 6+ | 队列与缓存 |
| Neo4j | 任意 | 可选，图谱层 |

### 启动

```bash
# 后端
cd backend
# 安装依赖
pip install -e ".[dev]"

# 数据库迁移 (初始化表结构)
alembic upgrade head

# 启动服务
uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

### 常用命令

```bash
python -m scripts.create_superuser <user> <pass>        # 创建管理员 (在 backend 目录下)
python scripts/trace_analyzer.py --id <trace_id>          # 全链路日志回溯分析
alembic revision --autogenerate -m "description"            # 生成迁移脚本
./.agent/checks/run_checks.ps1                              # 质量检查
```

---

## 文档地图

| 文档 | 一句话说明 |
|:---|:---|
| [🧭 Agent 治理](docs/architecture/README.md#1-智能体与技能协议-agentic-protocols) | Supervisor 架构、Agent DAG、Reflection 机制 |
| [🍯 数据治理](docs/architecture/README.md#2-数据治理与存储引擎-data--storage) | 知识酿造全流程：解析→增强→图谱→向量→检索 |
| [🏭 开发治理](docs/architecture/GOV-001-DEVELOPMENT_GOVERNANCE.md) | `.agent/` 规范体系、SOP 工作流、Git 门禁 |
| [🧬 共学体系](docs/guides/COLLABORATIVE_LEARNING.md) | 自省↔互学↔共进 三环飞轮，融合自审与协作学习 |
| [📡 链路观测标准](docs/architecture/unified_observability_standard.md) | `UnifiedLog` 协议、遥测收口与全链路追踪规范 |
| [🛡️ 安全审计报告](docs/governance/RAG-SECURITY-AUDIT-2026.md) | RAG 权限隔离与数据投毒风险深度扫描 |
| [🎓 学习路径](docs/guides/LEARNING_PATH.md) | L0-L4 边做边学地图，双向追踪最小规范 |
| [🧠 软件大脑](docs/architecture/ARCH-GRAPH.md) | 基于 Neo4j 的全生命周期架构资产图谱 |
| [系统概览](docs/SYSTEM_OVERVIEW.md) | 全局设计哲学与技术选型 |
| [路线图](docs/ROADMAP.md) | 开发里程碑与规划 |
| [协作交付手册](docs/guides/collaboration_and_delivery_playbook.md) | 团队协作全流程、GitHub 自动化、里程碑同步 |
| [模块注册表](REGISTRY.md) | 全局模块与 Skill 注册表 |
| [贡献指南](CONTRIBUTING.md) | 提交规范、工作流、协作约定 |

---

## License

Private — All Rights Reserved
