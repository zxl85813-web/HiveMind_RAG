# 📋 HiveMind RAG — 开发 TODO 清单

> **⚠️ 强制规则**: 每次开发对话结束前，必须更新此文件。
> 任何"先不做"、"暂时跳过"、"以后再说"的内容必须记录在此。
> 
> 🗺️ **完整开发计划**: [docs/ROADMAP.md](docs/ROADMAP.md) — 7 个里程碑 / 87 个任务 / ~30 天
> 📄 **需求文档**: REQ-001~010 见 `docs/requirements/`
> 🛡️ **架构治理**: ✅ `team-collaboration-standards`, ✅ `agent-design-standards`, ✅ `Git Hooks` 已合入并运转。
> 🧬 **架构参考**: [Anthropic Agent 工程模式参考手册](docs/architecture/anthropic_agent_patterns.md) — 源自 15 篇官方文档

> 📅 最后更新: 2026-05-06

---

## 状态标记

| 标记 | 含义 |
|------|------|
| ⬜ | 待做 (尚未开始) |
| 🟡 | 进行中 / 部分完成 |
| ✅ | 已完成 |
| 🔴 | 已废弃 / 不再需要 |
| 🐛 | 已知 Bug / 需要修复 |
| ⏸️ | 暂时搁置 (有明确原因) |

---

## 一、🔥 紧急 / 阻塞项 (Blockers & Tracking)

> 根据 `design-and-implementation-methodology.md` 的追踪规范，任何开发中遇到的中断必须记录于此。
> 格式: `- [ ] 🛑 BLOCKED: TASK_NAME - Reason: <具体问题详情>`


- [ ] 🐛 **BUG-004**: `batch/monitor.py` 使用同步 `Session(engine)` 而非 `AsyncSession`，在全异步的 FastAPI 应用中会阻塞事件循环。
  - **文件**: `backend/app/batch/monitor.py`
  - **修复方向**: 将所有方法替换为 `async with async_session_factory() as session`
  - **优先级**: 中（当前仅影响 Pipeline 监控写入性能，不影响主流程）



---

## 二、🏗️ 后端 — 待完成功能

### 2.0 多租户 / SaaS 化 (P0 #1) — 2026-04-30 本轮新增

- ✅ **Tenant + TenantQuota 模型** — `app/models/tenant.py`，`DEFAULT_TENANT_ID="default"` 兜底向后兼容
- ✅ **ContextVar 租户上下文** — `app/core/tenant_context.py`，跨 `asyncio.create_task` 自动继承
- ✅ **核心表加 `tenant_id`** — users / conversations / knowledge_bases / documents（migration `a1b2c3d4e5f6`）
- ✅ **可观测/审计加 `tenant_id`** — obs_ingestion_batches / obs_file_traces / obs_agent_spans / obs_hitl_tasks / audit_logs（migration `b2c3d4e5f6a7`）
- ✅ **请求边界绑定** — `get_current_user` 解析 JWT 后 `set_current_tenant(user.tenant_id)`
- ✅ **Swarm 入口** — `SwarmState.tenant_id` + `tenant_scope()` 包 `ainvoke / astream`
- ✅ **服务层 ACL** — `KnowledgeService.get_kb / list_kbs / check_kb_access` 强制 `tenant_id` 比较；跨租户返回 404 不泄露存在性；`ChatService` 同样
- ✅ **`require_admin` + `assert_tenant_owns`** — `app/api/deps.py` 新增辅助函数
- ✅ **Tenant 管理 API** — `/api/tenants` (admin) + `/api/tenants/_me/current`
- ✅ **三大单例 keyed-by-tenant** — `SemanticIdMapper / FlowMonitor / SkillMiner`
- ✅ **治理单例 keyed-by-tenant** — `RainbowRouter / ShadowEvalSampler`
- ⬜ **剩余模型 tenant_id 补强**（次优先级，按需补）：tags、evaluation、finetuning、pipeline_config、sync、security 子表（DesensitizationPolicy 等）
- ⬜ **Vector store collection 加租户前缀**（避免 ChromaDB 泄露）
- ⬜ **MCP 服务器按租户隔离**（每租户独立子进程或 namespace）
- ⬜ **Tenant 中间件** — 给非 JWT 路由（如 webhook）提供显式 `X-Tenant-Id` 解析
- ⬜ **前端租户切换** UI（`/api/tenants/_me/current` 已就绪）

### 2.0b 成本归因 + 预算闸门 (P0 #3) — 2026-04-30 本轮新增

- ✅ **TenantUsageDaily 模型 + migration** — `c3d4e5f6a7b8`，按 (tenant_id, date) 累计 prompt/completion/total/request/cost_usd_micro
- ✅ **TokenAccountant** — 进程内 `defaultdict` 计数器，零锁热路径；后台 30s flush 一次（`UPSERT … GREATEST` 防重复计数）
- ✅ **BudgetGate** — 在 `SwarmOrchestrator.invoke / invoke_stream` 入口检查 `max_tokens_per_day`，超额抛 `BudgetExceededError` (HTTP 429)；`default` 租户永不限制
- ✅ **BudgetCallbackHandler** — LangChain callback，自动从 ContextVar 读 tenant_id，`on_llm_end` 记录 `token_usage`
- ✅ **LLMRouter 接入** — 所有 `_create_llm` 实例都注入 `BudgetCallbackHandler`，跨 tier 全覆盖
- ✅ **后台 flusher** — `start_background_flusher / stop_background_flusher` 通过 `lifespan` 生命周期管理；shutdown 强制 final flush
- ✅ **配额缓存** — 60s TTL 内存缓存，避免每次 LLM 调用都查库；`PUT /tenants/{id}/quota` 自动失效缓存
- ✅ **Usage API** — `GET /tenants/_me/usage`、`GET /tenants/{id}/usage` (admin)、`POST /tenants/{id}/usage/flush` (admin)
- ✅ **Smoke test 验证** — 配额内放行 / 超额熔断 / 兄弟租户隔离 / default 不受限 / UPSERT 持久化 / 幂等 re-flush
- ✅ **Cost 计算精化** — `model_cost_table.py` 内置 30+ 主流模型 (GPT/Claude/Gemini/DeepSeek/Qwen/Kimi/local)，支持别名/前缀/大小写/未知 fallback；`BudgetCallbackHandler` 在 `on_llm_start` 捕获 model_name → `on_llm_end` 按真实价格计费
- ✅ **预算预警** — `TenantQuota.warn_threshold_pct` (default 80%)，跨阈值时写入 `audit_logs.action='budget_warning'` + 触发可注册的 `set_warning_sink(callback)`，每 (tenant, day) 仅 fire-once
- ✅ **$-spend 双路熔断** — `TenantQuota.max_cost_usd_micro_per_day` 与 `max_tokens_per_day` 任一触达即熔断 (HTTP 429)；migration `d4e5f6a7b8c9`
- ✅ **滑动窗口限流** — `app/services/governance/rate_limiter.py` `SlidingWindowRateLimiter`（deque[float] + cutoff），`TenantQuota.max_rpm/max_rps` 配置；`BudgetGate.check` 第 1 层防御（RPS/RPM），HTTP 429 + `Retry-After` header；migration `f6a7b8c9d0e1`
- ✅ **per-user / per-conversation 二级配额** — `TenantQuota.max_tokens_per_user_per_day` (按日) + `max_tokens_per_conversation` (lifetime)；`TokenAccountant._user_buckets / _conv_buckets` in-memory 计数；`BudgetCallbackHandler` 自动从 ContextVar 读 user_id/conv_id；`tenant_scope(..., user_id=, conversation_id=)` 在 swarm 入口绑定
- ✅ **前端 Usage 仪表盘** — `pages/UsagePage.tsx`，AntD `Progress` 进度条（token + $ 双轨，到阈值变橙、超限变红），`/api/tenants/_me/usage/history?days=30` 30 天 SVG sparkline（无图表库依赖），30s 自动刷新；侧边栏 `/usage` 入口
- ✅ **Smoke test 验证 (rate)** — 9/9 PASS：sliding window 触发/复位/隔离/disabled、gate 第 1 层 RPS 触发、per-user 触发但 sibling 未受影响、per-conversation 触发、default 租户始终通过

### 2.0c 租户密钥管理 (P0 #2) — 2026-04-30 本轮新增

