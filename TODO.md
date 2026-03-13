# 📋 HiveMind RAG — 开发 TODO 清单

> **⚠️ 强制规则**: 每次开发对话结束前，必须更新此文件。
> 任何"先不做"、"暂时跳过"、"以后再说"的内容必须记录在此。
> 
> 🗺️ **完整开发计划**: [docs/ROADMAP.md](docs/ROADMAP.md) — 7 个里程碑 / 87 个任务 / ~30 天
> 📄 **需求文档**: REQ-001~010 见 `docs/requirements/`
> 🛡️ **架构治理**: ✅ `team-collaboration-standards`, ✅ `agent-design-standards`, ✅ `Git Hooks` 已合入并运转。
> 🧬 **架构参考**: [Anthropic Agent 工程模式参考手册](docs/architecture/anthropic_agent_patterns.md) — 源自 15 篇官方文档

> 📅 最后更新: 2026-03-12

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

## 协作者分配规则（GitHub）

> 目的：让 TODO 与 GitHub Issue 的任务负责人保持一致，避免“有人做但无人认领”。

### 协作者账号

| 角色 | GitHub 用户名 | 说明 |
|------|---------------|------|
| Owner | `zxl85813-web` | 最终责任人，负责优先级与合并决策 |
| Collaborator | `Uchihacc` | 协作开发与任务执行 |

### 使用规范

- 每条可执行任务建议追加 `协作者: <github_username>` 字段。
- 当任务已对应 Issue 时，`协作者` 必须与 Issue Assignee 一致。
- 推荐格式：
  - `- ⬜ TASK-XXX: 任务说明（协作者: zxl85813-web）`
  - `- ⬜ TASK-YYY: 任务说明（协作者: Uchihacc）`

### 快速分配模板

| 任务ID | 任务 | 协作者 | 复核人 |
|--------|------|--------|--------|
| TASK-001 | 示例：前端主题统一 | `Uchihacc` | `zxl85813-web` |
| TASK-002 | 示例：CI 质量门禁 | `zxl85813-web` | `Uchihacc` |

---

## 0、🤖 Agent 架构重整看板（系统入口）

> 目标：把“功能清单式 TODO”重整为“Agent 分层执行看板”，便于 Supervisor 统一编排、Worker 并行执行、Reflection 验收闭环。
> 说明：本节是**唯一调度入口**；原有各章节继续保留为实现明细。

### 0.1 分层视图（Now / Next / Later）

| 层级 | 负责人 Agent | Now（本周） | Next（下阶段） | Later（储备） |
|------|-------------|-------------|----------------|---------------|
| 编排层（Orchestration） | Supervisor | ⬜ 建立任务路由矩阵（RAG/Code/Web/Ops）并绑定优先级 | ⬜ 引入“阻塞自动升级”策略（BLOCKED 自动建单） | ⬜ 任务成本感知路由（按延迟/费用动态分派） |
| 执行层（Workers） | RAG/Code/Web Worker | ⬜ 完成检索策略 A/B 测试基线 | ⬜ 标签→Pipeline 自动匹配规则 | ⬜ Self-RAG 自适应策略增强 |
| 记忆层（Memory） | Memory Agent | ⬜ 明确会话短记忆与评估长记忆写入边界 | ⬜ 正向反馈自动沉淀到评估集（M2.1F） | ⬜ 跨会话用户画像记忆治理 |
| 评审层（Reflection） | Reflection Agent | ⬜ 将自动审核规则引擎接入统一评分卡 | ⬜ Multi-Grader 三评分器联调（Code/Model/Human） | ⬜ 失败样本自动回灌提示词优化 |
| 治理层（Governance） | Governance Agent | ⬜ 修复 BUG-004（同步 Session → AsyncSession） | ⬜ 脱敏策略按知识库隔离配置 | ⬜ 安全等级 L1-L4 全链路联动 |
| 可观测层（Observability） | Observability Agent | ⬜ 增加检索命中率/空结果率/延迟指标面板 | ⬜ V3 Trace 全链路收口（Redis Buffer + FileTrace/AgentSpan） | ⬜ 质量-成本联合优化看板 |

### 0.2 本周执行序列（按依赖排序）

