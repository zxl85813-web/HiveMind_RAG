# DEV-REQ-013: V3 数据入库分布式智能体集群重构与监控脱水计划

| 字段 | 值 |
|------|------|
| **关联需求** | REQ-013 (全局多智能体数据入库架构V3) |
| **开始时间** | 2026-03-07 |
| **状态** | 🚧 需求拆解与规划中 |

> **动机与当前系统痛点审视**: 
> 1. **监控层隐患**：现有的 `Langfuse` 对于高频并发入库来说过于沉重，频繁跨网 HTTP 调用极易导致 Node 卡死；而 `swarm.py` 中手工维护在内存的 `self._traces` 更是具有内存溢出（OOM）和重启丢失的巨大风险。
> 2. **流水线僵尸化**：核心的入库骨架 `IngestionExecutor` 依然是基于传统数组遍历的固定阶段流水线 (Parse -> Audit)，对于包含复杂逻辑推断的分支文件（如果代码包含AST调用图则处理关联，否则进入普通文本）缺乏动态响应能力。
> 3. **C端B端智商断层**：前端聊天在用最先进的 LangGraph 路由，底层入库却还在依靠按文件后缀匹配的 `TextParser`，面对大规模不可预期的工程资产极其脆弱。

## 任务分解 (Granular TODOs)

| # | 子任务 | 文件/模块预期位置 | 状态 | 预估耗时 |
|---|--------|-------------------|------|----------|
| **Phase 1: 监控换核 (Lightweight Observability)**| | | | 
| 1.1 | 建立轻量级监控数据模型 (FileTrace, AgentSpan) | `backend/app/models/observability.py` | ⬜ | 1 h |
| 1.2 | 开发基于 Redis 缓冲的 Langchain 异步 CallbackHandler | `backend/app/core/telemetry/tracer.py` | ⬜ | 2 h |
| 1.3 | 清除 `Langfuse` 依赖及全局配置，移除旧的内存 `_traces` | `pyproject.toml`, `backend/app/agents/memory.py` | ⬜ | 0.5 h |
| **Phase 2: 任务粉碎与队列 (Dispatcher & Queue)**| | | | 
| 2.1 | 集群任务表与微任务状态管理 (Batch, IngestionTask) | `backend/app/models/ingestion.py` | ⬜ | 1 h |
| 2.2 | 配置 Celery/Redis Worker 作为后台并发消费引擎 | `backend/worker.py`, `backend/app/core/celery_app.py` | ⬜ | 2 h |
| 2.3 | API 端点重构：从阻塞编译变更为投递 ZIP 到粉碎机 | `backend/app/api/routes/knowledge.py` | ⬜ | 1.5 h |
| **Phase 3: 纯血分布式 Swarm 研发 (Native StateGraph)**| | | | 
| 3.1 | 定义用于单文件的全局状态树 `IngestionSwarmState` | `backend/app/agents/ingestion/state.py` | ⬜ | 0.5 h |
| 3.2 | 开发核心代理群：`DocAgentNode`, `CodeAgentNode` | `backend/app/agents/ingestion/specialists.py` | ⬜ | 3 h |
| 3.3 | 开发图汇聚与质检节点：`CriticNode` (人工干预判断) | `backend/app/agents/ingestion/critic.py` | ⬜ | 2 h |
| 3.4 | 编译入库工作流 `IngestionOrchestrator` (取代 Executor) | `backend/app/agents/ingestion/graph.py` | ⬜ | 2 h |
| **Phase 4: 全局黑板与人工抽检台 (Blackboard & HITL)**| | | | 
| 4.1 | 人工待办数据库与抽检状态机 (ReviewQueue) | `backend/app/models/hitl.py` | ⬜ | 1 h |
| 4.2 | Backend API: 获取抽检列表、提交人工决议 | `backend/app/api/routes/reviews.py` | ⬜ | 1.5 h |
| 4.3 | 全局经验黑板 (Redis 级联规则库) 同步推演机制 | `backend/app/services/learning/blackboard.py` | ⬜ | 2 h |
| 4.4 | Frontend: 抽检任务中心页面 (Review Dashboard) | `frontend/src/pages/IngestionReview.tsx` | ⬜ | 3 h |
| **Phase 5: 清理战场 (Deprecation)**| | | | 
| 5.1 | 废除旧的 `batch.ingestion.pipeline` 及 `executor` | `backend/app/batch/ingestion/*` | ⬜ | 1 h |

---

## 开发日志

### 准备阶段: 彻底重构的决策
**时间**: 2026-03-07
**操作**: 对比现存架构后，建立 `DEV-REQ-013` 文档。
**决策**: 架构师决议抛弃 Langfuse 避免网络 I/O 拖垮吞吐量；废弃僵固线型流水线，让 Swarm 原生统治全量流程。这不仅解决了十万级代码并发问题，还能让系统支持任意类型的私有知识文件扩展（只需加新的 AgentNode 即可）。

*(日志将随各个 Phase 的开展实时更新...)*

## 总结
**状态**: 计划已敲定，待开工。
**风险提示**: LangGraph 的分布式持久化 (State Checkpointing) 需要确保在 Redis 下并发安全；Celery 的 Worker 和 Graph 的结合需要处理好超时熔断机制。