- ✅ **`SecretBackend` 抽象** — `app/services/governance/secret_manager.py`，可插拔（默认 Fernet，预留 Vault/KMS 接口）
- ✅ **Fernet 加密 backend** — Master key 用 HKDF-SHA256 从 `settings.SECRET_KEY` 派生（可被 `SECRETS_MASTER_KEY` env 直接覆盖）；密文 + `hint` (`sk-...AbCd`) 入库，明文从不落盘
- ✅ **`tenant_secrets` 表 + migration `e5f6a7b8c9d0`** — 复合主键 `(tenant_id, key_name)`，受 `tenants.id` FK 约束
- ✅ **5 分钟内存缓存** — `get_secret_cached_only` 提供 sync 热路径访问；PUT/DELETE 自动失效；`ensure_loaded` 在 `get_current_user` 里预热当前请求的全部 provider key
- ✅ **LLMRouter 按租户注入** — `_tier_specs` 记录每 tier 的 (model, provider, temperature)；`get_model` 命中租户 → 查缓存 → 命中即返回 per-tenant `ChatOpenAI` 实例（按 `(tenant_id, tier)` 缓存复用）；`invalidate_tenant` 在密钥轮转时清掉旧实例
- ✅ **管理 API（write-only）** — `GET/PUT/DELETE /api/tenants/{id}/secrets[/{key_name}]`；`key_name` 白名单 `^[a-z][a-z0-9_]*(\.[a-z0-9_]+){1,3}$`；写后自动 `invalidate_tenant`
- ✅ **Smoke test 验证** — 9/9 PASS：encrypt/decrypt 往返、hint 掩码、PUT+GET、预热缓存、密钥轮转 + 缓存失效、LIST 仅返回掩码、DELETE 幂等、跨租户隔离、provider→secret-key 映射去重
- ⬜ **HashiCorp Vault backend** — 实现 `VaultBackend(SecretBackend)`，按 `set_backend()` 切换
- ⬜ **AWS KMS backend** — 同上
- ⬜ **审计** — 写 `audit_logs.action='secret_put|secret_delete'`，记录操作人 + 受影响 key_name（不含值）
- ⬜ **前端密钥管理 UI** — 仅显示 `hint` + `updated_at`，「rotate」按钮调用 PUT
- ⬜ **Master key 轮转 runbook** — 旧 key 解密 → 新 key 重加密的迁移脚本

### 2.1 知识库 RAG 核心

- ✅ **文件上传接口** — `POST /knowledge/documents` (全局上传)
- ✅ **文件关联接口** — `POST /knowledge/{kb_id}/documents/{doc_id}` (关联到 KB)
- ✅ **后台索引 Pipeline** — 解析 → 分块 → 向量化 → 存入 ChromaDB
- ✅ **OfficeParser** — 真实 PDF/DOCX 解析 (使用 PyMuPDF + python-docx)
- ✅ **ChromaVectorStore** — 本地 ChromaDB 向量存储实现
- ✅ **文本分块策略** — 已使用 LangChain `RecursiveCharacterTextSplitter` 和 `ParentChildChunkingStrategy` 实现语义分块
- ✅ **知识库检索 API** — `POST /knowledge/{kb_id}/search` 语义搜索接口 (集成了 Retrieval Pipeline)
- ✅ **RAG 问答集成** — 将检索结果注入 LLM Prompt 作为上下文
- ✅ **引用溯源** — 回答中标注来源文档和段落
- ✅ **文档删除** — 删除文档时同步清理向量数据库中的数据
- ✅ **大文件上传** — 现已改为流式分块读取，避免 OOM

### 2.1B Pipeline 可配置化 ⬜ (REQ-008)

> 📄 需求文档: `docs/requirements/REQ-008-rag-pipeline-quality.md`

#### Ingestion Pipeline（摄取流水线）
- ✅ **Pipeline 配置模型** — 数据库/YAML 存储 Pipeline 定义（步骤列表 + 参数）
- ✅ **Step 注册中心** — 类似 ParserRegistry，注册所有可用处理步骤
  - ✅ `OCR增强` (Via ImageParser) / ✅ `敏感信息脱敏` / ✅ `语义分块` / ✅ `向量化` / ✅ `质量检查` (Audit)
- ✅ **Pipeline 编排引擎** — 按配置顺序执行步骤，支持条件分支 (IngestionExecutor)
- ✅ **Pipeline Debug 日志** (2.1B) — 记录每个 Step 的处理结果，方便排查
  - ✅ 实现 `PipelineJob` 和 `PipelineStageLog` 数据模型
  - ✅ 在 `PipelineExecutor` 中注入生命周期钩子 (`on_stage_start`, `on_stage_end` 等)
  - ✅ 实现 `PipelineMonitor` 服务，自动持久化流水线轨迹到数据库
  - ✅ `IndexingService` 已集成 Monitor，支持全链路追踪
- ✅ **预设模板** — 内置 4 个核心 Pipeline 模板:
  - ✅ **通用文档流**: 通用解析 + 审计 + 安全脱敏
  - ✅ **技术文档流**: 针对 Markdown 和代码块优化的分块逻辑
  - ✅ **法律合同流**: 强制开启深度审计与隐私擦除
  - ✅ **数据表格流**: 针对 Excel/CSV 优化的行列感知处理
- ✅ **Contextual Retrieval (Situational Chunks)**: 给每个分块注入文档级背景 (Anthropic 文档启示)
- ✅ **Prompt Caching for Ingestion**: 降低 Situational Chunking 的成本
- ✅ **Contextual BM25 Integration**: 将 Situational Text 同时注入 BM25 索引
利用 Claude (Haiku) 为每个分块生成简短的文档关联背景（如：所属章节、文件名、日期、实体关联），然后再进行向量化与 BM25 索引。
- ✅ **前端 Pipeline 配置页** — 可视化拖拽编排 Pipeline 步骤
- ✅ **前端节点参数配置抽屉** — 动态配置算子内部参数 (Chunk Size / Desensitization Policy)
- ✅ **后端 Pipeline 执行引擎集成** — `indexing.py` 已完全重构为基于 PipelineExecutor 的模块化驱动

#### Retrieval Pipeline（检索流水线）
- 🟡 **Retrieval Pipeline 已有框架** — `services/retrieval/pipeline.py` 已实现三步管线
- ✅ **每个知识库可独立绑定检索配置** — Query改写策略、检索权重、Reranker 选择 (前端配置页已支持)
- ⬜ **检索策略 A/B 测试** — 对比不同配置的检索效果

### 2.1C 标签/分类体系 ⬜ (REQ-008)

- ✅ **Tag 数据模型** — `Tag`, `TagCategory`, `DocumentTag` 表 (Alembic migrated)
  - 预置分类: 文档类型 / 业务领域 / 安全等级 / 处理状态
- ✅ **标签 CRUD API** — 创建、查询、关联、删除标签
- ⬜ **标签-Pipeline 匹配规则** — 按标签自动选择处理 Pipeline
  - 例: 带 `legal` 标签的文档 → 法律合同 Pipeline
- ✅ **自动标签 (Auto-Tagging)** — 三种策略:
  1. 基于文件名/扩展名的规则标签 (✅ 已实现后缀识别)
  2. 基于内容的 AI 标签 (✅ 已实现在 Indexing 任务中由 LLM 自动推断主题)
  3. 基于知识库的继承标签 (文档继承所属 KB 的标签)
- ⬜ **前端标签管理 UI** — 标签创建管理 + 文档打标签界面

### 2.1D 数据质量审核 ⬜ (REQ-008)

#### 自动审核
- ✅ **DocumentReview 数据模型** — 审核记录表 (评分、状态、评论) (Alembic migrated)
- ⬜ **自动审核规则引擎**:
  - 最小内容长度 (≥ 100 字符)
  - 重复率检测 (分块重复 ≤ 30%)
  - 乱码检测 (非 UTF-8 字符 ≤ 5%)
  - 空白率检测 (无意义内容 ≤ 20%)
  - 格式完整性 (PDF 页数 > 0, DOCX 段落 > 0)
  - 内容哈希去重 (检查是否已有相同文档)
  - 敏感信息检测 (手机号/身份证/银行卡号)
- ⬜ **三档审核路由**: 自动通过 / 人工审核 / 自动驳回

