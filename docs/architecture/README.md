# 📐 HiveMind Intelligence Swarm — 深度设计与架构图谱

> **定位**: 本目录存放 HiveMind 系统中各专项模块的深度设计文档（L3-L4 层级）。
> 它们是系统架构决策的具体展开，也是开发者实现核心功能的权威依据。

---

## 🤖 1. 智能体与技能协议 (Agentic Protocols)

描述 Agent Swarm 的运行逻辑、技能装配与任务编排：

*   **[Agent 技能 RAG 哲学](agent_skill_rag_philosophy.md)** — 本项目 Agent 开发的底层逻辑：为什么要解耦行为与记忆。
*   **[Anthropic 智能体模式](anthropic_agent_patterns.md)** — 基于 Anthropic 最佳实践的模式实现。
*   **[动态技能架构设计](dynamic_skill_architecture.md)** — 系统的热插拔 Skill 机制说明。
*   **[工作流生命周期](workflow_lifecycle.md)** — 每类任务从触发到闭环的状态机逻辑。
*   **[认知架构图谱 (ARCH-Graph)](ARCH-GRAPH.md)** — 连接需求、设计、代码与度量的“数字大脑”中枢定义。
*   🆕 **[动态图谱记忆体系 (AGENT_GRAPH_MEMORY)](AGENT_GRAPH_MEMORY.md)** — Hybrid GraphRAG + Agent Style Memory 双核能力：架构跳跃检索与个性化编程风格持久记忆。
*   🆕 **[图谱驱动架构拆解展示 (SHOWCASE)](SHOWCASE-GRAPH-DECOMPOSITION.md)** — 图谱节点可视化与架构关系分解示范。
*   🆕 **[图谱高级用例 (GRAPH-ADVANCED)](GRAPH-ADVANCED-USECASES.md)** — 技术债热力图(Timebomb Detection)等进阶图谱分析场景。

---

## 🍯 2. 数据治理与存储引擎 (Data & Storage)

*   **[数据治理哲学](data_governance_philosophy.md)** — 核心 41KB 文档：详述我们如何“编译”而非仅仅存储知识。
*   **[数据微服务治理](data_microservice_governance.md)** — 将每一个知识库 (KB) 视为独立治理的服务单元。
*   **[RAG 数据接口协议](rag_data_interface_design.md)** — 规范 RAG 输出的强 Schema 契约。
*   **[记忆压缩方案](memory_compression_design.md)** — 长程记忆中的信息蒸馏与压缩设计。
*   🆕 **[业务流全景映射 (business_flow)](business_flow.md)** — 系统端到端请求生命周期的全链路 Neo4j 图谱映射。
*   🆕 **[业务驱动测试策略 (business_driven_testing)](business_driven_testing.md)** — 基于图谱的全栈 E2E 测试用例生成策略。
*   🆕 **[Neo4j 数据流设计 (neo4j_data_flow)](neo4j_data_flow.md)** — 图谱节点/关系的写入、查询与扩展设计规范。

---

## ⚡ 3. 支撑服务与路由弹性 (Core, Routing & Resilience)

*   **[DES-001-FRONTEND_ARCHITECTURE.md](../design/DES-001-FRONTEND_ARCHITECTURE.md)** — 核心：AI-First 前端全景架构 (含 Core 层)
*   **[DES-003-BACKEND_ARCHITECTURE.md](../design/DES-003-BACKEND_ARCHITECTURE.md)** — 核心：后端全景架构与数据治理体系
*   **[routes.json](./routes.json)** — 🛰️ 智体路由全景图谱 (Static Map)
*   **[ACCESS_ROLE_MEMORY_GOVERNANCE.md](./ACCESS_ROLE_MEMORY_GOVERNANCE.md)** — 系统的权限与记忆访问控制设计。
*   **[核心路由与分类设计](core_routing_classification_design.md)** — 流量进入后如何快速路由到正确的 Agent 或缓存。
*   **[服务治理拓扑](service_governance_topology.md)** — 全局服务互联与监控边界。
*   **[前端韧性治理](frontend_resilience_governance.md)** — 状态跟随、断网容错与 AI 模式持久化。
*   **[AI_FRONTEND_STRATEGY.md](../../AI_FRONTEND_STRATEGY.md)** — 专项：AI 前端交互哲学、预取效能与流式健壮性白皮书

---

## 🛠️ 4. 工程化与治理 (Engineering & Governance)

*   **[GOV-001-DEVELOPMENT_GOVERNANCE.md](./GOV-001-DEVELOPMENT_GOVERNANCE.md)** — 🆕 开发治理、RDD 注册驱动与 Phase Gate 审计规范
*   **[全链路可观测性标准](./unified_observability_standard.md)** — `UnifiedLog` 协议、遥测收口与全链路追踪规范
*   **[DES-002-TESTING_STRATEGY.md](../design/DES-002-TESTING_STRATEGY.md)** — 全链路质量保障与 TDD 体系
*   **[超级力量 (Superpowers) 集集指南](SUPERPOWERS_INTEGRATION_GUIDE.md)** — 基于 Agent 辅助的“降维”开发理念。
*   **[分支策略手册](branch_strategy.md)** — 不同类型 Issue 对应的分支生命周期。
*   **[动态批处理流](dynamic_batch_workflow.md)** — 针对重型文档 ingestion 的并发处理机制。
*   **[开源技术路线引用](open_source_references.md)** — 本系统选型背后的依据与参考引用。

---

## 🏗️ 5. 架构决策记录 (ADR)

*   **进入目录: [docs/architecture/decisions/](decisions/)** — 查阅历史上每一个关键技术选型的 ADR。

---
> _“架构不仅是组件的堆砌，更是对系统演进可能性的深思熟虑。”_
