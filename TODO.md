# 📋 HiveMind Intelligence Swarm — 开发 TODO 清单

> **⚠️ 强制规则**: 每次开发对话结束前，必须更新此文件。
> 任何"先不做"、"暂时跳过"、"以后再说"的内容必须记录在此。
>
> 🗺️ **完整开发计划**: [docs/ROADMAP.md](docs/ROADMAP.md) — 7 个里程碑 / 95 个任务 / ~35 天   
> 📄 **需求文档**: `docs/requirements/`
> 🛡️ **架构治理**: [开发治理准则](docs/governance/DEV_GOVERNANCE.md)
> 📦 **功能注册表**: [REGISTRY.md](REGISTRY.md)
> 🕒 **历史归档**: [docs/changelog/CHANGELOG.md](docs/changelog/CHANGELOG.md)

---

## 🚦 任务看板

| 维度 | Agent / 模块 | 核心待办 (Now / Next / Later) | 状态 |
| :--- | :--- | :--- | :--- |
| **路由层** | RAGGateway | [x] 意图预取 (Intent Scaffolding) & 4 层路由 (Arachne) | ✅ 已完成 |
| **执行层** | Workers | ⬜ 标签→Pipeline 动态分派 system (M3.1.5) | ⚠️ 观察到后端重启后服务挂死 |
| **存储层** | Memory Agent | [x] 知识库 Gap-Insight 自动诊断 (Radar Integration) | ✅ 已完成 |
| **治理层** | Governance Agent | [x] 治理页面(Settings/Audit)渲染修复 (Import/CSS Fixes) | ✅ 已修复 |
| **前端层** | AgentsPage | [x] Layout Locking 与 意图脉冲 (Arachne UI) | ✅ 已完成 |
| **评估层** | EvalPage | [x] RAG 6 指标质量评估引擎 + 报表导出 (M5.1~M5.2) | ✅ 已完成 |
| **协同层** | DebateOrchestrator| [x] L5 需求定界、多模型辩论引擎与优先级策略 (Priority & Multi-AI) | ✅ 已硬化 |
| **治理层** | GovernanceHook | [x] 强制事故上报系统 (Force Incident Recording) & 规约卫兵 (ContractGuard) | ✅ 已交付 |

---

## ✅ 已完成归档 (最近 Sprint)

### [2026-04-10] 系统加固与治理修复 (System Hardening & Governance Fixes)
- [x] **治理页面渲染修复**: 修复 `SettingsPage` 与 `AuditPage` 的缺失导入 (Flex, icon) 与 损毁 CSS 引用，恢复治理后台可用性。
- [x] **API 类型声明冷修复**: 修正 `settingsApi.ts` 中非法的 `bool` 关键字为 `boolean`。
- [x] **系统状态审计**: 诊断出后端服务在重启后未真正拉起，以及 SiliconFlow 模型 404 与 Token 段缺失 (JWT segments error) 等隐患。

### [2026-04-13] 网络连通性与权限同步加固 (Connectivity & Permission Hardening)
- [x] **跨域连接修复**: 修复 Windows 环境下 localhost 解析导致的 `ERR_CONNECTION_REFUSED`，通过绑定 `0.0.0.0` 及代理目标指向 `127.0.0.1` 解决。
- [x] **权限同步秒级生效**: 解决登录后菜单显示滞后的问题，实现登录成功后的 Profile 即时填充与路由守卫状态订阅。
- [x] **控制台警告清理**: 消除 `Typography.Text` 的非法 `block` 属性警告，并补全 PWA Meta 标签。

### [2026-04-12] 基础架构稳定性加固 (Infrastructure Stabilization)
- [x] **Swarm 核心方法回正**: 补全 `SwarmOrchestrator` 丢失的 `get_agents` 与 `invoke_stream` 方法，修复 500 崩溃。
- [x] **全局异常处理治理**: 在 `main.py` 注册异常处理器，确保所有 5xx 错误返回合规 JSON 并解决 CORS 头丢失风险。
- [x] **Ant Design v6 适配**: 迁移 `notification` 的 `message` 字段为 `title`，重构已弃用的 `List` 组件为 Flex 布局。
- [x] **401 死循环拦截**: 在 API 拦截器注入路由锁，防止认证失效后的重定向风暴。