#### 人工审核
- ✅ **审核任务队列 API** — 获取所有待人工审核的任务
- ✅ **审核详情页/列表** — 查看具体违反规则的项
- ✅ **状态联动** — 审核通过后，KBLink 自动恢复 indexing
- ✅ **M2.3.6 知识重叠度检测 (Knowledge Overlap Detection)** — 评估资料对 LLM 的增量价值
  - ✅ 自动生成探针 QA 对
  - ✅ 纯模型(无上下文)闭卷测试
  - ✅ 计算知识覆盖率并标记入库价值 (0.0-1.0)
  - ✅ 前端展示重叠度评分 (Overlap Score)

### 2.1E RAG 质量评估体系 ✅ (REQ-008)

> 采用 RAGAS 标准框架实现 MVP 版本

- ✅ **评估仪表盘前端 (EvalPage)** — 概览统计 + 测试集列表 + 评估报告列表
- ⬜ **Multi-Grader Evaluation System (M2.1E)**: 系统化集成三种评分器：
  - **Code-based (Deterministic)**: 运行 `pytest` / `linter` / `Schema` 校验。
  - **Model-based (LLM-as-a-Judge)**: 编写结构化 Rubric (红线准则)，如“是否泄露 PII”、“是否遵守架构分层”。
  - **Human-in-the-loop**: 构建打分界面供专家校准 LLM 评分器。
- ⬜ **Regression vs. Capability Suites**: 建立回归测试集（100% 通过要求，防止退化）与能力爬坡集（针对当前弱点，如“复杂图谱推理”）。
- ⬜ **Agent Harness Isolation**: 确保评估环境完全隔离，避免 git 历史或残留文件对模型产生“泄题”干扰。
- ✅ **Bad Case 追踪** — 对低分回答进行标注并辅助微调引导
- ✅ **知识库健康度** — 每个 KB 的综合评分和历次对比趋势图 (Health Score & Trend)

### 2.1F RAG 进阶能力 ⬜ (REQ-009)

> 📄 需求文档: `docs/requirements/REQ-009-rag-advanced.md`

#### 高级分块 (P1)
- ✅ **分块策略注册中心** — `ChunkingStrategyRegistry`，类似 ParserRegistry
- ✅ **父子分块 (Parent-Child)** — 小块检索 → 返回父级大块作为上下文
- ✅ **递归字符分割** — 按段落→句子→字符递归拆分
- ✅ **表格/代码感知分块** — 不拆开表格和函数体
- ✅ **Chunk 数据模型** — 需要 `parent_chunk_id` 自关联字段

#### GraphRAG — 知识图谱增强检索 (P1)
- 🟡 **Neo4j 已部署** — 配置和接口已有，但未用于 RAG 检索
- ✅ **自动实体抽取** — 用 LLM 从文档块中提取 (实体, 关系, 实体) 三元组, 并且存入 Neo4j,
- ✅ **图谱与知识库关联** — 每个 KB 有独立的子图命名空间 (通过 Node kb_id 实现隔离)
- ✅ **混合检索** — Vector + Graph Traversal 混合 (GraphRetrievalStep)
- ✅ **社区检测** — Leiden 算法聚类 (NetworkX Louvain/Greedy Modularity fallback) + LLM 社区摘要
- ✅ **前端图谱可视化** — 在 KnowledgeDetail 添加基于 react-force-graph 的图谱互动视图

#### 查询理解 (P1)
- ✅ **QueryPreProcessingStep 已完善** — 实现了针对查询的重写和意图处理
- ✅ **意图分类** — 事实查询 / 比较分析 / 总结概览 / 操作指令
- ✅ **HyDE** — 生成假设性答案，用答案的 embedding 去检索
- ✅ **查询路由** — 根据问题内容自动选择最相关的知识库 (`KnowledgeBaseSelector` via LLM)
- ✅ **指代消解** — 多轮对话中的 "它" "上面提到的" 等代词解析 (内置于查询重写)
- ✅ **查询分解** — 复杂问题拆分为多个子问题

#### 用户反馈闭环 (P1)
- ✅ **AnswerFeedback 数据模型** — 👍/👎/修正 (利用 Chat Message Rating)
- ✅ **前端 UI** — 每条 AI 回答下方 👍👎 按钮 + 修正面板 (内置于 ChatPanel)
- ✅ **反馈分析** — 👎 多的问题自动加入评估测试集 (Bad Cases 追踪)
#### “正向反馈”利用 (M2.1F)
- ✅ **Auto-Promotion**: High-quality (Liked) Q&A pairs are automatically converted to `EvaluationItem` entries.
- ✅ **User-Gold Dataset**: Dynamically growth of ground-truth testsets based on real-world user validation.
- ✅ **Few-shot Loop**: (Ready for integration) The newly created items are tagged and can be used as few-shot examples in RAG prompts.
- ✅ **M2.5 Multi-Model Collaboration & Evaluation** (Model Arena) <!-- id: 5 -->
    - ✅ EvaluationService orchestrating different generation models.
    - ✅ Cost and Latency tracking per model run.
    - ✅ Frontend Leaderboard (Arena) for performance comparison.
- ✅ **Performance & Caching (P2)** <!-- id: 7 -->
    - ✅ Semantic Caching (Tier 2/3) using vector similarity.
    - ✅ Implementation of `TokenService` using `tiktoken` for accurate counts.
    - ✅ Token usage tracking & cost estimation.
    - ✅ Latency measurement preserved in database.
    - ✅ Frontend visualization of performance metrics.

#### 安全与治理 (P1)
- ✅ **文档级权限 ACL** — `DocumentPermission` 模型，支持用户/角色/部门粒度
- ✅ **全系统安全审计** — `AuditLog` 记录所有敏感操作 (权限变更、非法访问)
- ✅ **角色/部门隔离** — 权限校验逻辑已集成部门 (Department) 和角色 (Role) 维度
- ✅ **导出审计** — 系统自动记录知识外发及导出行为 (通过 `log_audit` 方法)
- ✅ **安全治理中心 UI** — 提供审计日志查看与 ACL 配置概览

#### 数据脱敏体系 (P1) — REQ-010

> 📄 需求文档: `docs/requirements/REQ-010-data-desensitization.md`

- ⬜ **敏感信息分类定义** — PII (手机/身份证/银行卡/邮箱/姓名/地址) + BSI (金额/密码/API Key/内网IP/数据库连接串)
- ✅ **检测器注册中心** — `DetectorRegistry`，可插拔检测器:
  - ✅ `PhoneDetector` — 正则 `1[3-9]\d{9}`
  - ✅ `IDCardDetector` — 正则 `\d{17}[\dXx]`
  - ✅ `APIKeyDetector` — 匹配 `sk-xxx` / `api_key=xxx` 模式
  - ✅ `EmailDetector` / `BankCardDetector`
- ✅ **脱敏策略配置** — `DesensitizationPolicy` 模型
  - ✅ 支持 6 种脱敏方法: 掩码 / 星号 / 占位符 / 哈希 / 删除 / 替换
  - ✅ **精细化策略配置** — 支持每种类型的白名单 (Whitelist)、风险等级 (Severity) 以及自定义正则规则 (Custom Regex)
  - ⬜ 按知识库 / 全局配置不同策略
  - ⬜ 安全等级体系: L1(公开) → L4(机密)
- ✅ **Proactive AI Insights (M2.1I)**: AI suggests next steps after chat (Integrated)
- ✅ **AI-Driven Dataset Creation (M2.1D)**: Interactive guidance via Eval Architect Agent
- ✅ **Knowledge Base Health (M2.3)**: Stats and Trends UI (Completed)
- ✅ **Data Desensitization (M2.2)**: Finalize sensitivity labels and redaction rules (✅ Completed with structured rules & custom regex)
- ⬜ **Utilizing Positive Feedback (M2.1F)**: Auto-expand testset using 'liked' answers (P1)
- ⬜ **Adaptive RAG / Self-RAG (2.1F P3)**: LLM decides when to retrieve and self-corrects

#### 数据脱敏体系 (P1) — REQ-010
...
- ✅ **脱敏处理管道** — 基本框架已在 `Ingestion Action` 和 `chat_stream` (Outbound Filter) 实现
- ⬜ **安全仪表盘** — 敏感数据占比 / 趋势 / 排行