- ⬜ **A1（阻塞修复）**：`BUG-004` 异步化改造（先解除潜在性能阻塞）
- ⬜ **A2（质量基线）**：自动审核规则引擎 + 三档路由联调
- ⬜ **A3（检索效果）**：Retrieval A/B 对照实验 + 指标落库
- ⬜ **A3.1（提示词结构）**：Head-Tail Prompt Anchoring（关键约束前后锚点）
- ⬜ **A4（反馈闭环）**：正向反馈自动沉淀为 EvaluationItem
- ⬜ **A5（观测收口）**：V3 Trace + 质量监控面板接入
- ⬜ **A6（边做边学）**：按 `docs/LEARNING_PATH.md` 逐关完成实操练习，补全中级/进阶检验项

### 0.5 权限-角色-记忆专项（Authorization + Role + Memory）

> 目标：先固化权限硬边界，再上线角色/个人记忆增强；确保“更聪明”不等于“更大权限”。
> 规范文档：`docs/ACCESS_ROLE_MEMORY_GOVERNANCE.md`

- ✅ **ARM-P0-1（权限顺序统一）**：统一所有入口判定链路为 `Auth -> RBAC -> KB ACL -> Document ACL -> Prompt`。
- ✅ **ARM-P0-2（默认策略收敛）**：统一为 `default deny`，列出显式例外清单。
- ✅ **ARM-P0-3（拒绝原因码）**：审计日志增加 `deny_reason`（`rbac_denied/kb_acl_denied/doc_acl_denied`）。
- ✅ **ARM-P0-4（授权作用域对象）**：输出标准化 `authorized_kb_ids/authorized_doc_ids` 给上游使用。
- ✅ **ARM-P1-1（Role Memory Schema）**：定义角色记忆结构（术语、模板、风险偏好）。
- ✅ **ARM-P1-2（Personal Memory Schema）**：定义个人记忆结构（偏好、历史上下文、常用资源）。
- ✅ **ARM-P1-3（Prompt 分层注入）**：在 Prompt Engine 落地 Role/Personal 双层注入。
- ✅ **ARM-P1-4（作用域裁剪器）**：记忆读取前按授权作用域裁剪可见资源。
- ⬜ **ARM-P2-1（关系授权试点）**：设计单跳关系规则（owner/member/steward）并完成可解释审计。
- ⬜ **ARM-P3-1（双回归）**：发布前强制通过“权限回归 + 记忆安全回归”。

### 0.3 Agent 完成定义（DoD）

- ⬜ 每项任务必须包含：路由归属（Supervisor 决策）+ 执行日志（Worker）+ 评审结论（Reflection）
- ⬜ 每项任务必须关联：Issue/REQ/DES/OpenSpec 至少一种工件
- ⬜ 每项任务完成后必须更新：`TODO.md` + `REGISTRY.md`（若涉及接口/模型变更）

### 0.6 🏮 架构治理与路由自愈 (Architectural Critique Work)
> 目标：解决路由逃逸与语义分裂，落实 `critique_and_governance_backlog.md`
- ⬜ **GOV-001 (P0)**: 向量与图谱的一致性治理（Truth Alignment 校验器）
- ⬜ **GOV-002 (P1)**: 路由自愈机制（Routing Watchdog + Tier Escalation）
- ⬜ **GOV-003 (P1)**: 记忆价值密度采样（Importance-based Retention）
- ⬜ **GOV-004 (P2)**: 路由缓存 (JIT Route Cache with LRU)

### 0.4 共学体系专项（按 1 -> 3 -> 2）

> 目标：将“自省查漏补缺”与“团队互相借鉴”真正接到工程流水线上。
> 约束：严格按你指定顺序推进 `1 -> 3 -> 2`，但每个阶段内允许并行子任务。

- 🟡 **CL-1（第一优先）差距互补配对自动化**
  - 产物：`ReflectionEntry` 结构化 Schema + 存储 + Gap-Insight 匹配规则
  - 并行子任务：
    - ✅ CL-1A：定义 `GAP / ISSUE / INSIGHT` 字段规范与校验
    - ✅ CL-1B：写入持久化层（便于周报和配对检索）
    - ✅ CL-1C：实现基础匹配策略（关键词 +语义）
    - ✅ CL-1D：实现 `github-collaboration` 技能，支持 Discussion 自动发布。
    - ✅ CL-1E：输出配对建议清单（已关联 GitHub 项目看板）。
  - 快速验证：`GET /api/v1/agents/swarm/reflections/matches?limit=10`

