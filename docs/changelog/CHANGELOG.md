# 📝 Changelog

## [Unreleased] — v0.6.x (M5+)

> 当前主线: M5 评估与可观测性推进 + M4 Swarm Chat 前端联调

---

## [v0.6.0] — 2026-04-08: Sprint "Arachne" (Architectural Reshaping)

### 🚀 核心突破: 零延迟感应与 4 层治理
- **[M5.2.1] 意图预取 (Intent Scaffolding)**: 实现了基于 WebSocket `partial_input` 的异步意图感应，在用户打字阶段自动触发 RAG 预热，TTFT 降低 300ms-800ms。
- **[M5.3.1] 4 层自适应路由**: 交付 `ClawRouter v2`，支持 Reasoning/Complex/Medium/Simple 四级级联，并引入 **RTT 动态降级** (Latency > 800ms 时自动缩减模型深度)。
- **[M5.3.3] 检索雷达 (RAG Radar)**: 实现了“电信即知识” (Telemetry as Knowledge)，支持从系统自省日志 (ReflectionLog) 中检索错误诊断信息，Agent 具备自我运行状况的感知能力。

### 🔧 架构加固
- **环境净化与标准对齐**: 全局强制 UTF-8 编码，统一脚本执行上下文 (setup_script_context)，解决了 Windows 环境下的字符崩溃遗留问题。
- **图谱深度融合**: 升级 `GraphRetrievalStep` 支持架构敏感的多跳拓扑遍历 (MAPPED_TO_CODE, DEFINES 等关系追踪)。
- **前端防抖 (Layout Locking)**: 交付 `ChatBubble` 布局锁定系统，支持 `Intent Pulse` 动画与 `X-Response-Sequence` 序列校验，彻底消除流式震颤。

### 🛡️ 安全与治理
- **Trace 对账**: API 响应头强制注入 `Response-Sequence` 与 `Timestamp`，支持前端精确对齐后端的流式状态帧。

---

## [v0.5.2] — 2026-03-31 (Agent Graph Memory)

### 🧠 智体图谱记忆 (Hybrid GraphRAG + Agent Style Memory)
- **Hybrid GraphRAG**: `RAGGateway.retrieve_for_development` 新增架构跳跃扩展，沿 `[:DEPENDS_ON]`/`[:DEFINES_MODEL]`/`[:EXPOSES_API]` 关系 1-2 跳扩展，`Score: 0.95` 权重注入
- **Agent Style Memory**: `GraphIndexService.record_agent_preference` 用 LLM 提炼用户吐槽为 `CognitiveAsset {type: 'Preference'}` 偏好节点，持久化至 Neo4j
- **偏好注入**: `get_agent_preferences` 在每次 Agent 开工前拉取信任阈值 >0.5 的偏好，注入 System Prompt 铁律集
- **技术债扫描**: `detect_timebombs.py` 基于图谱入度 + 测试节点关系，自动生成零测试覆盖高耦合模块报告
- **图谱案例文档**: 发布 `AGENT_GRAPH_MEMORY.md`、`SHOWCASE-GRAPH-DECOMPOSITION.md`、`GRAPH-ADVANCED-USECASES.md`

---

## [v0.5.1] — 2026-03-26 (全方位可观测性)

### 📊 统一可观测性架构 (Unified Observability)
- **UnifiedLog 协议**: 强契约标准落地，所有脚本/服务接入 `trace_id` 结构化日志，单测 7/7 通过
- **前端遥测加固**: `MonitorService.dispatchBeacon` 升级为 `fetch keepalive` + `sendBeacon` 双保险，TTFT 正则化匹配
- **SourceMap 隔离**: `post-build.js` 自动将 SourceMap 打包至 `debug_symbols/` (不上线)
- **链路分析**: 交付 `trace_analyzer.py`，支持跨文件 Trace 聚合与时间线重建
- **遥测接口**: 新建 `POST /api/v1/telemetry` 收口端点
- **安全审计**: 完成 RAG 权限/投毒深度审计，归档 `RAG-SECURITY-AUDIT-2026.md`
- **标准文档**: 发布 `unified_observability_standard.md`

---

## [v0.5.0] — 2026-03-26 (Agent Swarm 智体协作升级)

### 🐝 智体蜂巢 M4 全面升级
- **SwarmMemoryBridge**: `SupervisorAgent` 集成记忆桥，Plan 阶段自动装载 L1-L5 历史背景
- **闭环持久化**: Swarm 执行后自动回写 L3 向量库与 Episodic 记忆
- **ResearchAgent 增强**: 新增 LLM 驱动的 Synthesis 结果合成阶段
- **治理钻探**: `run_sg007_governance_drills.py` Steady/Spike/Chaos 场景验证熔断与降级通过
- **SmartGrep 服务**: `SmartGrepService` BM25 + Fuzzy 混合召回正式上线
- **Swarm 压力测试**: `torture_cascading_acl.py`、`torture_poisoning_v1.py` 等安全边界验证通过

