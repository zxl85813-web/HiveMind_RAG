# 📦 HiveMind Intelligence Swarm — 资产注册表 (Registry)

> **⚠️ 重要**: 每次开发新功能/组件前，必须先查阅此文件，确认是否已存在可复用的代码。
> 每次新增功能后，必须在此文件中登记。

> 📅 最后更新: 2026-03-31 (补录 GraphMemory / 图谱记忆服务 / 脚本 / 页面)

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
| **Agent** | POST | `/agents/swarm/chat` | Swarm 协作对话 (SSE 流式) | `agents.py` | ✅ |
| **Agent** | ALL | `/memory/` | 长期/短期记忆管理接口 | `memory.py` | ✅ |
| **安全** | ALL | `/security/` | RBAC 权限 / 部门 / 密钥管理 | `security.py` | ✅ |
| **可观测** | GET | `/observability/` | 检索质量 / 路由占比 / 成本监控 | `observability.py` | ✅ |
| **可观测** | GET | `/observability/phase-gate/{phase}` | HMER 阶段准出审计报告 (Phase 0->1) | `observability.py` | ✅ |
| **治理** | ALL | `/service-governance/` | 限流 / 熔断器 / 智能路由配置 | `settings.py` | ✅ |
| **评估** | ALL | `/evaluation/` | RAG 质量评估系统 (独立 Grader v2) | `evaluation.py` | ✅ |
| **流水线** | ALL | `/pipelines/` | Ingestion Pipeline 配置与监控 | `pipelines.py` | ✅ |
| **审计** | GET | `/audit/` | 系统操作审计日志检索 | `audit.py` | ✅ |
| **遥测** | POST | `/telemetry/` | 性能埋点与 Trace 数据上报 | `telemetry.py` | ✅ |
| **评估** | GET | `/evaluation/ab-summary` | A/B 测试对比数据聚合 | `evaluation.py` | ✅ |
| **学习** | ALL | `/learning/` | 外部订阅 / 发现列表 / 自动采集 | `learning.py` | ✅ |
| **通信** | WS | `/ws/connect` | WebSocket 双工交互连接 | `websocket.py` | ✅ |
| **微调** | ALL | `/finetuning/` | 模型微调任务管理接口 | `finetuning.py` | 🟡 骨架 |
| **生成** | ALL | `/generation/` | 内容生成与资产输出接口 | `generation.py` | 🟡 骨架 |
| **审计V3** | GET | `/audit/v3/` | 升级版审计链路查询接口 | `audit_v3.py` | 🟡 骨架 |

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
| **质量中心** | `EvaluationItem`, `Report`, `Metrics`, `BadCase` | `evaluation.py` | ✅ |
| **治理中心** | `LLMMetric` | `observability.py` | ✅ |
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
| 🆕 `GraphIndexService` | **图谱记忆核心**: Hybrid GraphRAG 架构检索 + Agent Style Memory 偏好读写 | ✅ 已实现 |
| 🆕 `CodeVaultService` | **代码全景资产**: 基于 AST 的代码解析与图谱存储 (M7.2) | `memory/tier/graph_index.py` | ✅ |
| 🆕 `ClawRouterGovernance` | **智能分流引擎**: 15 维动态评分决策中心 (M7.1) | `claw_router_governance.py` | ✅ |
| 🆕 `AbstractIndexService` | **图谱索引抽象层**: 定义 `record_agent_preference` / `get_agent_preferences` 契约 | ✅ 已实现 |
| 🆕 `BudgetService` | **成本治理中心**: LLM Token 预算统计与自动化超支熔断 (M7.1) | `app/services/governance/budget_service.py` | ✅ |
| 🆕 `KnowledgeFreshnessService` | **知识新鲜度中心**: RAG 文档生命周期巡检与过期治理 (TASK-GOV-003) | `app/services/knowledge/freshness_service.py` | ✅ |
| 🆕 `FaithfulnessGrader` | **忠实度评估器**: 逐句 claim 验证，检测幻觉 (Eval v2) | `app/services/evaluation/graders/faithfulness.py` | ✅ |
| 🆕 `RelevanceGrader` | **相关性评估器**: 逆向问题生成 + 语义相似度 (Eval v2) | `app/services/evaluation/graders/relevance.py` | ✅ |
| 🆕 `CorrectnessGrader` | **正确性评估器**: GT 事实对比 TP/FN/FP 计算 (Eval v2) | `app/services/evaluation/graders/correctness.py` | ✅ |
| 🆕 `ContextPrecisionGrader` | **上下文精确度评估器**: 检索信噪比评估 (Eval v2) | `app/services/evaluation/graders/context.py` | ✅ |
| 🆕 `ContextRecallGrader` | **上下文召回率评估器**: 信息覆盖度评估 (Eval v2) | `app/services/evaluation/graders/context.py` | ✅ |
| 🆕 `BaseGrader` | **评估器基类**: CoT 推理 + 多次采样 + 置信度计算 (Eval v2) | `app/services/evaluation/graders/base.py` | ✅ |
| 🆕 `RagAssertionGrader` | **硬规则断言层**: CITE-001/002 强制规则兜底 | `app/services/evaluation/rag_assertion_grader.py` | ✅ |
| 🆕 `MultiGraderEval` | **多裁判评估器**: 6 维度独立评分 + 硬规则联动 | `app/services/evaluation/multi_grader.py` | ✅ |
| 🆕 `ABTracker` | **A/B 实验追踪器**: 执行变体遥测采集与统计分析 | `app/services/evaluation/ab_tracker.py` | ✅ |
| 🆕 `SelfLearningService` | **自进化服务**: 失败案例自动反思 + Todo 生成 (L4) | `app/services/evolution/self_learning.py` | ✅ |

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
| 🆕 `CanvasLabPage` | `/canvas-lab` | 画布模式实验性交互 Lab | 🟡 实验中 |
| 🆕 `FineTuningPage` | `/fine-tuning` | 模型微调任务配置与监控 | 🟡 骨架 |
| 🆕 `StudioPage` | `/studio` | 创作工作台 (代码/文档生成) | 🟡 骨架 |
| 🆕 `ForbiddenPage` | `/403` | 无权限访问提示页 | ✅ |
| 🆕 `ChatPage` | `/chat` | 核心对话交互页面 | ✅ |
| 🆕 `KBAnalyticsPage` | `/kb-analytics` | 知识库质量与热点分析 | ✅ |
| 🆕 `TokenDashboardPage` | `/token-stats` | 实时 Token 消耗与成本仪表盘 | ✅ |
| 🆕 `TracePage` | `/traces` | 全链路追踪日志查看器 | ✅ |

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
| `SwarmChatPanel` | **智体协作面板**: SSE 流式思考与 Action 交互 | `components/agents/SwarmChatPanel.tsx` |

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
| **治理钻探** | `run_sg007_governance_drills.py` | 模拟 Steady/Spike/Chaos 场景，验证熔断与降级 | GATE-SG-4 | ✅ |
| **门禁验证** | `validate_gate_sg1_stability_window.py` | 滚动窗口期稳定性审计 (24h/5 samples) | GATE-SG-1 | ✅ |
| **熔断验证** | `validate_step3_circuit_breaker.py` | 模拟依赖故障，验证熔断/探针/恢复链路 | GATE-SG-2 | ✅ |
| **成本审计** | `validate_step5_sg3_cost_quality.py` | 模拟负载，审计智能路由的成本节约与质量损耗 | GATE-SG-3 | ✅ |
| **门禁验证** | `validate_step7_governance_gates.py` | 评估 SG-003/007 结果并生成最终准出结论 | GATE-SG-5 | ✅ |
| **状态验证** | `validate_step7_closure_readiness.py` | 阶段 5 关闭前的全量就绪度核对 | GATE-SG-5 | ✅ |
| **数据管理** | `seed_demo_eval.py` | 植入综合评测 Demo 数据 (Arena/KB) | - | 已对齐 (UnifiedLog 🛰️) |
| **性能基线** | `baseline_llm.py` | 获取各 Provider 的 TTFT/TPS 基线数据 | - | ✅ |
| **资产同步** | `create_github_milestone_from_todo.py` | 将本地 TODO.md 自动映射为 GitHub Milestone | - | ✅ |
| **调试分析** | `trace_analyzer.py` | 聚合审计 `logs/` 目录下所有 UnifiedLog 链路 | - | ✅ |
| **覆盖审计** | `check_registration_coverage.py` | 自动化检测 scripts 资产登记情况与监控对齐度 | - | ✅ |
| **执行层验证** | `verify_batch_engine.py` | 验证基于 LangGraph 的 JobManager DAG 调度逻辑 | - | ✅ |
| **日常学习** | `run_daily_learning_cycle.py` | 运行每日自学习任务 | - | 已对齐 (UnifiedLog 🛰️) |
| **日常学习** | `run_daily_learning_cycle_with_retry.py` | 带重试机制的学习循环 | - | 已对齐 (UnifiedLog 🛰️) |
| **协同报告** | `generate_weekly_learning_report.py` | 生成协同学习周报 (CL-3) | - | 已对齐 (UnifiedLog 🛰️) |
| **缓存维护** | `clear_cache.py` | 清理语义缓存 (Semantic Cache) | - | 已对齐 (UnifiedLog 🛰️) |
| **身份管理** | `create_superuser.py` | 创建系统超级管理员 (admin) | - | 已对齐 (UnifiedLog 🛰️) |
| 🆕 **图谱记忆验证** | `test_agent_memory.py` | 验证 Agent Style Memory 写入与注入闭环 | - | ✅ |
| 🆕 **GraphRAG 验证** | `test_graphrag.py` | 验证 Hybrid GraphRAG 架构跳跃检索效果 | - | ✅ |
| 🆕 **技术债扫描** | `detect_timebombs.py` | 基于图谱依赖/测试关系检测高危零覆盖模块 | - | ✅ |
| 🆕 **Swarm 智能验证** | `verify_swarm_intelligence.py` | 验证多 Agent 协作推理与反思质量 | - | ✅ |
| 🆕 **复杂协作测试** | `test_complex_collaboration.py` | 端到端 Swarm 多角色协同场景测试 | - | ✅ |
| 🆕 **Swarm 评估矩阵** | `run_swarm_eval_matrix.py` | 批量评估 Swarm 跨场景表现 | - | ✅ |
| 🆕 **肠架构图** | `torture_cascading_acl.py` | ACL 级联权限边界压力测试 | GATE-SEC | ✅ |
| 🆕 **动态提示恢复** | `verify_dynamic_prompt_recovery.py` | 验证长上下文动态 Prompt 恢复机制 | - | ✅ |
| 🆕 **成本审计** | `audit_llm_costs.py` | 全系统 LLM 消耗金额统计与预警 | - | ✅ |
| 🆕 **知识新鲜度审计** | `audit_knowledge_freshness.py` | 识别 RAG 知识库中过期的陈旧文档 | - | ✅ |
| 🆕 **L3 能力看板同步** | `l3_dashboard_sync.py` | L3 智体能力自动化评测与看板生成 | GATE-L3 | ✅ |
| 🆕 **L4 过程完整性审计** | `gate_l4_process_integrity.py` | 推理链结构完整性审计 (Evidence/Friction/Truth) | GATE-L4 | ✅ |
| 🆕 **评测数据植入** | `ingest_eval_data.py` | 向评测向量库植入测试文档 | - | ✅ |
| 🆕 **评估图谱同步** | `sync_evaluation_to_graph.py` | 将评估体系节点/关系同步至 Neo4j 图谱 | - | ✅ |
| 🆕 **API 契约同步** | `export_openapi.py` / `sync-api.ps1` | **SSoT 驱动**: 将后端 Pydantic 模型同步至前端 TS 类型 | - | ✅ |
| 🆕 **规约入图** | `sync_governance_to_graph.py` | 把 Markdown 规约同步至 Neo4j，实现动态治理 | - | ✅ |