- ✅ **CL-3（第二优先）共学度量看板（先手工后自动）**
  - 产物：周/月度指标面板（自省活跃度、互学覆盖率、知识结晶率、差距闭合度、飞轮转速）
  - 并行子任务：
    - ✅ CL-3A：定义指标口径与采集来源
    - ✅ CL-3B：先落地 Markdown 周报模板（低成本可执行）
    - ✅ CL-3C：预留自动采集接口（后续接脚本/CI）
  - 产物：`docs/guides/collaborative_learning_metrics.md`
  - 产物：`docs/learning/weekly/WEEKLY_LEARNING_REPORT_TEMPLATE.md`
  - 产物：`backend/scripts/generate_weekly_learning_report.py`

- ✅ **CL-2（第三优先）每日学习报告自动触发**
  - 产物：定时生成学习报告（外部信号 + 内部变更 + 风险提示）
  - 并行子任务：
    - ✅ CL-2A：定时任务触发器（本地/CI 二选一）
    - ✅ CL-2B：报告模板统一（可追踪至 TODO/Issue）
    - ✅ CL-2C：失败重试与日志留痕
  - 产物：`backend/scripts/run_daily_learning_cycle.py`
  - 产物：`backend/scripts/run_daily_learning_cycle_with_retry.py`
  - 产物：`backend/scripts/register_daily_learning_task.ps1`
  - 日志：`docs/learning/daily/logs/YYYY-MM-DD.log`

- ⬜ **并列推进规则（执行约束）**
  - 在 `CL-1` 未达到“可用”前，不开启 `CL-3` 实现编码（仅允许设计草案）。
  - 在 `CL-3` 未形成可读周报前，不开启 `CL-2` 自动化（防止先自动化后无验收口径）。
  - 任一子任务完成后，必须回填本节状态并关联 Issue/PR。

### 0.7 Skill-Creator 与 RAG 深度整合专项 (Eval & Action Integration)

> 目标：将 `skill-creator` 的评测自动化理念引入系统 CI/CD，并将 `rag_search` 从单个技能提升为系统的基础知识协议。

#### 1. 军工厂：评测自动化 (Skill-Creator 落地)
- 🟡 **TASK-EVAL-001（评测脚本工程化）**：将 `skill-creator/scripts/run_eval.py` 迁移适配为系统的核心测试脚本 `backend/scripts/evals/skill_trigger_eval.py`，用于 CI/CD 阶段拦截所有 Agent Tool 的误触发（协作者: zxl85813-web）。
- ✅ **TASK-EVAL-002（RAG 黄金测试集）**：建立 `skills/rag_search/evals/rag_search_evals.json`，包含至少 10 个正向触发样本和 10 个负向边界样本(如需转 Web/Memory 的问题)（协作者: Uchihacc）。
- ⬜ **TASK-EVAL-003（断言评分器介入）**：在 M2.1E Multi-Grader 中集成 RAG 强规则校验：1. 必须包含格式化引用 `[1][2]`；2. 知识库无内容时必须声明“未找到”。

#### 2. 武器库：RAG 的资产化与下沉 (RAG 架构重构)
- 🟡 **TASK-RAG-001（Skill 三段式解耦）**：重构 `rag_search/SKILL.md`，遵循渐进式加载（Progressive Disclosure）。把 RRF 排序、Query Rewriting 等复杂逻辑剥离为 Python 工具块存入 `skills/rag_search/scripts/`，供模型即时调用（协作者: zxl85813-web）。
- ⬜ **TASK-RAG-002（系统级路由预处理）**：将 `rag_search` 倡导的查询重写前置到 `SwarmOrchestrator` 输入层，将代词消除、模糊问题补全操作在实际调用 RAG 检索前完成（协作者: zxl85813-web）。
- ⬜ **TASK-RAG-003（前端引用协议渲染）**：解析大模型遵循 `rag_search` 生成的 `[1][2]` 样式，在前端 `Generative UI` 中渲染为交互式标签，点击弹出引用的文档片段 (Snippet) 抽屉（协作者: Uchihacc）。

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
- ✅ **Contextual Retrieval (Situational Chunks)**: 给每个分块注入文档级背景 (Anthropic 文档启示)
- ✅ **Prompt Caching for Ingestion**: 降低 Situational Chunking 的成本
- ✅ **Contextual BM25 Integration**: 将 Situational Text 同时注入 BM25 索引
利用 Claude (Haiku) 为每个分块生成简短的文档关联背景（如：所属章节、文件名、日期、实体关联），然后再进行向量化与 BM25 索引。
- ✅ **前端 Pipeline 配置页** — 可视化拖拽编排 Pipeline 步骤
- ✅ **前端节点参数配置抽屉** — 动态配置算子内部参数 (Chunk Size / Desensitization Policy)
- ✅ **后端 Pipeline 执行引擎集成** — `indexing.py` 已完全重构为基于 PipelineExecutor 的模块化驱动
- ✅ **AntV X6 Simple Demo** — 新增 `CanvasLabPage` 中的最小流程编排画布示例，作为替换 PipelineBuilder 的前置验证
- ✅ **AntV X6 Demo 增强** — 已补充工具栏交互（缩放/归中/新增步骤）与节点状态反馈，提升画布体验验证质量