---

## [v0.4.0] — 2026-03-25 (高级 RAG M3 + 文档对齐)

### 🚀 高级 RAG 能力 (M3)
- **Pipeline 可配置化**: `IngestionStepRegistry` + `PipelineConfig`，4 种内置 Pipeline 模板 (通用/技术/法律/数据)
- **GraphRAG IntegRation**: `EntityExtractionStep` LLM 三元组抽取 + 图谱社区检索，混合向量+图 Retrieval
- **上下文压缩**: `ContextCompressionStep` 抽取 Chunk 相关句，Token 节省 40%+
- **Lost-in-Middle 防护**: 重排文档顺序，最相关内容置首尾
- **用户反馈体系**: `AnswerFeedback` 模型 + `POST /chat/messages/{id}/feedback` + 前端 👍👎 UI
- **前端预取增强**: `IntentManager` 集成 AI Warmup 探测器，预感应支持 `is_prefetch` 参数

### 📚 文档体系 SSoT 对齐
- 重建全站文档索引，发布 `DES-001`/`DES-002`/`DES-003` 权威设计文档
- 发布 `GOV-001-DEVELOPMENT_GOVERNANCE.md` 开发治理规范
- 发布 `AI_FRONTEND_STRATEGY.md` AI 场景前端技术白皮书

---

## [v0.3.0] — 2026-03-10 (质量与安全 M2)

### 🛡️ 数据安全与质量体系 (M2)
- **脱敏引擎**: `DesensitizationService` 6 种脱敏方法 (掩码/星号/占位符/哈希/删除/替换)，5 类内置检测器 (手机/身份证/银行卡/邮箱/APIKey)
- **LLM 过滤**: 发送前 + 接收后的 Outbound Filter 双重扫描
- **标签体系**: `Tag`/`TagCategory`/`DocumentTag` 三表，AI 自动打标 + 手动打标
- **数据审核**: `DocumentReview` 模型，7 条自动规则引擎 (长度/重复率/乱码/空白率/格式/去重/敏感)
- **权限 ACL**: `DocumentPermission` 模型 + `PermissionFilterStep` 检索权限过滤
- **前端安全 UI**: 文档列表安全等级 🟢🟡🟠🔴 标签 + 脱敏策略配置页

---

## [v0.2.0] — 2026-03-01 (RAG 闭环 MVP M1)

### 🎯 端到端 RAG 能力 (M1)
- **高级分块**: `RecursiveChunkingStrategy` + `ParentChildChunkingStrategy` + 表格感知分块，替换 800 字符硬切
- **查询理解**: `QueryRewriteStep` + `HyDEStep` + 指代消解 + 路由选库
- **知识库搜索**: `POST /knowledge/{kb_id}/search` 检索接口 + BGE-Reranker 真实实现
- **RAG 问答集成**: 对话前检索 KB → 上下文注入 System Prompt，`[1][2]` 引用溯源
- **多轮记忆**: 滑动窗口历史消息传入 LLM，"它"/"刚才提到的"正确解析
- **前端搜索 UI**: `KnowledgeDetail` 搜索框 + 结果展示

---

## [v0.1.0] — 2026-02-15 (Foundation)

### 🏗️ 项目基础架构
- **项目初始化** — 创建整体项目结构和目录
- **后端框架** — FastAPI 应用骨架，包含 API 路由、数据模型、Schema
- **Agent 核心** — SwarmOrchestrator, SharedMemoryManager, LLMRouter, MCPManager, SkillRegistry, ExternalLearningEngine 框架
- **通信层** — WebSocket ConnectionManager, 消息协议定义
- **Skills** — 3 个 Skill 模板 (rag_search, web_search, data_analysis)
- **开发治理** — Rules, Workflows, REGISTRY.md, 文档体系
- **基础设施** — Docker Compose (PostgreSQL, Redis, ChromaDB, MinIO)

### 📋 初始需求文档
- REQ-001: Agent 蜂巢架构
- REQ-002: 共享记忆与自省机制
- REQ-003: 对外学习机制
- REQ-004: 多 LLM 路由
- REQ-005: MCP 与 Skills 系统
- REQ-006: 混合通信 (SSE + WebSocket)
- REQ-007: 开发治理与质量体系