- [x] **需求定界网关 (Scoping Gate)**: 落地 `ScopingAgent`，强制执行“前置确认”审计，并根据需求复杂度自动判定优先级 (Priority 1-5)。
- [x] **多模型辩论演进 (Multi-AI Debate)**: 升级 `DebateOrchestrator`，支持高优先级任务通过 GPT-4o/Claude-3/Gemini 等异构模型进行红蓝对抗，增加博弈多样性。
- [x] **模型方言适配 (Model Dialect Adaptation)**: 交付 `ModelDialect` 引擎，针对 Claude (XML)、DeepSeek (CoT) 等不同架构自动优化提示词结构与注意力锚点。
- [x] **黄金链路收割 (Elite Trace Harvesting)**: 交付 `EliteTraceHarvester`，自动提取高价值智体执行链路，为后续的“以大带小”蒸馏 (Distillation) 与模型微调准备高质数据集。
- [x] **智体评审经济学 (Agent Review Economics)**: 在 `ReviewerAgent` 中集成 `ReviewGovernance` 机制，依据任务优先级动态匹配评审模型（Elite/Balanced/Economy），并引入模型优劣势（Strengths/Weaknesses）与价格敏感型审计。
- [x] **日志闭环自演化 (Self-Evolving Logs)**: 交付 `ExperienceLearner`，实现从系统日志中自动“提取教训”，并将其反哺至 `ReviewGovernance` 实现动态策略修正。
- [x] **动态广度与时间配置**: 实现讨论轮数 (Rounds) 与 模型 Tier 随优先级自动阶梯化调整的治理策略。
- [x] **人机统帅接口 (Human Strategic Steering)**: 在 `SupervisorAgent` 中注入 `human_steer` 钩子，支持人类指令强行切断智体发散。
- [x] **跨集群辩论引擎 (Inter-Swarm Debate)**: 实现 `DebateOrchestrator` 支持并行提案与红蓝互审逻辑。
- [x] **L5 治理路线图固化**: 将 L5 核心治理原则写入 `docs/README.md` 与 `ROADMAP.md`。

### [2026-04-09] L4 自主进化与红蓝对抗 (L4 Autonomous Evolution & Adversarial Governance)
- [x] **L4 过程完整性网关**: 落地 `gate_l4_process_integrity.py`，支持思维链路审计与“认知不诚信”检测 (M4.2.4)
- [x] **L4 闭环自愈修复**: 升级 `SelfLearningService` 生成 `Cognitive Directive`，实现基于教训的动态规则注入 (M4.2.3)
- [x] **L4 行为熔断器**: 在 `SupervisorAgent` 中实现“知识真空”与“逻辑停滞”自动熔断保护 (M4.2.7)
- [x] **L4 认知升阶路由**: 联动 `MemoryBridge` 实现高风险任务自动升级模型 Tier 与审计强度 (M4.2.4)
- [x] **L4 红蓝对抗测试**: 交付 `AnarchyAgent` 模拟内鬼渗透，完成 3 轮治理鲁棒性演习并固化“安全治理宪法”

### [2026-03-31] 架构治理与 Code Vault (M7.1/M7.2 Architecture Resilience)

- [x] **M7.1 智能路由升级**: `ClawRouter` 实现 15 维动态评分矩阵，支持 Cost/Latency/Code 综合分流
- [x] **M7.1 治理观测**: `LLMMetric` 模型落地，支持 per-model 实时性能追踪
- [x] **M7.2 AST 解析集成**: 交付 `CodeStructureParser`，支持 Python 类、函数与文档字符串提取
- [x] **M7.2 Swarm 增强**: `IngestionOrchestrator` 接入 `CodeExtractorAgent` 节点，实现代码本体逻辑自动入图
- [x] **M7.2 双擎索引**: 实现 ES (文本) + Neo4j (结构) 代码资产解耦存储

### [2026-04-07] RAG 性能大会战 (Performance & Accuracy Breakthrough — M5.1/M5.2)