#### Retrieval Pipeline（检索流水线）
- 🟡 **Retrieval Pipeline 已有框架** — `services/retrieval/pipeline.py` 已实现三步管线
- ✅ **每个知识库可独立绑定检索配置** — Query改写策略、检索权重、Reranker 选择 (前端配置页已支持)
- ⬜ **检索策略 A/B 测试** — 对比不同配置的检索效果
- 🟡 **链式 A/B 变体开关** — 已支持 `retrieval_variant`（`default` / `ab_no_graph` / `ab_no_compress`）
- ⬜ **Prompt A/B 变体实验** — 对比 `prompt_variant`（`default` / `head_tail_v1`）在长上下文下的准确率与引用率

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
- ✅ **AntV G6 Simple Demo** — 新增 `CanvasLabPage` 中的最小 Agent 关系图示例，作为替换 AgentDAG/GraphVisualizer 的前置验证
- ✅ **AntV G6 Demo 增强** — 已补充聚焦操作、缩放控制与状态图例，提升关系画布交互验证质量

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

### 2.1G 代码知识仓库与 SQL 摘要检索专项 ⬜ (NEW)

> 目标：让 Agent 在开发过程中稳定检索“代码 / 设计文档 / SQL”证据，优先用 SQL 语义摘要召回，再回源 SQL 本体验证。

#### G0 已完成基础能力（本轮）

- ✅ **Hook 对齐（Issue 关联可配置强制）**
  - `commit-msg` 支持 `hooks.requireIssueRef` 开关（默认严格）
  - `install-hooks.ps1` 安装时自动设置 `hooks.requireIssueRef=true`
- ✅ **开发向 RAG 接口骨架**
  - 新增 `POST /api/v1/agents/swarm/dev-rag/search`
  - 网关支持 `retrieve_for_development()`：向量检索 + Neo4j 图谱提示（可选）
- ✅ **Agent 工具接入**
  - 新增 `search_dev_knowledge` 原生工具，支持 `query/kb_ids/include_graph`

#### G1 文档与代码统一入库（先轻后重）

- ⬜ **统一 Artifact Schema v1**：定义 code/doc/sql 三类最小公共字段（id/path/type/version/updated_at/tags）
- ⬜ **文档分类器 v1**：仅做分类，不做强结构化（`adr/req/design/runbook/meeting/api_spec/unknown`）
- ⬜ **代码符号抽取 v1**：抽函数/类/路由/模块依赖，建立可追溯 symbol 索引
- ⬜ **证据回链规范**：所有回答必须附 `path + line + source_type` 证据锚点

#### G2 SQL 分级处理与摘要优先检索（核心）

- ⬜ **SQL 复杂度分级器**：L1 简单 / L2 中等 / L3 复杂
- ⬜ **长 SQL 切分器**：按语句边界 + CTE 逻辑段切分（支持父子段落关系）
- ⬜ **SQL 语义摘要卡 v1（强制用于 L3）**
  - 字段：`purpose/inputs/outputs/logic/biz_rules/risks/tags`
  - 绑定 `sql_hash`，SQL 变更后摘要自动失效重建
- ⬜ **检索主链改造**：优先检索 SQL 摘要卡，命中后回源 SQL 本体验证（禁止仅摘要直接下结论）
- ⬜ **降级策略**：SQL AST 失败时回退文本索引，流程不中断

#### G3 Neo4j 解构策略（仅对复杂 SQL）

