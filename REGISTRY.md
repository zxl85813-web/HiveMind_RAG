# 📦 HiveMind Intelligence Swarm — 资产注册表 (Registry)

> **⚠️ 重要**: 每次开发新功能/组件前，必须先查阅此文件，确认是否已存在可复用的代码。
> 每次新增功能后，必须在此文件中登记。

> 📅 最后更新: 2026-03-25 (对齐 SmartGrep/Telemetry/Phase4 资产)

---

## 🐍 后端 (Backend)

### API 端点 (api/v1/)

| 模块 | 方法 | 路径 | 描述 | 文件 | 状态 |
|------|------|------|------|------|------|
| **基础** | GET | `/health/` | 健康检查 | `health.py` | ✅ |
| **对话** | POST | `/chat/completions` | 对话补全 (SSE) | `chat.py` | ✅ |
| **对话** | GET | `/chat/conversations` | 会话管理 (CRUD) | `chat.py` | ✅ |
| **知识库** | ALL | `/knowledge/` | 库管理 (CRUD) / 搜索 / 链路 | `knowledge.py` | ✅ |
| **知识库** | ALL | `/tags/` | 文档/库标签体系管理 | `tags.py` | ✅ |
| **Agent** | GET | `/agents/swarm/todos` | 蜂巢任务监控 (TODO/Reflect) | `agents.py` | ✅ |
| **Agent** | ALL | `/memory/` | 长期/短期记忆管理接口 | `memory.py` | ✅ |
| **安全** | ALL | `/security/` | RBAC 权限 / 部门 / 密钥管理 | `security.py` | ✅ |
| **可观测** | GET | `/observability/` | 检索质量 / 路由占比 / 成本监控 | `observability.py` | ✅ |
| **可观测** | GET | `/observability/phase-gate/{phase}` | HMER 阶段准出审计报告 (Phase 0->1) | `observability.py` | ✅ |
| **治理** | ALL | `/service-governance/` | 限流 / 熔断器 / 智能路由配置 | `settings.py` | ✅ |
| **评估** | ALL | `/evaluation/` | RAG 质量评估系统接口 | `evaluation.py` | ✅ |
| **流水线** | ALL | `/pipelines/` | Ingestion Pipeline 配置与监控 | `pipelines.py` | ✅ |
| **审计** | GET | `/audit/` | 系统操作审计日志检索 | `audit.py` | ✅ |
| **遥测** | POST | `/telemetry/` | 性能埋点与 Trace 数据上报 | `telemetry.py` | ✅ |
| **评估** | GET | `/evaluation/ab-summary` | A/B 测试对比数据聚合 | `evaluation.py` | ✅ |
| **学习** | ALL | `/learning/` | 外部订阅 / 发现列表 / 自动采集 | `learning.py` | ✅ |
| **通信** | WS | `/ws/connect` | WebSocket 双工交互连接 | `websocket.py` | ✅ |

### 核心解耦协议 (Schemas)

| 名称 | 职责 | 文件 |
|------|------|------|
| `KnowledgeProtocol` | 定义 KnowledgeResponse / Fragment 统一交换格式 | `knowledge_protocol.py` |
| `ArtifactSchema` | Code / SQL / Doc 资产制品统一描述契约 | `artifact.py` |
| `SwarmState` | 定义 Agent 编排过程中的状态转移上下文 | `chat.py` |
| `SecurityClaims` | 定义 JWT 与 RBAC 权限点校验结构 | `auth.py` |

### 数据库模型 (Models)

| 分类 | 模型名称 | 文件 | 状态 |
|------|------|------|------|
| **用户/权限** | `User`, `Role`, `Permission`, `Department` | `security.py` | ✅ |
| **对话驱动** | `Conversation`, `Message`, `AnswerFeedback` | `chat.py` | ✅ |
| **知识资产** | `KnowledgeBase`, `Document`, `KbLink`, `Tag` | `knowledge.py` / `tags.py` | ✅ |
| **治理/观测** | `Span`, `Trace`, `CircuitBreakerEvent`, `BaselineMetric` | `observability.py` | ✅ |
| **搜索增强** | `SmartGrepExpansion`, `MatchResult` | `smart_grep.py` | ✅ |
| **意图/缓存** | `IntentCache`, `PrefetchJob` | `intent.py` | ✅ |
| **质量中心** | `EvaluationItem`, `Report`, `Metrics` | `evaluation.py` | ✅ |
| **后台任务** | `PipelineJob`, `PipelineStageLog`, `SyncLog` | `pipeline_config.py` | ✅ |

### 服务治理与业务逻辑 (Services)

| 名称 | 职责 | 实现状态 |
|------|------|------|
| `RAGGateway` | **单一知识入口**: 实现 KB 熔断、策略路由、结果聚合 | ✅ 已上线 |
| `FallbackOrchestrator` | **降级编排器**: `Cache -> Local -> Backup` 自动回退机制 | ✅ 已上线 |
| `ClawRouterGovernance` | **智能架构路由**: 按复杂度/成本动态分派 Eco/Premium 模型 | ✅ 已上线 |
| `DependencyCircuitBreaker` | **依赖断路器**: 针对 ES/Neo4j/LLM 的滑动窗口错误隔离 | ✅ 已上线 |
| `RateLimitGovernanceCenter` | **流量治理**: 令牌桶限流 (Route/User/Key 粒度) | ✅ 已上线 |
| `IntentManager` | **意图预测**: 意图识别与数据并行预取 | ✅ 已上线 |
| `TieredParallelOrchestrator` | **并行检索**: Vector/Graph/Grep 并发赛马 | ✅ 已上线 |
| `SmartGrepService` | **语义化搜索**: 传统正则扩展与快速逻辑扫描 | ✅ 已上线 |
| `EpisodicMemoryService` | **情景记忆召回**: 支持同义词扩展的深度回忆 | ✅ 已上线 |
| `CacheService` | **JIT 路由缓存**: 语义级别的路由匹配决策加速 | ✅ 已实现 |
| `KnowledgeService` | 知识库全生命周期驱动逻辑 | ✅ |
| `AuditService` | 系统敏感操作全量埋点与持久化 | ✅ |
| `WriteEventBus` | 跨服务异步写通知 (Document -> Indexing) | ✅ |