#### 上下文压缩 (P2)
- ⬜ **抽取式压缩** — 从检索块中提取与 Query 最相关的句子
- ⬜ **Lost in the Middle 优化** — 重排文档顺序，相关内容放首尾

#### 性能与缓存 (P2)
- ⬜ **语义缓存** — 相似问题返回缓存答案 (延迟 50ms vs 3000ms)
- ⬜ **Embedding 缓存** — 避免重复计算
- ⬜ **Token 用量追踪** — `TokenUsage` 模型，费率计算

#### 文档生命周期 (P2)
- ⬜ **增量更新** — 文档修改时仅重索引变更 Chunk
- ⬜ **文档过期 (TTL)** — 过期文档自动排除出检索结果
- ✅ **多来源同步** — Confluence / Notion / Git Repo 定时同步任务闭环联调实现

#### 自动审核与去重 (2.1D)
- ✅ **Auto-Audit Engine**: Robust rules for length, duplication, garble, and blank ratios.
- ✅ **3-Tier Routing**: Auto-approve high quality, filter sensitive/doubtful to Manual Review, reject low quality.
- ✅ **Integrated PII Detection**: Proactively flags sensitive information (PII density) during audit.
- ✅ **Content Dedup**: SHA-256 hash-based strict deduplication implemented.

#### 可观测性 (P2)
- ⬜ **LangFuse 集成** — RAG 全链路追踪
- ⬜ **检索质量监控** — 命中率、延迟、空结果率
- ⬜ **知识库使用分析** — 热门查询、冷门文档

#### 自适应 RAG (P3)
- ✅ **Adaptive RAG (Self-RAG)**: Supervisor dynamically decides whether to retrieve context or answer directly.
- ✅ **Graph Refactor**: Entry point moved to Supervisor; Retrieval is now a routeable strategy node.
- ✅ **Self-Refinement Loop**: Agents can report context quality issues, triggering re-retrieval via Supervisor.