- ⬜ **图谱准入规则**：仅 L3 SQL 进入全图解构，L1/L2 默认不入或轻入
- ⬜ **SQL 图谱最小模型**
  - 节点：`SQLStatement/CTE/Table/Column/Predicate`
  - 关系：`USES_TABLE/JOINS_WITH/DERIVES_FROM/FILTERS_ON/WRITES_TO`
- ⬜ **影响分析查询模板**：支持“改某表/字段会影响哪些 SQL/API/文档”

#### G4 Agent 路由与质量治理

- ⬜ **查询路由规则**：问业务口径先查定义文档；问实现细节再查 SQL 摘要与代码符号
- ⬜ **证据完整性校验器**：无本体证据时降级为“待确认”，防止摘要幻觉
- ⬜ **评估指标落库**：Recall@K、Evidence Precision、Impact Accuracy、Hallucination Rate

#### G5 执行顺序（按依赖）

- ⬜ **P1（本周）**：G1 + G2（摘要卡与检索主链）
- ⬜ **P2（下周）**：G3（复杂 SQL Neo4j 解构）
- ⬜ **P3（验收）**：G4（路由治理 + 指标闭环）

#### G6 任务拆解清单（可直接建 Issue）

##### P1（本周）— Schema / 摘要卡 / 检索主链

- ⬜ **TASK-KV-001**：定义 Artifact Schema v1（协作者: zxl85813-web）
  - 交付物：`artifact_id/type/path/version/updated_at/tags` 字段规范文档
  - 验收：代码/文档/SQL 三类样例均可通过 schema 校验
- ⬜ **TASK-KV-002**：实现文档分类器 v1（协作者: Uchihacc）
  - 交付物：`adr/req/design/runbook/meeting/api_spec/unknown` 分类结果
  - 验收：抽样 100 篇文档，分类准确率达到内部基线
- ⬜ **TASK-KV-003**：实现 SQL 复杂度分级器（协作者: zxl85813-web）
  - 交付物：L1/L2/L3 自动分级 + score 计算
  - 验收：覆盖简单/中等/复杂 SQL 样例集，分级结果可复现
- ⬜ **TASK-KV-004**：实现长 SQL 切分器（协作者: Uchihacc）
  - 交付物：语句边界 + CTE 逻辑段切分，支持父子段落关系
  - 验收：超长 SQL 不超时，切分后可回拼定位原文
- ⬜ **TASK-KV-005**：实现 SQL 语义摘要卡 v1（协作者: zxl85813-web）
  - 交付物：`purpose/inputs/outputs/logic/biz_rules/risks/tags/sql_hash`
  - 验收：L3 SQL 强制生成摘要；SQL 变更后摘要自动失效重建
- ⬜ **TASK-KV-006**：改造检索主链为“摘要优先”（协作者: zxl85813-web）
  - 交付物：摘要召回 -> SQL 本体验证 -> 证据输出
  - 验收：无本体证据时返回“待确认”，禁止仅摘要直接结论
- ⬜ **TASK-KV-007**：实现 AST 失败降级链路（协作者: Uchihacc）
  - 交付物：AST 失败自动回退文本索引 + 警告日志
  - 验收：异常 SQL 不阻断整体入库流程

##### P2（下周）— 复杂 SQL 图谱解构与影响分析

- ⬜ **TASK-KV-008**：实现 L3 SQL 图谱准入规则（协作者: zxl85813-web）
  - 交付物：仅 L3 入全图，L1/L2 不入或轻入策略
  - 验收：准入结果与分级器一致，可追踪审计
- ⬜ **TASK-KV-009**：实现 SQL 图谱最小模型（协作者: Uchihacc）
  - 交付物：节点 `SQLStatement/CTE/Table/Column/Predicate`，关系 `USES_TABLE/JOINS_WITH/DERIVES_FROM/FILTERS_ON/WRITES_TO`
  - 验收：至少 20 条复杂 SQL 成功入图，关键关系可查询
- ⬜ **TASK-KV-010**：实现影响分析查询模板（协作者: zxl85813-web）
  - 交付物：表/字段变更 -> 影响 SQL/API/文档 的查询模板
  - 验收：给定变更对象能稳定输出影响清单

##### P3（验收）— Agent 路由与质量闭环

