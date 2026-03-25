# 📐 DES-003: HiveMind 后端全景架构与数据治理体系

> **定位**: 本文档整合了 HiveMind 后端从 Ingestion 到 Agent 响应的全链路架构，是后端开发的 Single Source of Truth。

---

## 1. 架构分层 (Layered Architecture)

HiveMind 后端采用“流式、解耦、原子化”的分层设计：

### 1.1 API & 路由层 (FastAPI Gateway)
*   **职责**: 负责身份鉴权、速率控制、路由分发与 SSE 初始握手。
*   **核心关联**: [core_routing_classification_design.md](../architecture/core_routing_classification_design.md)
*   **治理**: 遵循 HMER Phase 2 规范，所有 API 必须具备标准的 `trace_id` 用于全链路追踪。

### 1.2 Agent 蜂巢 (Agent Swarm & Orchestrator)
*   **职责**: 任务分类、技能分配合、长程记忆检索与多 Agent 协同。
*   **交互模型**: 基于 Anthropic 最佳实践的思维链 (CoT) 模式。
*   **核心关联**: [anthropic_agent_patterns.md](../architecture/anthropic_agent_patterns.md)

### 1.3 智适应 RAG 链路 (Resilient RAG Pipeline)
*   **职责**: 语义检索同步与异步重排序。
*   **弹性**: 支持在流式输出中动态注入“引证 (Citation)”与“中间状态 (Status)”。
*   **核心关联**: [rag_data_interface_design.md](../architecture/rag_data_interface_design.md)

---

## 2. 数据治理哲学：知识编译 (Knowledge Compilation)

我们不只是存储数据，我们在“编译”知识。

### 2.1 数据摄取 (Ingestion)
*   **理念**: 将每一个知识库 (KB) 视为独立治理的服务单元。
*   **策略**: 通过 `dynamic_batch_workflow` 实现高并发的文档拆解与向量化。
*   **核心关联**: [data_governance_philosophy.md](../architecture/data_governance_philosophy.md)

### 2.2 多维存储架构 (Multi-Storage)
*   **Vector (Chroma/Milvus)**: 负责高维语义检索。
*   **Graph (Neo4j)**: 负责实体关系追溯与架构拓扑发现。
*   **Relational (PostgreSQL)**: 负责业务元数据、角色权限与审计记录。

---

## 3. 后端在 Phase 4 (意图感知) 下的处理协议

为了配合前端的 `IntentManager`：
*   **预感应支持**: 后端各检索接口必须支持 `is_prefetch` 参数，在预热请求时不执行高开销的 LLM 生成模型，仅执行 Embedding 检索并更新热点缓存。
*   **断点续传协议**: SSE 接口需识别 `_resume_index` 参数，实现生成内容的精准偏移发射。

---

## 4. 后端 HMER 指标定义 (Observability)

后端必须实时上报以下关键指标：
| 指标 | 描述 | HMER 目标 |
| :--- | :--- | :--- |
| **Model TTFT** | 模型的首字响应延迟 (后端感知) | < 250ms |
| **Search Precision** | 检索召回的准确度相关性 | > 85% |
| **Token Cost** | 每千次 Token 的实际开销管控 | 基线控制 |
| **Cache Hit Rate** | 语义缓存命中率 | 目标 > 30% |

---

## 5. 结论：后端治理的最终目标
HiveMind 后端的终极使命是：**“将混乱的数据洪流转化为 Agent 的行动底座”**。通过严谨的分层设计与元数据治理，我们确保每一条 AI 的指令都能在架构层面得到确定的反馈与闭环监控。

---
> _“代码会腐化，但由严密定义构建的后端生态，将随着数据的汇聚而愈发强大。”_