- [x] **Latency 4x 优化**: 交付 `ContextualCompressionStep` (M2.1H)，基于动态 Context Budget (45% ratio) 实现智能分层裁剪，耗时从 40s 降至 <10s
- [x] **架构解耦 (Direct-Memory)**: 重构 `GenerationContext` 彻底移除不稳定的 VFS/Broker 路径拦截，解决响应为 `None` 的核心逻辑漏洞
- [x] **深度对齐 (Critic-Logic)**: 修复 `steps.py` 中 f-string 转义导致的生成崩溃，注入 `retrieved_content` 至 Critic Agent，实现基于事实的自我修正
- [x] **远程向量激活 (ARAG-003)**: 修改 `ChromaVectorStore` 强制透传远程 ZhipuAI Embedding，绕过本地 `onnxruntime` 环境依赖死锁
- [x] **引用治理增强**: 强化 Drafting 指令，强制输出 `[N]` 证据链，RAG 评测分从 0.27 提升至 0.8+ (实测抽样)

### [2026-04-02] 架构硬化 (P0 Hardening — M7.3 Architecture Resilience)

- [x] **P0 核心沙箱加固**: 引入 `RestrictedPython` 实现 AST 层级安全隔离，增加 5s 强制超时与递归深度限制 (M7.3.1)
- [x] **P0 Token 预算系统**: 基于 `tiktoken` 落地 32K 五区预算管理(System/Memory/RAG/History/Output)与语义化自动截断 (M7.3.2)
- [x] **架构自省**: 完成 Sandbox 逃逸安全测试与 Token 边界压力测试

### [2026-04-02] P1 优先项交付 (Resilience & Intelligence Density — M7.4)

- [x] **P1 Ingestion 语义编译**: 交付 `EnricherAgent` 节点，实现在入库环节自动提取时间实体、语义标签、版本链与 Pulse 摘要 (M7.4.1)
- [x] **P1 Swarm Checkpointing**: 引入 `SqliteSaver` 持久化检查点，支持 Swarm 任务在后端重启后的 100% 状态恢复 (M4.2.9)
- [x] **P1 工具 Token 预估**: 为核心 RAG 工具增加 `concise` 模式与精准 Token 消耗预估返回，实现预算闭环 (M7.3.3)

### [2026-04-02] P2 协作进化 (Semantic Discovery & MCP Integration — M7.4)

- [x] **P2 语义 Skill 发现**: `ToolIndex` 升级为 Embedding 向量召回，智体现可通过语义理解发现 100+ 潜在原子技能 (M7.4.2)
- [x] **P2 MCP 标准落地**: 交付 `DatabaseServer` (FastMCP 实例)，实现结构化数据的标准化上下文注入与安全查询 (M4.2.10)
- [x] **P2 智体互联**: `MCPManager` 接入 Swarm 运行时，支持动态加载 external 工具集

### [2026-03-31] Swarm Chat 联调与 6 指标评估体系 (M4/M5 Synergy)

- [x] **Swarm Chat Backend**: 后端 `agents.py` 实现 SSE 流式端点，支持节点思考与消息增量同步
- [x] **Swarm Chat Frontend**: 交付 `SwarmChatPanel` 组件，集成玻璃拟态 UI 与 Action 动态按钮
- [x] **RAG 评估引擎升级**: `EvaluationService` 升级为 6 维评估模型 (F/R/P/Rec/Acc/Sim)
- [x] **Eval UI 全面更新**: `EvalPage` 支持 6 维雷达对比、QA 逐题明细分析与 HTML 报表导出
- [x] **资产注册**: `REGISTRY.md` 补录新 API 与组件，模型层同步更新

### [2026-03-31] 文档体系对齐 (Docs Alignment)

- [x] **CHANGELOG 补录**: 补录 v0.1.0~v0.5.2 共 6 个版本发布记录
- [x] **ROADMAP 交付标准**: 修复 M2/M4 交付标准 — 勾选已实现项，保留真实待办项
- [x] **REGISTRY 全面补登**: 新增 2 个图谱服务、3 个 API 路由、4 个前端页面、8 个验证脚本
- [x] **架构索引更新**: `architecture/README.md` 补录 6 份新文档导航
- [x] **TODO 对齐**: 任务看板细化、活跃任务更新

### [2026-03-31] 智体图谱记忆 (Agent Graph Memory)

