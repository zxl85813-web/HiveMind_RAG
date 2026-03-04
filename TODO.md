# 📋 HiveMind RAG — 开发 TODO 清单

> **⚠️ 强制规则**: 每次开发对话结束前，必须更新此文件。
> 任何"先不做"、"暂时跳过"、"以后再说"的内容必须记录在此。
> 
> 🗺️ **完整开发计划**: [docs/ROADMAP.md](docs/ROADMAP.md) — 7 个里程碑 / 87 个任务 / ~30 天
> 📄 **需求文档**: REQ-001~010 见 `docs/requirements/`
> 🛡️ **架构治理**: ✅ `team-collaboration-standards`, ✅ `agent-design-standards`, ✅ `Git Hooks` 已合入并运转。

> 📅 最后更新: 2026-03-04

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

- ✅ **评估数据模型** — `EvaluationSet`, `EvaluationItem`, `EvaluationReport` (Faithfulness 等指标)
- ✅ **测试集管理 (Testset Generator)** — 基于 LLM 自动生成 ground-truth 问答对
- ✅ **评估运行引擎** — 批量执行 RAG Pipeline → 用 LLM-as-a-Judge 评估指标
- ✅ **评估仪表盘前端 (EvalPage)** — 概览统计 + 测试集列表 + 评估报告列表
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

---

## 四、🧪 测试 — 待完成

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