---

## 🏗️ 架构底座 (Core Architecture)

| 组件 | 对应设计/规则 | 描述 |
|------|--------------|------|
| **错误边界** | `ErrorBoundary.tsx` | 捕获组件渲染崩溃，提供自愈重置机制 |
| **权限卫兵** | `AccessGuard.tsx` | 细粒度的页面/功能位级 RBAC 拦截 |
| **统一响应** | `ApiResponse` (后端) | 遵循 `error_code / message / detail` 标准协议 |
| **治理韧性** | `DES-001-FRONTEND_ARCHITECTURE.md` | 前端架构权威设计说明书 (整合版) |
| **契约治理** | `DES-004-API_CONTRACT_GOVERNANCE.md` | **SSoT**: 前后端 Api 契约与类型治理规范 |
| **图谱治理** | `DEC-005-GRAPH_DRIVEN_GOVERNANCE.md` | **Graph-Driven**: 基于 Neo4j 的动态规约映射与自愈 |
| **全量计划** | `MASTER_GOVERNANCE_PLAN.md` | **Final Logic**: 全量治理、规约进化与刚性拦截路线图 |
| **验证体系** | `DES-002-TESTING_STRATEGY.md` | 全链路测试与质量保障策略 (整合版) |
| **评估体系** | `docs/evaluation/RAG_EVALUATION_FRAMEWORK.md` | RAG 三层分层评测 + LLM-as-Judge 偏差治理 |
| **评估体系** | `docs/evaluation/AGENT_EVALUATION_FRAMEWORK.md` | Agent 四层分层评测 (L1~L4) + 过程完整性审计 |
| **评估体系** | `docs/evaluation/EVALUATION_SYSTEM_AUDIT.md` | 评估体系深度审计报告 + 7 缺陷改造路线图 |
| **评估速查** | `docs/evaluation/METRICS_CHEATSHEET.md` | RAG 评测指标速查 + 诊断流程图 |
| **评估速查** | `docs/evaluation/AGENT_METRICS_CHEATSHEET.md` | Agent 评测指标速查 + L4 审计解读 |
| **设计系统** | `frontend-design` Skill | Cyber-Refined 赛博精致视觉规范 |

---

> 🔗 **关联索引**:
> - [TODO.md](TODO.md) — 任务优先级与进度
> - [docs/architecture/](docs/architecture/) — 深度设计文档