- [x] **Hybrid GraphRAG**: `RAGGateway` 接入图谱架构跳跃检索，`Score: 0.95`
- [x] **Agent Style Memory**: `GraphIndexService` 写入/注入闭环，Neo4j 持久化
- [x] **技术债扫描**: `detect_timebombs.py` 基于图谱依赖 + 测试节点检测零覆盖高耦合模块
- [x] **架构文档**: 发布 `AGENT_GRAPH_MEMORY.md`、`SHOWCASE-GRAPH-DECOMPOSITION.md`、`GRAPH-ADVANCED-USECASES.md`

### [2026-03-26] 全方位的可观测性治理 (Unified Observability Promotion)

- [x] **基建验证**: 成功落地 `UnifiedLog` 强契约协议，单测 7/7 通过
- [x] **业务重构**: 完成 `ChatPage` 与 `KnowledgePage` 的"样板房"式重构
- [x] **安全封印**: `post-build.js` 自动隔离 SourceMap，本地 `debug_symbols` 归档
- [x] **调试利器**: 交付 `trace_analyzer.py` 并通过了 `drill-trace-999` 实战演推
- [x] **标准确立**: 发布 [Unified Observability Standard](docs/architecture/unified_observability_standard.md)
- [x] **量化拷打**: 完成 RAG 权限/投毒深度审计并归档至 [RAG-SECURITY-AUDIT-2026.md](docs/governance/RAG-SECURITY-AUDIT-2026.md)

### [2026-03-26] 智能协作 Swarm 架构升级 (M4.2 - Swarm Collaboration)

- [x] **Kernel 加固**: 在 `SupervisorAgent` 中集成 `SwarmMemoryBridge`
- [x] **记忆对齐**: 实现 Plan 阶段的 L1-L5 历史背景自动装载
- [x] **闭环持久化**: Swarm 成功执行后自动回写 L3 向量库与 Episodic 记忆
- [x] **专家增强**: 为 `ResearchAgent` 增加基于 LLM 的结果合成（Synthesis）阶段
- [ ] **多端联调**: 在 `/api/v1/swarm/chat` 端点暴露协作接口并对接前端 ← **M4 遗留**

### [2026-03-25] 文档系统对齐与架构治理 (Docs Transition to SSoT)

- [x] **SSoT 对齐**: 彻底清理并重建全站文档索引 (Index/README.md)
- [x] **前端核心层定义**: 在 DES-001 中补齐 `src/core` (Monitor, Intent, LocalEdge)
- [x] **治理规范确立**: 发布 GOV-001，定义 RDD 与 Phase Gate 审计规范
- [x] **后端架构大一统**: 整合碎片化设计，发布 [DES-003](docs/design/DES-003-BACKEND_ARCHITECTURE.md)
- [x] **AI UX 表达**: 发布 [AI_FRONTEND_STRATEGY](AI_FRONTEND_STRATEGY.md) 面向 AI 场景的技术白皮书
- [x] **运维对齐**: 整合 `backend/scripts/` 监控，接入 `UnifiedLog` 协议 (**100% 覆盖**)

### 🎯 Phase 4.1 完成项

- [x] **后端预感应支持**: 为 retrieval 接口实现 `is_prefetch` 参数，开启"轻量级预热"
- [x] **前端预测增强**: 在 IntentManager 中集成 AI Warmup 探测器
- [x] **HMER 自动化评分**: 交付 `scripts/check_registration_coverage.py` 自动计算 REGISTRY.md 对齐度

---

## 🛠️ 当前活跃任务 (Active — M4/M5 主线)

### M4 / M5 后续精进 (Refinement)

- [x] **V3 Trace 全链路可视化**: Query→改写→检索→Rerank→压缩→生成 完整 Trace 展示 (`M5.2.3`)
- [x] **Token 实时大屏**: 基于 `TokenUsage` 独立表的实时成本监控大屏 (`M5.2.1`)
- [x] **知识库使用分析看板**: 热门查询/冷门文档/使用趋势前端 (`M5.2.4`)
- [x] **并行协作 (Debate Mode)**: 实现 Supervisor 触发多智体并行工作与共识合成 (`M4.2.5`)
- [ ] **Swarm 策略 A/B 测试**: 支持在 `EvalPage` 直接对比不同 Swarm 策略的跑分结果