---

## ⚛️ 前端 (Frontend)

### 功能页面 (Pages)

| 名称 | 路径 | 职责 | 状态 |
|------|------|------|------|
| `DashboardPage` | `/` | 统计看板与快捷入口 | ✅ |
| `KnowledgePage` | `/knowledge` | 知识库管理与上传 | ✅ |
| `AgentsPage` | `/agents` | Agent 蜂巢任务与自省流监控 | ✅ |
| `AuditPage` | `/audit` | 系统安全审计日志列表 | ✅ |
| `SecurityPage` | `/security` | RBAC 权限与部门拓扑配置 | ✅ |
| `EvalPage` | `/evaluation` | RAG 质量比对与评估报告展示 | ✅ |
| `PipelineBuilderPage`| `/pipelines` | Ingestion 流水线编排画布 | ✅ |
| `LearningPage` | `/learning` | 外部订阅与资讯发现中心 | ✅ |
| `SettingsPage` | `/settings` | LLM 参数、密钥与系统全局配置 | ✅ |
| `ArchitectureLabPage` | `/architecture-lab` | A/B 测试看板、性能对比与遥测监控 | ✅ |
| `BatchPage` | `/batch` | 批量数据处理与任务队列监控 | ✅ |

### 逻辑组件 (Hooks & Providers)

| 名称 | 职责 | 文件 |
|------|------|------|
| `useSSE` | 支持 POST 的高级流式通信 Hook (含重连逻辑) | `useSSE.ts` |
| `useWebSocket` | WebSocket 连接管理与消息队列缓存 | `useWebSocket.ts` |
| `useChat` | 对话交互、消息渲染与上下文感知逻辑封装 | `useChat.ts` |
| `MonitorService` | 客户端遥测采集 (TTFT, Network, Error Audit) | `core/MonitorService.ts` |
| `IntentManager` | 🆕 预测性预取解析器 (意图预测) | `core/IntentManager.ts` |
| `LocalEdgeEngine` | 🆕 IndexedDB 边缘存储引擎 | `core/LocalEdgeEngine.ts` |
| `XProvider` | AntD X 扩展组件全局注入器 | `App.tsx` |

### 状态中心 (Stores)

| 名称 | 职责 | 实现方式 |
|------|------|------|
| `useAuthStore` | 记录 Profile、角色权限及 Mock 角色切换 | Zustand |
| `useChatStore` | 核心消息树、Panel 开合、Client Event 日志 | Zustand |
| `useWSStore` | 实时系统消息、通知红点状态 | Zustand |

---

## 🛠️ 运维与验证脚本 (Scripts)

> **原则**: 凡是参与 CI/CD 准入、数据治理或环境验证的脚本，必须在此登记，并接入 `UnifiedLog` 协议。

| 分类 | 脚本名 | 职责描述 | 相关治理 Gate | 状态 |
|------|--------|----------|---------------|------|
| **治理钻探** | `run_sg007_governance_drills.py` | 模拟 Steady/Spike/Chaos 场景，验证熔断与降级 | GATE-SG-4 | 🔄 接入中 |
| **门禁验证** | `validate_gate_sg1_stability_window.py` | 滚动窗口期稳定性审计 (24h/5 samples) | GATE-SG-1 | ⚠️ 待对齐 |
| **状态验证** | `validate_step7_closure_readiness.py` | 阶段 5 关闭前的全量就绪度核对 | GATE-SG-5 | ⚠️ 待对齐 |
| **性能基线** | `baseline_llm.py` | 获取各 Provider 的 TTFT/TPS 基线数据 | - | ⚠️ 待对齐 |
| **资产同步** | `create_github_milestone_from_todo.py` | 将本地 TODO.md 自动映射为 GitHub Milestone | - | ✅ |
| **调试分析** | `trace_analyzer.py` | 聚合审计 `logs/` 目录下所有 UnifiedLog 链路 | - | ⚠️ 待对齐 |

---

## 🏗️ 架构底座 (Core Architecture)

| 组件 | 对应设计/规则 | 描述 |
|------|--------------|------|
| **错误边界** | `ErrorBoundary.tsx` | 捕获组件渲染崩溃，提供自愈重置机制 |
| **权限卫兵** | `AccessGuard.tsx` | 细粒度的页面/功能位级 RBAC 拦截 |
| **统一响应** | `ApiResponse` (后端) | 遵循 `error_code / message / detail` 标准协议 |
| **治理韧性** | `DES-001-FRONTEND_ARCHITECTURE.md` | 前端架构权威设计说明书 (整合版) |
| **验证体系** | `DES-002-TESTING_STRATEGY.md` | 全链路测试与质量保障策略 (整合版) |
| **设计系统** | `frontend-design` Skill | Cyber-Refined 赛博精致视觉规范 |

---

> 🔗 **关联索引**:
> - [TODO.md](TODO.md) — 任务优先级与进度
> - [docs/architecture/](docs/architecture/) — 深度设计文档