- ⬜ **TASK-KV-011**：实现查询路由规则（协作者: zxl85813-web）
  - 交付物：业务口径优先文档、实现细节优先摘要+符号
  - 验收：路由日志可观测，误路由率低于基线
- ⬜ **TASK-KV-012**：实现证据完整性校验器（协作者: Uchihacc）
  - 交付物：证据缺失自动降级 + 可解释提示
  - 验收：抽检回答无“无证据断言”
- ⬜ **TASK-KV-013**：评估指标落库与看板（协作者: zxl85813-web）
  - 交付物：Recall@K / Evidence Precision / Impact Accuracy / Hallucination Rate
  - 验收：周报中可查看趋势并支持回归对比

##### 里程碑闸门（Go/No-Go）

- ⬜ **GATE-P1**：摘要优先检索主链可用，且“证据回链”已上线
- ⬜ **GATE-P2**：复杂 SQL 入图稳定，影响分析模板通过抽检
- ⬜ **GATE-P3**：路由与指标闭环完成，可用于持续优化

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

#### 上下文压缩与 Token 管理 (P2)
> 📄 设计文档: `docs/architecture/memory_compression_design.md`
- ⬜ **语义 Token 服务** — `TokenService` 集成 `tiktoken` 统一计量
- ⬜ **抽取式压缩** — 从检索块中提取与 Query 最相关的句子，拦截长尾
- ⬜ **对话短期记忆流压缩** — 会话超出 Token 阈值时自动生成摘要对象(`SummaryMessage`)替换长历史
- ⬜ **Lost in the Middle 优化** — 重排文档顺序，相关内容放首尾 (已在 RerankingStep 完成基础版本)
- ⬜ **长期记忆衰减** — 建立记忆热度（Temperature）时间惩罚与清除冷数据机制

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
- ⬜ **V3 Trace 集成** — RAG 全链路追踪（Redis Buffer + FileTrace/AgentSpan）
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
- ⬜ **Agent 内部改造**: 重构 `SwarmOrchestrator._retrieval_node`，注入结构化 `KnowledgeResponse`
- ⬜ **Skill Tool 升级**: 改造 `search_knowledge_base` tool，走 RAGGateway 链路并返回结构化文本
- ⬜ **API 增强**: 将 `/{kb_id}/search` 升级为返回完整协议，新增 `POST /knowledge/retrieve` 智能检索接口

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
- ⬜ **Progressive Skill Disclosure**: 优化 `.agent/skills/` 结构，引导 Agent 先读取目录 metadata，再按需通过 `cat` 读取详细文档，支持超大规模 Skill 库。
- ⬜ **Semantic Identifier Mapping**: 改造 Skill 输出，将数据库 UUID 自动映射为语义化名称或 0-indexed ID，降低模型幻觉。
- ⬜ **Context Compaction Node**: 在 Swarm 流程中增加自动摘要压缩节点，当消息记录过长时自动触发，防止 Token 爆炸。
- ⬜ **Hybrid Reflection**: 在 Reflection 节点中集成 Linter、Schema 校验等硬规则验证，不完全依赖 LLM 裁判。
- ⬜ **Contextual BM25 Integration**: 基于增强后的 Situational Chunks 构建高精度关键词索引，实现 Hybrid 检索的最佳性能（Recall@20 指标对齐 Anthropic 实验室数据）。
- ⬜ **Search Subagents**: 实现子智能体并行检索模式，用于处理大规模、高模糊度的知识搜索任务。
- ⬜ **Contextual Reranking (P0)**: 将 Reranking 提升为核心检索组件，支持 `Top 150 Retrieve -> Cross-Encoder Rerank -> Top 20 Inject` 的分段式高精度检索流。
- ⬜ **Tool Result Clearing (Advanced Compaction)**: 在 Swarm 会话滚动中，对旧的 Tool 调用结果进行“选择性擦除”，仅保留结果摘要和状态变更，防止长会话下的 Context 污染。
- ⬜ **Just-in-Time (JIT) Context Navigation**: 完善 Agent 的文件系统/Web 动态探索路径，优先使用 `glob`/`grep`/`head` 定向加载上下文，而非暴力检索全库。

### 2.1J Agent 安全沙箱与生产治理 (Sandboxing & Reliability) ⬜