#### 变更履历 RAG (P1) — REQ-011 ⬜
- ⬜ **ChangelogAwareParser**: 实现 Excel/Word 变更履历自动提取逻辑
- ⬜ **Context Multi-Stitching**: 将提取的变更信息 (Version/Date) 注入关联章节 Chunk 的 Metadata
- ⬜ **Changelog Summary Search**: 实现按时间、版本号、作者等条件的结构化 RAG 检索
- ✅ **GitHub Issues Sync**: 已同步 REQ-011 及子任务至 GitHub (Issue #1-#4)

### 2.1G RAG 治理与数据契约 ⬜ (NEW ARCH)

> 📑 参考文档: `docs/architecture/rag_data_interface_design.md` & `arag_microservice_governance.md`

#### Phase 1: 核心契约与网关 (P0)
- [x] ** 统一输出协议**: 创建 `app/schemas/knowledge_protocol.py` (KnowledgeResponse/KnowledgeFragment)
- [x] ** 实现 RAGGateway**: 建立 `app/services/rag_gateway.py` 作为知识检索的单一入口 (API Gateway 模式)
- [ ] ** 文档版本链基础**: 在 `Document` 模型中增加 `supersedes_id` 和 `is_active` 字段 (自洽性治理)
- [ ] ** EnrichmentStep 实现**: 在 Ingestion Pipeline 中增加语义增强步 (自动摘要、关键词提取、版本标记)

#### Phase 2: 三端消费者改造 (P1)
- ✅ **Agent 内部改造**: 重构 `SwarmOrchestrator._do_retrieval_work`，注入结构化 `KnowledgeResponse`（带 citations + confidence）
- ✅ **Skill Tool 升级**: 改造 `search_knowledge_base` tool，走 RAGGateway，返回带 `[^citation_id]` 标签的结构化文本
- ✅ **API 增强**: `/{kb_id}/search` 返回完整 `KnowledgeResponse`；新增 `POST /knowledge/retrieve` 智能多 KB 检索接口

#### Phase 3: 高级微服务治理 (P2)
- [x] ** KB 级熔断器**: 在 RAGGateway 中实现熔断逻辑，当某个 KB 连续失败时自动降级
- [x] ** 健康检查接口**: `GET /knowledge/{kb_id}/health` 返回 KB 质量评分与索引状态
- [ ] ** 变更通知总线**: 建立 Event Bus，文档更新时通知 Agent 刷新语义缓存
- [x] ** 权限细化**: 实现 Chunk-level 安全标签校验 (ACL 基础框架)

#### Phase 4: 极致性能与体验 (P3)
- [x] ** Semantic Cache**: 语义级别 Question-Answer 缓存 (Similarity > 0.95)
- [x] ** Embedding Cache**: 内存级 LRU 嵌入缓存，减少 API 调用
- [x] ** Context Optimization**: 实现 "Lost in the Middle" 结果重排算法
- [ ] ** Streaming UI 优化**: 增强打字机效果的流畅度与 Markdown 渲染性能

#### Phase 5: 服务治理与高可用 (Service Governance) ⬜
- ⬜ **读写分离与 CQRS 切分**: RAG Ingestion Pipeline (重IO) 与 Retrieval (低延迟读) 物理/微服务级别隔离，避免资源争抢。
- ⬜ **动态熔断器 (Circuit Breaker)**: 针对 LLM/ES/Neo4j 设置超时与错误率阈值，触发时自动降级 (Fallback)至本地轻量级或缓存数据，防止雪崩。
- ⬜ **分布式流控与压测**: 提供 API 路由级别的 Rate Limiting 与 Token 令牌桶机制配置。
- ⬜ **Agent-Native LLM 智能路由 (ClawRouter 模式)**: 引入多维度加权评分引擎（Token量、复杂度、响应速度等），动态决定 Agent 请求走 `Eco` (如 GLM-4-flash) 还是 `Premium` 模型。
- ⬜ **无感 LLM 降级容错**: 商业/主 API 不可用时，隐式回退至端侧开源模型或备用廉价线路，确保对话体验零中断。

#### Phase 6: 前端与交互韧性 (Frontend Resilience) ⬜
- ⬜ **组件级容错与断路 (Error Boundaries)**: Agent 流式请求失败时，停止空窗阻塞，展示可读的降级页面（例如离线/维护状态UI）。
- ⬜ **状态树切分 (State Segmentation)**: 剥离重度计算的渲染状态 (如 ForceGraph) 与高频交互状态 (Chat Stream)，避免连锁卡顿渲染。

#### 架构底座 (Philosophy Implementation)
- ⬜ **Skill 纯函数化审计**: 确保 `app/skills/` 下所有逻辑无状态、无副作用
- ⬜ **Agent 副作用隔离**: 统一由 `SwarmState` 和 `MemoryManager` 管理 Agent 的状态变迁
  - ⬜ **状态机入口规范化**: 每一个 Agent 节点必须定义明确的 Input/Output Schema (契约驱动)


### 2.1H Agent 架构增强 (Anthropic 文档启示) ⬜

- ✅ **Agentic Search Skills**: 实现 `grep`/`glob`/`head` 等 JIT 上下文获取工具
- ✅ **Dynamic Tool Loading**: 实现 `search_available_tools` 模式，降低 Context 负载
- ✅ **Programmatic Tool Execution**: 实现 `python_interpreter` 供 Agent 批量编排工具
- ✅ **Think Tool Integration**: 为所有 Agent 注入专用 `think` 工具，用于在执行复杂工具链前记录显式推理逻辑和多步计划。
- ✅ **Progressive Skill Disclosure**: SkillRegistry 解析 SKILL.md frontmatter，提供 Tier1 catalog / Tier2 inspect / Tier3 callable 三层；新增 `inspect_skill` Agent 工具与 `GET /agents/skills/{name}` 端点。
- ✅ **Semantic Identifier Mapping**: 新增 `app/services/semantic_id_mapper.py`，提供进程全局双向别名注册表 (sticky + bucketed counters + LRU)；UUID 转化为语义别名 `doc-rfc-2119-1` / `kb-marketing-2`，不同 slug 分桶计数保证可读。接入：`RAGGateway._make_citation` 发出的 `Citation.citation_id` 从 `kb8chars:src12chars#chunk` 换为 `doc-{slug}-{n}#chunk`；JIT 导航工具 (`kb_doc_head` / `kb_doc_chunk_range` / `kb_doc_grep`) 在边界调用 `mapper.resolve()`，Agent 传别名或原 UUID 均可；`kb_list_documents` 输出只露别名。烟雾测试：警潜 stickiness / bucketing / round-trip / citation 集成 6 项全通过。
- ✅ **Context Compaction Node**: Supervisor 节点调用 FAST LLM，把超过阈值的旧消息折叠为单条 SystemMessage 摘要 (`_compact_history`)。
- ✅ **Hybrid Reflection**: 在 Reflection 节点中集成 Linter、Schema 校验等硬规则验证，不完全依赖 LLM 裁判 (见 hard_rules.py)。
- ✅ **Contextual BM25 Integration**: 基于增强后的 Situational Chunks 构建高精度关键词索引。实现：`bm25_step.py` 走 weighted 融合 (dense=0.4 sparse=0.6) + CJK bigram。
- ✅ **Search Subagents**: 实现子智能体并行检索模式 (见 search_subagents.py + spawn_search_subagents 工具)。
- ✅ **Contextual Reranking (P0)**: RAGGateway 默认 `recall=max(top_k*20, 100)≤150`，pipeline RerankingStep 输出 `recall=X rerank=Y` 追踪。
- ✅ **Tool Result Clearing (Advanced Compaction)**: `_prune_messages` 已对 head ToolMessage 做 >150 字符摘要替换，仅保留 tool_call_id + 长度信息。
- ✅ **Just-in-Time (JIT) Context Navigation**: 新增 KB 级 `kb_doc_head` / `kb_doc_chunk_range` / `kb_doc_grep` / `kb_list_documents` 工具，引用扩展无需再走 RAG。

### 2.1J Agent 安全沙箱与生产治理 (Sandboxing & Reliability) ✅

- [x] ** Sandboxed Skill Runtime**: 基于 `SecuritySanitizer` 和 `ToolAuditor` 实现简单的沙箱规则。
- [x] ** Rainbow Deployment for Agents**: 参考 Anthropic 生产实践，建立“彩虹发布”机制 (见 governance/rainbow_router.py: sticky-by-conversation 哈希 + 加权环分配)。
- ✅ **Production Shadow Evals**: 在生产环境匹名运行“影子评估” (见 governance/shadow_eval.py: 不阻塞采样重跑 MultiGrader，ring-aware，进 audit log)。
- ✅ **Sensitivity Monitoring**: 改进内部可观测性，监控 Agent 决策模式 (见 governance/flow_monitor.py: 节点循环 / 工具滥用 / 重复同参检测，不看内容只看逻辑流)。

### 2.1I Agent 长期任务稳定性与可靠性 (Long-Horizon & Reliability) ✅ (除 Visual Verification)

- ✅ **Feature-based Scaffolding**: 实现基于数据库的任务记录器。Supervisor 初始化任务清单并持久化到 `swarm_todos` 表，Agent 强制按清单增量执行。
- ✅ **LangGraph State Checkpointing**: 集成 `MemorySaver` 为 SwarmOrchestrator 提供 Checkpoints，支持 `thread_id` (Conversation ID) 级别的状态持久化。
- ✅ **MCP "Code Mode" Bridge**: AST 验证 + ctypes 强中断的 Python 沙箱 (`app/services/sandbox/code_mode.py`)，替换不安全的 `exec()`；拦截 `import`/dunder/`open`，捕获 stdout，可注入大型工具返回数据供脚本过滤聊合。`python_interpreter` 工具已走新 runner。
- ✅ **Self-Evolving Skills**: `app/services/governance/skill_miner.py` 从成功会话的工具调用序列中挖含重复子串，生成带 `status: draft` frontmatter 的 SKILL.md 草稿到 `skills/_drafts/`，供人工审核后提升。
- ⬜ **End-to-End Visual Verification**: 为 Coding/UI Agent 集成 Puppeteer 视觉反馈，确保功能不仅“代码绿”而且“运行绿”。
- ✅ **Observability Trace Analytics**: `app/services/governance/trace_analytics.py` 在 FlowMonitor 上层输出 `TraceReport` (supervisor thrash / tool redundancy / cycle / runaway)；`GET /trace/{conversation_id}` API 暴露。

### 2.1K Code Vault (代码资产知识库) (P1) — REQ-012 ⬜

> 📄 需求文档: `docs/requirements/REQ-012-code-vault.md`

- ⬜ **基础设施扩展**: 数据库新增 `AssetReview` 记录表，Neo4j 新增 `CodeAsset` 节点支持状态机流动（Draft -> Cross-Reviewing -> Online -> Deprecated）。
- ⬜ **双引擎基座 (切分)**: ES/pgvector 负责海量代码片段和文档的语义匹配；Neo4j 构建代码本体依赖库（连通代码实现、功能设计、API设计文档）。
- ⬜ **多维度映射追踪**: 在图谱中建立清晰的 `(Developer)-[:WROTE]->(CodeAsset)` 和 `(Designer)-[:DESIGNED]->(API)` 关系。
- ⬜ **AI 打赏与正向反馈飞轮**: 当大模型成功引用了被用户赞(Liked)的底层资产时，自动给原代码/设计贡献者积分打赏奖励，形成防锈飞轮。
- ⬜ **专项资产防重收口**: 开发前强校验并提取 `SQL` 脚本库和 `Common Utils` (通用工具集)，入库前通过 AST 分析与语义哈希阻止“重复造轮子”。 
- ⬜ **定制化 Ingestion**: 开发 `CodeASTParserSkill` 和 `SwaggerIngestionSkill` 提取资产，区分 Common/Biz/SQL 类型。
- ⬜ **RAG 引擎适配**: 检索时强制高优注入相关的 `SQL` 和 `Common` 资产供 AI 参考，并过滤低质量/未审核代码。
- ⬜ **积分溯源回授**: 实现 AI 辅助生成代码后，对提供 Few-shot 上下文的源节点开发者给与积分打赏奖励飞轮。

### 2.1L 数据入库微服务与 Swarm 重构 (V3 Ingestion) ⬜ (REQ-013)

> 📄 详情参见开发日志: `docs/changelog/devlog/DEV-REQ-013-v3-architecture-refactor.md`
> 🏛️ 契约与断路参考: `docs/architecture/data_microservice_governance.md`

- ✅ **Phase 1: 监控与健康检查换核** 
  - 移除 Langfuse，开发基于 Redis + PostgreSQL 的极简溯源(FileTrace/AgentSpan)系统。
  - **[Governance]** 新增 KB 级健康检查接口: `GET /knowledge/{kb_id}/health` (结合检索精度与用户反馈评分)。
- ✅ **Phase 2: 任务分片与调度 (Task Sharding)** 
  - 引入 Celery/Redis 作为后台处理引擎，将 10 万大任务粉碎切分 (Sharding) 分发给独立 Worker。
- ✅ **Phase 3: Native Swarm 流水线与断路器 (Circuit Breakers)** 
  - 废弃僵化 `IngestionExecutor`，开发纯血 LangGraph 非线性 `IngestionOrchestrator`。
  - **[Governance]** 针对外部不可控数据源（如外部爬虫/解析失败），引发超过设定阈值的异常时，在节点间引入容错与熔断降级。
- ✅ **Phase 4: 全局隔离与人工抽检 (Data Isolation & HITL)** 
  - 建立抽检队列表暂存置信度低的数据（取代让系统强行消化）；将修正后的经验推入 Redis 黑板进行集群共享同步。
- ✅ **Phase 5: 清理遗留资产** 
  - 彻底移除旧版基于代码插件遍历的编排层（`IngestionExecutor`、`PipelineMonitor` 等）。
  - 已将 `knowledge.py` 预览接口切换至 V3 Observability 体系。

### 2.1N 全域治理图谱 (Universal Governance Graph, UGG) 🟡 (DES-015)

> 📑 设计说明书: `docs/design/DES-015-governance-graph-spec.md`

- 🟡 **Phase 1: 基础构建与血缘补全** 
  - ✅ **UGG 规格定义** — 完成 DES-015 架构设计，定义四维空间模型。
  - 🟡 **UGG 集成引擎 (`sync_pgg.py`)** — 初始化骨架，支持多源同步。
  - ⬜ **Git 血缘同步** — 提取 Commit 链，建立 `Commit -> File` 与 `Developer -> Commit` 关系。
  - ⬜ **GitHub 管理同步** — 同步 Issue/PR/Review，关联 `Issue -> Requirement` 与 `Review -> Commit`。
  - ⬜ **Agent 归因同步** — 将 `AgentAction` 动作关联至生成的代码与执行的评审。
- ⬜ **Phase 2: 动态完整性审计 (Integrity Guard)**
  - ⬜ **Orphan 检查 (G-01)** — 拦截无 Issue 关联的 Commit。
  - ⬜ **Coverage 检查 (G-02)** — 拦截无测试覆盖的新增函数。
  - ⬜ **Provenance 检查 (G-03)** — 拦截来源不明的 AI 生成代码。
  - ⬜ **Approval 检查 (G-04)** — 拦截未经承认者审核的核心变更。
- ⬜ **Phase 3: 可视化与复盘仪表盘**
  - ⬜ **血缘追踪视图** — 前端展示“从需求到代码”的完整拓扑路径。
  - ⬜ **治理合规性报告** — 实时统计项目研发流程的健康度得分。

> [!TIP]
> **V3 Swarm 架构已正式上线**。系统现在具备极高的并行处理能力（Celery），并拥有原生 LangGraph 驱动的灵巧 Agent 协作能力。


### 2.1M Agent Builder Assistant (智能辅助构建工具) 🟡 (REQ-014)

> 📄 需求文档: `docs/requirements/REQ-014-agent-builder-assistant.md`
> 🏛️ 设计说明书: `docs/design/DES-014-agent-builder-assistant.md`

- ✅ **Phase 0: 需求发现与测试集共创 (Discovery & Co-Creation)** 
  - ✅ 设计 6 阶段访谈协议与 LangGraph 图谱 (`BuilderGraph`)。
  - ✅ 设计反顺从/反膨胀 (`Anti-Sycophancy`) 的护栏规则与 `scope_guardian_node`。
  - ⬜ 实现 `BuilderChatService` 与 `testset_creation_node` 引导用户提取 Golden Dataset。
- ⬜ **Phase 1: 模板引擎与配置生成 (Templates & Generation)**
  - ⬜ 集成 `SkillRegistry` 和 `SwarmOrchestrator` 实现实例库搜索与动态匹配。
  - ⬜ 开发 Meta-Prompt 自动生成 `AgentConfig` 并映射至数据库 `AgentDraft`。
- ⬜ **Phase 2: 沙箱测试与脚手架评估 (Sandbox & Harness)**
  - ⬜ 开发 `HarnessService`，基于测试集创建自动化的 `EvalHarness`。
  - ⬜ 更新 `SandboxService` 以哨兵模式捕获结果，并结合 `CostTracker` 执行成本熔断。
  - ⬜ 实现 A/B 测试面板与 Tokens 消耗实时展示。
  - ⬜ 在前端沙箱中实时渲染执行 DAG 图谱。


### 2.2 对话与 AI 核心

- ✅ **SSE 流式对话** — `POST /chat/completions` (已基本实现)
- ✅ **会话 CRUD** — 创建、列表、详情、删除
- ✅ **RAG 上下文注入** — 对话时自动从关联 KB 检索相关文档片段 (通过 Swarm 检索节点)
- ✅ **多轮对话记忆** — 将历史消息传入 LLM（滑动窗口传递消息）
- ✅ **Prompt 模板管理** — 系统 Prompt 已改为可配置模板 (PromptEngine)

### 2.3 Agent 系统

- ✅ **SwarmOrchestrator** — Agent 蜂巢编排（MVP 级别）
- ✅ **SharedMemoryManager** — 共享记忆管理器
- ✅ **TODO / Reflection API** — 蜂巢 TODO 列表和自省日志接口
- ✅ **Supervisor 路由引擎** — Agent 间的智能任务分配 (SwarmOrchestrator 已实现意图路由)
- ✅ **Agent 并发调度** — 基于 LangGraph 的多 Agent 批处理机制 (Batch Engine & DAG)
- ✅ **Agent 执行追踪** — 记录每个 Agent 的执行链路 (用于前端 DAG 可视化)

### 2.4 外部学习

- ✅ **订阅 CRUD 接口** — 已实现
- ✅ **发现列表接口** — 已实现
- ⬜ **实际爬取引擎** — 定时从 GitHub/HN/ArXiv 拉取技术资讯
- ⬜ **相关性评估模型** — 用 LLM 评估新技术与项目的匹配度

### 2.5 后端基础设施

- ✅ **统一异常处理** — `AppError` 层级 + 全局处理器
- ✅ **JWT 认证框架** — `security.py`
- ✅ **统一响应格式** — `ApiResponse` 封装
- 🐛 **依赖安装不完整** — `PyMuPDF` (`fitz`) 和 `python-docx` 需要手动安装
  - 命令: `pip install PyMuPDF python-docx`
  - 应添加到 `pyproject.toml`
- ✅ **数据库迁移** — Alembic 已规划并执行 `alembic init` 和 `revision`
- ✅ **Prompt Registry** — 已在 `app/prompts` 下实现 (loader.py, engine.py)
- ⬜ **CRUD Service 基类** — 所有 Service 应继承统一基类
- ⬜ **分页响应** — 所有列表 API 应支持分页

---

## 三、⚛️ 前端 — 待完成功能

### 3.1 国际化 (i18n)

- ✅ **i18n 基础框架** — i18next + react-i18next + 语言检测
- ✅ **全局导航 (AppLayout)** — 已翻译
- ✅ **仪表盘 (DashboardPage)** — 已翻译
- ✅ **知识库列表 (KnowledgePage)** — 已翻译
- ✅ **知识库详情 (KnowledgeDetail)** — 已翻译
- ✅ **Agent 蜂巢页 (AgentsPage)** — 已翻译
- ✅ **技术动态页 (LearningPage)** — 已翻译
- ✅ **系统设置页 (SettingsPage)** — 已翻译
- ✅ **聊天面板 (ChatPanel)** — 已翻译
- ✅ **创建知识库弹窗 (CreateKBModal)** — 已翻译
- ✅ **Mock 开关组件 (MockControl)** — 已翻译

### 3.2 功能完善

- ✅ **知识库文件上传 UI** — Upload.Dragger + 状态反馈
- ✅ **Mock 数据系统** — MSW handlers 已实现
- ⬜ **知识库搜索/问答 UI** — 在 KnowledgeDetail 中增加搜索输入框
- 🟡 **文档预览** — 已实现 Trace Modal 中的分块预览，并支持点击文件名高亮跳转至知识库
- ✅ **Agent DAG 可视化** — 实时展示 Agent 执行链路
- ✅ **前端通信 Hooks** — `useSSE`, `useWebSocket`, `useChat`
- ✅ **ErrorDisplay 组件** — 统一错误展示
- ✅ **LoadingState 组件** — 统一加载态
- ✅ **ConfirmAction 组件** — 统一确认弹窗
- ✅ **Generative UI 面板** — 流式打字机效果、Agent思考过程(手风琴折叠)、支持 Markdown HTML 渲染
- ✅ **AI-First UI (Phase 2)** — 实现 REQ-008 中定义的 AI 优先交互
  - ✅ **永驻 Chat 面板** — 布局右侧持久化显示，支持折叠与宽度调整
  - ✅ **情境感知建议 (Contextual Prompts)** — 输入框上方根据当前页面展示 AI 建议
  - ✅ **AI Action 系统** — 支持 AI 触发导航、打开特定 Modal（如创建知识库）
  - ✅ **全局 Modal 联动** — AI 动作可触发全局组件（CreateKBModal）
  - ✅ **模式切换** — AI 居中模式 (AI-centric) 与 经典导航模式 (Classic)

### 3.3 设计与体验

- ✅ **Cyber-Refined 设计系统** — CSS 变量 + 毛玻璃 + 渐变
- ✅ **响应式布局** — AI-First 布局
- ⬜ **暗色/亮色模式切换** — 当前仅有暗色模式
- ⬜ **移动端适配** — 侧边栏折叠、Chat 面板浮动

## 四、⚡ Phase 6: 性能优化 (Performance) — 进度跟踪

- ✅ **并行检索 (Parallel Retrieval)** — `HybridRetrievalStep` 支持并发查询多个 KB 与扩展 Query
- ✅ **上下文压缩 (Contextual Compression)** — 新增 `ContextualCompressionStep` 抽取式压缩 Context，节省 Token
- ✅ **显存/显量管理 (Token Budgeting)** — `SwarmOrchestrator` 实现基于字符预算的激进消息剪枝
- ✅ **SQL 查询优化** — 解决 `ChatService` 会话列表 N+1 查询问题，并增加 `TodoItem` 索引
- ✅ **异步预热 (Async Pre-warming)** — `SwarmOrchestrator` 实现推测式并行检索，并跳过冗余节点
- ✅ **SSE 批次优化 (SSE Batching)** — `ChatService` 支持数据包微批次发送，大幅降低网络开销
- ⬜ **MCP 智能路由** — 根据 Tool 描述自动选择最优 MCP 节点

---

## 五、🧪 测试 — 待完成

- ✅ **E2E 测试框架** — Playwright 已集成
- ✅ **集成测试矩阵** — `integration.spec.ts` 已创建
- ⬜ **后端单元测试** — 所有 Service / Route 的 pytest 用例
- ⬜ **前端组件测试** — Vitest + React Testing Library
- ⬜ **API 契约测试** — 前后端接口一致性验证

---

## 五、📐 架构与规划 — 讨论记录

> 以下是历次对话中讨论过但尚未落地的架构决策。

### 5.1 已确定方案 (待实现)

| 编号 | 决策 | 讨论时间 | 状态 |
|------|------|---------|------|
| D-001 | SSE + WebSocket 混合通信方案 | 2026-02-15 | ✅ ADR 已写，代码已实现 |
| D-002 | ChromaDB 作为本地开发向量库，生产用 ES | 2026-02-22 | ✅ 已实现双引擎切换 |
| D-003 | Alembic 数据库迁移 | 2026-02-15 | ✅ 已实现配置并生成初始迁移 |
| D-004 | Prompt Registry 集中管理 Prompt | 2026-02-15 | ✅ 已实现 (在 app/prompts 下) |
| D-005 | 前端 Mock ↔ 真实 API 一键切换 | 2026-02-15 | ✅ MSW + run_mock.bat |

### 5.2 待讨论事项

- ⬜ **Agent 通信协议** — Agent 之间用什么格式传递消息？JSON Schema？Protobuf？
- ⬜ **多租户设计** — 是否需要支持多用户隔离？
- ⬜ **Skill 沙箱执行** — 如何安全执行用户自定义 Skill？
- ⬜ **MCP Server 热插拔** — 如何无需重启就加载新的 MCP Server？
- ⬜ **LLM Fallback 链** — 主模型挂了之后的降级策略

---

## 六、🐛 已知问题 (Known Issues)

| 编号 | 问题 | 文件 | 发现时间 | 状态 |
|------|------|------|---------|------|
| BUG-001 | `list_kbs` 使用硬编码 `mock_user_id` | `routes/knowledge.py:56` | 2026-02-22 | ✅ 已修 |
| BUG-002 | `link_document` 返回值未包裹 `ApiResponse` | `routes/knowledge.py:132` | 2026-02-22 | ✅ 已修 |
| BUG-003 | MinerUParser 仍然是 Mock 实现，返回假数据覆盖了 OfficeParser 真实解析 | `plugins/mineru_parser.py` | 2026-02-22 | ✅ 已修 |
| BUG-004 | 大文件上传 OOM (全量读入内存) | `routes/knowledge.py:91` | 2026-02-22 | ✅ 已修 |
| BUG-005 | 端口 8000 占用导致 `WinError 10013` | `run.bat` | 2026-02-22 | ✅ 已修 (改 127.0.0.1) |
| BUG-006 | IDE Pyre2 报大量 "Could not find import" | 多个后端文件 | 2026-02-22 | ⏸️ IDE 配置问题，不影响运行 |

---

## 七、📦 依赖安装备忘

### 后端 (需在 .venv 中)
```bash
# 已安装
pip install fastapi uvicorn sqlmodel chromadb sentence-transformers aiosqlite aiofiles loguru zhipuai pydantic-settings

# 需要安装 (新增的 OfficeParser 依赖)
pip install PyMuPDF python-docx
```

### 前端 (需在 frontend/ 下)
```bash
# 已安装
npm install i18next react-i18next i18next-browser-languagedetector
```

---

## 八、📝 变更日志 (按日期倒序)

### 2026-05-06
- ✅ **Agent 测试工作坊与沙盒 (Agent Test Studio & Sandbox)**:
  - **AgentCard 升级**: 为 Custom 与 Built-in 所有 Agent 引入了 `onTest` 独立回调和带有 `ExperimentOutlined` 图标的“测试”按钮。
  - **AgentTestStudio 专属组件**: 开发了功能极其丰富的测试沙盒控制台，涵盖四大核心模块：
    - *提示词调试与沙盒 (Sandbox)*: 提供可编辑的全局 System Prompt 以及 Model Hint 微调选项，结合实时的 Agent Swarm 决策与 RAG 检索踪迹。
    - *A/B 对抗测试区 (Arena)*: 实现了两个 Agent 实例的并行对决，支持自定义对比问题、模型规格以及提示词微调，实时输出延迟、Token 消耗和 RAGAS 智能评分。
    - *运行日志与链路 (Traces)*: 可视化 LangGraph 的节点跳转序列 (pre_processor → supervisor → agent_node → reflection)，支持查看详细 payload 参数。
    - *评估测试报告 (Reports)*: 结合 RAGAS 规范和 Bad Cases 检测列表，展示运行成功率、平均调用耗时、健康度趋势。
  - **AgentsPage 页面集成**: 在 Agent 管理后台无缝挂载了 `AgentTestStudio` 组件，成功消除原先只能在侧边栏聊天框测试的单一交互，实现了开箱即用的闭环测试环境。
- ✅ **基础认证与固定用户数据库播种 (Database Seeding & JWT Auth)**:
  - **后端路由与数据库播种**: 新建 `auth.py` 路由，提供了 JSON 载荷验证的 `/login` 登录接口和获取当前登录用户信息的 `/me` 接口。在 `__init__.py` 中完成统一注册。
  - **固定用户播种**: 在 `init_data.py` 中增加了对 `admin` 用户的初始化逻辑，无论是在 DEBUG 还是在生产模式下，启动时都会检测 `admin` 用户是否存在，不存在则使用 `admin123` 密码自动注册播种。
  - **BCrypt 兼容性漏洞修复**: 修复了由于 `passlib` 和新版本 `bcrypt` 不兼容引发的 `ValueError: password cannot be longer than 72 bytes` 报错。采用直接引用 `bcrypt` 进行密码哈希与匹配，从根本上移除了不稳定的 `passlib` 依赖，保证了系统启动时的零卡顿与绝对稳定性。
  - **远程一键构建与部署**: 在远程 Azure 服务器上完成了新文件和新路由的上传和一键编译（`docker compose ... up -d --build backend`）。
  - **健康检查与接口双向通过**: 经验证，远程服务器 API 成功以 200 返回 `{"status":"ok"}`。且通过本地 Python 进行端到端请求测试，成功通过 `admin/admin123` 获取了 200 OK 以及正确的 Access Token 载荷！

### 2026-04-30
- ✅ **2.1I Long-Horizon 三件套**:
  - **MCP Code Mode Bridge** (`app/services/sandbox/code_mode.py`): AST 验证的 Python 沙箱，在语法树层拒绝 `import` / dunder 属性访问 / `open()` / `exec()` / `eval()` / `__builtins__`；只露安全 builtins 白名单 (math/json/re/datetime/itertools/statistics + 基础型)；stdout 重定向捕获；独立线程 + ctypes `PyThreadState_SetAsyncExc` 硬中断超时脚本 (`while True: pass` 300ms 可杀)；`run(code, inject={}, timeout_s=5)` 允许注入大型工具返回数据让脚本过滤。替换原不安全的 `python_interpreter` 实现。
  - **Trace Analytics** (`app/services/governance/trace_analytics.py`): 从 FlowMonitor 话题里提取 `TraceReport`，检测 supervisor thrash (访问多但 unique agent 少)、tool redundancy (同工具 args 重复)、继承 FlowMonitor 已报的 cycle / runaway / abuse 事件；`GET /trace/{conversation_id}` API 暴露 (路由挂载在 `/api/v1/trace/{conv_id}`)。
  - **Self-Evolving Skill Miner** (`app/services/governance/skill_miner.py`): 记录会话级工具调用序列；面向成功会话挖长度 2-5 重复子串 (默认 support ≥ 2 会话)；优先输出较长高支持模式；`flush_to_drafts()` 生成带 `status: draft` frontmatter 的 SKILL.md 到 `skills/_drafts/<slug>/`，以人工审核为闸门。全部三个模块的烟雾测试都跳的是本地代码路径，无需网络 / 模型调用。

### 2026-04-29
- ✅ **2.1G Phase 2 三端协议统一**: Knowledge Protocol 升级到 v2 (citations + confidence + extensions)；RAGGateway 接入真实 RetrievalPipeline (此前 `_retrieve_from_single_kb` 为 stub 假数据)；Swarm `_do_retrieval_work` 改走 Gateway 并保留结构化 fragments；`search_knowledge_base` tool 输出带 `[^citation_id]` 的可引用 markdown；新增 `POST /knowledge/retrieve` 多 KB 智能检索端点。
- ✅ **2.1H Anthropic 增强 Wave 1**:
  - **Contextual Reranking (P0)**: Gateway 默认召回提升至 `min(top_k×20, 150)`；RerankingStep 输出 `recall=X rerank=Y` 追踪标记。
  - **JIT Context Navigation**: 新增 `kb_doc_head` / `kb_doc_chunk_range` / `kb_doc_grep` / `kb_list_documents` 四个 KB 级 JIT 工具，Agent 引用扩展无需再走 RAG。
  - **Progressive Skill Disclosure**: SkillRegistry 解析 SKILL.md frontmatter，提供 Tier1 catalog / Tier2 inspect / Tier3 callable 三层；新增 `inspect_skill` Agent 工具与 `GET /agents/skills/{name}` 端点。
  - **Context Compaction Node**: Supervisor 节点新增 `_compact_history`，超过 18 条消息或 14k 字符时调用 FAST LLM 把旧消息折叠为单条 SystemMessage 摘要。
- ✅ **2.1H Anthropic 增强 Wave 2**:
  - **C3 Search Subagents**: 新增 `app/agents/search_subagents.py`，提供 `SubagentSpec` / `SubagentReport` 协议与 `run_search_subagents` 驱动；用 `asyncio.gather` 并行 fan-out 隔离上下文的子 Agent，每个子 Agent 拥有独立短工具循环 (默认 3 turn) 与基线 RAG 召回兜底；通过 `spawn_search_subagents` LangChain 工具暴露给 Supervisor，主 Agent 在遇到 2-6 个独立子问题时直接 fork。NATIVE_TOOLS 总数 12 → 13。
  - **Hybrid Reflection (反同源偏差)**: 新增 `app/services/evaluation/hard_rules.py`，提供 6 条确定性硬规则 (非空 / 协议词泄漏 / JSON 块合法性 / PII 泄漏 / 长度 / 引用 ID 解析)；MultiGraderEval 在 LLM 评分前先跑硬规则，失败则强制 `verdict=FAIL` 并阻止该响应进入语义缓存；`_reflection_node` 把 `state.retrieval_trace.citations` 的 ID 集合传入校验，杜绝悬空引用。烟雾测试覆盖 PII / 引用合法性 4 用例全通过。
  - **C6b Contextual BM25 (Anthropic Contextual Retrieval)**: 新增 `app/services/retrieval/bm25_step.py`，自包含 Okapi BM25 (k1=1.5, b=0.75, 无新依赖)；分词器同时输出英文词 token 和 CJK 字符二元组，让中文查询也能拿到稀疏信号；支持 `metadata.contextual_summary` 作为可选上下文前缀，给后续摄入侧 contextual prefixing 留接口；rank fusion 用 weighted normalized score (dense=0.4, sparse=0.6) 而非朴素 RRF —— 在 5–150 的小召回池上 RRF 无法让单个强稀疏命中翻盘，这套方案能让 RFC-2119 / 错误码 / 中文 keyword 等精确命中真正爬到首位。装在 `Hybrid → ContextualBM25 → ACL → Rerank` 之间，把更好的初始顺序喂给 cross-encoder。烟雾测试 EN+CN 双场景命中文档均正确升至 #1。  - **C7 Semantic Identifier Mapping**: 新增 `app/services/semantic_id_mapper.py` 进程全局双向别名注册表 (sticky / bucketed counters / LRU 5000)，UUID 与语义别名双向转换。`Citation.citation_id` 从 `kb8chars:src12chars#chunk` 换为 `doc-rfc-2119-3#chunk`——同一 raw UUID 总是解析为同一别名，模型复折不崩；`kb_list_documents` 只输出别名，`kb_doc_head/chunk_range/grep` 在边界反向解析，Agent 传别名或原 UUID 都能调。灭火 UUID 呱这类幻觉源头。
- ✅ **2.1J 生产治理三件套**:
  - **Rainbow Deployment Router** (`governance/rainbow_router.py`): 多版本模型“彩虹环”路由 (stable / canary / rollback)，sha1(conversation_id) 哈希到 ring 保证同一会话不会中途换模；加权分配可表达任意切法 (80/15/5 、 95/5/0)；烟雾测试 5000 conv id 分布 81.3%/14.0%/4.6%，stickiness 验证通过。关闭时透明回落 default LLMRouter。
  - **Production Shadow Evals** (`governance/shadow_eval.py`): 在 `_reflection_node` FINISH 分支按 `SHADOW_EVAL_SAMPLE_RATE` (默认 5%) 异步 fire-and-forget 重跑 MultiGraderEval；ring-aware（拼接当前 ring 名到 audit 事件），供后续做版本间质量对比；出错只警告不阐。
  - **Sensitivity Flow Monitor** (`governance/flow_monitor.py`): 装在 supervisor / reflection / tool 调用边界，只看节点序列不看内容；检测三类异常 —— 同节点过频重入 (cycle)、同工具过量调用 (tool_abuse)、同 (tool, args) 重复 (duplicate_args / 循环死结)；烟雾测试 cycle/abuse/dup_args 三环均成功警报。LRU 1000 话题。
### 2026-03-07
- 🚧 **架构重构规划** — 生成 V3 版分布式数据入库流转集群架构，产出 `DEV-REQ-013` 拆解方案，决议剥离 Langfuse、全面替换线型管道。

### 2026-03-06
- ✅ **数据底座隔离** — 实现知识库读写与管理独立权限管理 (KB ACL)，从 API 层面拦截越权操作。
- ✅ **Agents Context 隔离** — 在 Swarm retrieval work 阶段中加入用户上下文过滤，Agent 本身只能检索用户有权限的库。
- ✅ **前端接入界面** — 增补 `KBPermissionsModal` 协作控制面板。

### 2026-02-24
- ✅ **Trace 深度集成** — 实现 Trace Modal 中检索分块的预览
- ✅ **智能联动** — 支持从 Trace 直接跳转到对应知识库文件并高亮定位
- ✅ **脱敏策略细化** — Backend/Frontend 全面支持：白名单、风险等级、自定义正则 (REQ-010)
- ✅ **新增检测器** — 增加 IP地址、MAC地址、护照号原生检测逻辑

### 2026-02-22
- ✅ 修复端口占用 WinError 10013 (改用 127.0.0.1)
- ✅ 实现 OfficeParser (PDF/DOCX 真实解析)
- ✅ 实现 ChromaVectorStore (本地向量存储)
- ✅ 注册 OfficeParser 到 indexing pipeline
- ✅ 国际化: KnowledgeDetail.tsx 全面翻译
- ✅ 添加中英文 i18n 键: fileName, fileSize, uploadText, uploadHint, status
- ✅ .env 默认设置 VECTOR_STORE_TYPE=chroma
- ✅ 修复 upload_document_global 返回值 (包裹 ApiResponse)

### 2026-02-15 (前次会话)
- ✅ 修复后端依赖缺失 (fastapi, chromadb 等)
- ✅ 创建 run.bat 一键启动脚本
- ✅ 实现 i18n 基础框架 + 语言切换器
- ✅ 国际化: AppLayout, DashboardPage, KnowledgePage
- ✅ 修复 KnowledgePage 重复导入和 React Hooks 丢失

---

> 💡 **使用方法**: 每次开发对话结束前，更新此文件中对应条目的状态。
> 新发现的问题直接追加到"已知问题"表中。
> 讨论过但没做的事情记录到"架构与规划"章节。