### 其他待办

- [ ] **断点续传联调**: 验证 `StreamManager` 与后端 `_resume_index` 协议的端到端闭环
- [ ] **GitHub Issues 迁移**: 将本 TODO.md 的活跃项迁移至 GitHub Projects
- [ ] **M2.3.5 审核台前端**: 文档审核/分块对比/批注页面 (Governance Agent 所需)
- [ ] **M2.4 权限落地验证**: ACL 全链路 E2E 测试 (`torture_cascading_acl.py` 已有基础)

### 🏗️ 架构硬化 (Harness & Knife Hardening — M7.3/M7.4)

- [x] **P0: 核心沙箱安全加固 (M7.3.1)**: 已落地 `RestrictedPython` 隔离层与 `SafeEnvironment`
- [x] **P0: TokenService 与 32K 预算系统 (M7.3.2)**: 已落地 `tiktoken` 五区预算管理与自动截断
- [x] **P1: Ingestion 管线 EnrichmentStep (M7.4.1)**: 已落地语义编译 Agent (Tags/Timeline/Pulse)
- [x] **P1: Agent 状态持久化 (Checkpointing)**: 已落地 `SqliteSaver` 检查点持久化
- [x] **P1: 工具响应 Token 预估**: 已为 RAG 工具增加 `concise` 模式
- [x] **P2: 语义化 Skill 发现与 MCP 迁移**: 已落地 `ToolIndex` 向量化与 `DatabaseServer` MCP 实例
- [ ] **RAG 环境补全**: 彻底修复后端 `.venv` 下的 `onnxruntime-directml` 路径冲突，或者全量迁移至远程 Embedding (M5.3)
- [ ] **幻觉熔断 (Hallucination Circuit Breaker)**: 在 `SelfCorrectionStep` 增加低分触发“重写查询并二次召回”的逻辑 (M5.2.5)
- [ ] **L3 智体能力测试 (Path A)**: 自动化 RAG 评分看板集成 (M5.3) 🚧
- [x] **L3 基础架构**: 交付 `l3_dashboard_sync.py` 与 `docs/evaluation/` 目录
- [ ] **L3 质量门禁**: 实现 `gate_l3_intelligence.py` 准入校验
- [ ] **Next Milestone**: 自动化回归测试与多环境部署验证
- [x] **REQ-015: L5 智体治理任务提报与图谱融合 (M6.1.4)** ✅ 已硬化
    - [x] Phase 1: 任务格式标准化与 TODO.md 扩展
    - [x] Phase 2: Neo4j Task 节点与关系定义
    - [x] Phase 3: TODO <-> Graph 双向同步脚本
    - [x] Phase 4: 前端治理任务展示面板 (已通过 E2E 稳定性加固)

---

## 🤖 智体提报任务 (Agent-Escalated Tasks)
- [x] **TASK-GOV-B6135DD5**: [治理演示] Neo4j 连接池耗尽风险预警 (Priority: P0) | [查看存根](docs\tasks\TASK-GOV-B6135DD5.snapshot.md)

- [x] **TASK-GOV-05898911**: [治理演示] Neo4j 连接池耗尽风险预警 (Priority: P0) | [查看存根](docs\tasks\TASK-GOV-05898911.snapshot.md)

- [ ] **TASK-GOV-BC6349A1**: [治理演示] Neo4j 连接池耗尽风险预警 (Priority: P0) | [查看存根](docs\tasks\TASK-GOV-BC6349A1.snapshot.md)


## 🐛 待修复 Bug / 风险追踪

- [x] **BUG-001**: 某些文档在 `view_file` 时被识别为 `unsupported mime type` (已通过全局 UTF-8 容错和 ParserRegistry 嗅探加固修复)
- [ ] **RISK-001**: 并发开发时 TODO.md 的合并冲突风险 (建议转向 GitHub Issues — **待迁移**)
- [ ] **RISK-002**: M2/M4 ROADMAP 交付标准仍有 4 条未勾选 (审核台前端 + ACL验证 + DAG可视化 + MCP外部工具)