- [x] ** Sandboxed Skill Runtime**: 基于 `SecuritySanitizer` 和 `ToolAuditor` 实现简单的沙箱规则。
- [ ] ** Rainbow Deployment for Agents**: 参考 Anthropic 生产实践，建立“彩虹发布”机制。
- ⬜ **Production Shadow Evals**: 在生产环境匿名运行“影子评估”，对比真实用户反馈与自动化评分的差异，快速捕捉如“模型理解退化”或“基础设施导致的随机错误”。
- ⬜ **Sensitivity Monitoring**: 改进内部可观测性，监控 Agent 决策模式（不看内容看逻辑流），识别循环死结或工具滥用。

### 2.1I Agent 长期任务稳定性与可靠性 (Long-Horizon & Reliability) ⬜

- ✅ **Feature-based Scaffolding**: 实现基于数据库的任务记录器。Supervisor 初始化任务清单并持久化到 `swarm_todos` 表，Agent 强制按清单增量执行。
- ✅ **LangGraph State Checkpointing**: 集成 `MemorySaver` 为 SwarmOrchestrator 提供 Checkpoints，支持 `thread_id` (Conversation ID) 级别的状态持久化。
- ⬜ **MCP "Code Mode" Bridge**: 建立 MCP 的代码执行网关，允许 Agent 编写 Python 脚本对海量工具返回的数据（如 1000 行 CSV）进行端内过滤聚合，而非全部传输。
- ⬜ **Self-Evolving Skills**: 实现“技能沉淀”机制，当 Agent 发现一种通用的工具编排模式时，自动将其保存为新的 `Skill` 并写入 `.agent/skills/` 目录。
- ⬜ **End-to-End Visual Verification**: 为 Coding/UI Agent 集成 Puppeteer 视觉反馈，确保功能不仅“代码绿”而且“运行绿”。
- ⬜ **Observability Trace Analytics**: 统计分析 Agent 的决策链路 (Thought -> Tool -> Result)，自动识别并标记“低效工具调用”或“逻辑循环陷阱”。

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

> [!TIP]
> **V3 Swarm 架构已正式上线**。系统现在具备极高的并行处理能力（Celery），并拥有原生 LangGraph 驱动的灵巧 Agent 协作能力。


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
- 🟡 **后端单元测试** — 部分完成 (KnowledgeService, Security API)
- 🟡 **前端组件测试** — 部分完成 (knowledgeApi, LoadingState, AppLayout)
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

### 5.2 待讨论事项与新架构设想

- ⬜ **Agent 通信协议** — Agent 之间用什么格式传递消息？JSON Schema？Protobuf？
- ⬜ **多租户设计** — 是否需要支持多用户隔离？
- ⬜ **Skill 沙箱执行** — 如何安全执行用户自定义 Skill？
- ⬜ **MCP Server 热插拔** — 如何无需重启就加载新的 MCP Server？
- ⬜ **LLM Fallback 链** — 主模型挂了之后的降级策略

### 5.3 核心算法库重构 (Core Algorithms Abstraction)
> 📄 设计文档: `docs/architecture/core_routing_classification_design.md`
> 🔍 参考项目与选型: `docs/architecture/open_source_references.md`
- ⬜ **统一的分类引擎 (Classification Engine)** — 抽取 `QueryPreProcessingStep` 等处的 prompt 为统一的服务接口，支持级联降级 (规则 -> 向量 -> LLM)。推荐引入 `jxnl/instructor` 基于 Pydantic 化归类别。
- ⬜ **统一的分词切分 (Tokenization & Chunking)** — 将入库的常规分割器改造为 `Semantic Chunker` 语义切分，辅以 `tiktoken` 精准限额，以及后期挂载 `LLMLingua` 记忆压缩器。
- ⬜ **动态智能路由 (Routing Algorithms)** — 扬弃纯 Prompt 大模型路由，在 Swarm Supervisor 中挂载超高速的向量分类树路由器（如对标 `aurelio-labs/semantic-router` 的机制）。

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

### 2026-03-09
- ✅ **测试基座搭建** — 集成 Vitest (Frontend) 并配置后端使用 SQLite 内存库进行隔离测试。
- ✅ **核心服务测试** — 完成 `KnowledgeService` 单元测试与 Security API 集成测试。
- ✅ **前端组件测试** — 完成 `AppLayout`、`LoadingState` 及 `knowledgeApi` 的单元测试。
- ✅ **Bug 修复** — 修复 `kb_service.py` 中 `NotFoundError` 参数错误。

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
