# 🏛️ HiveMind RAG — 问题体系与开发治理框架总说明

> **本文档是整个开发体系的导航地图 (Navigation Map)。**  
> 任何人（开发者与 AI Agent）在动手写代码前必须先读这里，理解我们"怎么提问题、怎么解决问题、怎么记录问题"。

---

## 一、体系设计哲学 (Design Philosophy)

HiveMind RAG 的开发不是"想到哪里写到哪里"，而是完全拥抱 **Document-Driven + Agent-Native** 的研发范式。

核心理念：**"所有意图必须显式记录，所有代码必须有依据，所有问题必须有闭环。"**

在这之上，我们信奉 **HMER 验证哲学 (大胆设想，小心求真)**：
- **H**ypothesis (假设) — 每次变更前，明确可证伪的业务或技术假设。
- **M**easure (度量) — 建立基线数据，确定改造前后的量化指标。
- **E**xperiment (实验) — 在最小范围（Feature Flag/影子写入/A-B 测试）进行验证。
- **R**eflect (反思) — 用数据说话，做出投产、迭代或回滚的决策。

```
你的想法 / Bug / 需求
     │
     ▼
[Issue Template] ← GitHub Issue 是唯一合法的任务入口
     │
     ▼
[需求文档 REQ-NNN] ← 需求的语义化固化
     │
     ▼
[设计文档 DES-NNN] ← 数据库/API/Agent/前端的四维设计
     │
     ▼
[OpenSpec 变更] ← 把设计拆解成可执行的代码任务
     │
     ▼
[代码实现] ← 遵守 .agent/rules/ 框架约束
     │
     ▼
[测试 + PR + Review] ← 双视角测试，CI 门禁把关
     │
     ▼
[CHANGELOG] ← 问题的合法归档与闭环
```

---

## 二、问题分类体系 (Issue Taxonomy)

在本系统中，"问题"不是一个模糊的概念，它被严格分成以下几种类型，每种类型有固定的 Issue Template 和处理流程：

### 1. 🐛 缺陷报告 (Bug Report)
**触发条件**: 运行时行为与预期不符，或者 CI 出现红旗。  
**入口**: GitHub → New Issue → 选择 `🐛 Bug 缺陷报告` 模板。  
**必填字段**: 复现步骤 / 期望 vs 实际 / 日志截图 / 优先级（P0~P3）。  
**流转路径**: Issue 建立 → 打 Label(`bug`, `pX-xxx`) → 从 `develop` 切 `fix/issue-{ID}` 分支 → 修复 → PR → CI 绿 → Merge。

| 优先级 | 说明 | SLA |
|--------|------|-----|
| P0-critical | 系统宕机/核心功能完全不可用 | 同日修复 |
| P1-high | 主要业务受损，无规避方案 | 48h |
| P2-medium | 边缘场景，有规避方案 | 下个迭代 |
| P3-low | UI瑕疵/体验问题 | Backlog |

---

### 2. ✨ 功能需求 (Feature Request)
**触发条件**: 需要新增业务能力，或者对现有功能做较大改造。  
**入口**: GitHub → New Issue → 选择 `✨ Feature 新功能需求` 模板。  
**必填字段**: 业务目标 / 方案构思 / 架构影响复选框 / 规模估计 (S/M/L)。  
**流转路径**:  
```
Issue 建立 (PO)
  → /opsx-explore 探索架构影响 (Architect)
  → 生成 REQ-NNN 需求文档 (AI)
  → 生成 DES-NNN 设计文档 (AI + 确认)
  → /opsx-propose 生成代码任务清单 (AI)
  → /opsx-apply 实现代码 (Dev/AI)
  → PR + Review + Merge (Reviewer)
  → CHANGELOG 归档 (AI)
```

---

### 3. 🤖 AI 阻滞报告 (AI Blocked Report)
**触发条件**: AI Agent 在执行代码生成任务时遇到无法自行解决的阻塞。  
**入口**: AI 自动发起（或由人类代填）→ 选择 `🤖 AI Blocked Report` 模板。  
**必填字段**: 被阻塞的原始 Issue ID / 运行 Skill 名称 / 错误日志 / 需要人类做什么。  
**流转路径**:  
```
AI 阻塞 → 新建 [BLOCKED] Issue → 打 ai-generated 标签
  → 人类 Review 阻塞原因
  → 解决底层依赖 / 调整设计
  → 重新指派 AI 继续任务
  → 关闭 [BLOCKED] Issue
```

---

### 4. 🏗️ 架构提案 (Architecture Proposal)
**触发条件**: 任何引入新的外部依赖、数据库表结构变更、模块拆分/合并，或破坏性 API 变更。  
**入口**: GitHub → New Issue → 选择 `🏗️ Architecture Proposal` 模板（触发 ADR 流程）。  
**流转路径**:  
```
Issue 建立
  → 讨论技术方案 (Architect + PO)
  → 制定 HMER 验证方案 (收集基线, 设定指标)
  → 创建 ADR 文档 (docs/architecture/decisions/NNNN-xxx.md)
  → 方案批准 → 开始实现 → 灰度验证 → 数据反思决策
```

---

## 三、文档体系 (Documentation System)

项目里的每一类文档有独立的作用域，严禁将不同性质的内容混合存放：

| 文档位置 | 类型 | 作用 | 更新时机 |
|----------|------|------|---------|
| `REGISTRY.md` | 台账 | 系统的"心脏"。所有 API/Service/Model/Component 的登记表。 | **每次新增或修改功能必须同步更新** |
| `TODO.md` | 看板 | 当前进行时的任务、阻塞点、已知 Bug。 | **每次对话结束前，通过 `/update-todo` 强制刷新** |
| `docs/ROADMAP.md` | 战略 | 中长期的里程碑规划（7 个 Milestone，大颗粒度）。 | 季度或大版本发布时调整 |
| `docs/requirements/REQ-NNN.md` | 需求 | 需求的语义化和正式化说明书。 | 需求讨论确定后立即归档 |
| `docs/design/DES-NNN.md` | 设计 | 四维设计（DB/Backend/API/Frontend）。 | 开始写代码前必须存在 |
| `docs/architecture/*.md` | 架构 | 全局架构图、分支策略、批处理引擎设计等宏观文档。 | 重大架构决策后更新 |
| `docs/architecture/decisions/*.md` | ADR | 每一个重要技术决策的不可变历史记录。 | 做出决策时写入，之后只读 |
| `docs/changelog/CHANGELOG.md` | 历史 | 过去完成时。里程碑完成后提炼的发布说明。 | Milestone 发布时从 TODO 迁移 |

---

## 四、工作流体系 (Workflow System)

`.agent/workflows/` 是将标准操作流程（SOP）变成可执行 AI 命令的工具箱：

| 命令 | 触发场景 | 输出物 |
|------|----------|--------|
| `/extract-requirement` | 你随口说了一个业务想法 | `docs/requirements/REQ-NNN.md` |
| `/develop-feature` | 准备开始实现某个功能前 | 检查 REGISTRY + TODO + 确认依赖 |
| `/create-api` | 需要新增一个后端 API | Schema + Service + Route 标准骨架 |
| `/create-component` | 需要新增一个前端组件 | `.tsx` + `.module.css` 标准骨架 |
| `/design-database` | 需要变更数据库表结构 | Alembic 迁移脚本 + ER 图 |
| `/write-tests` | 功能完成后，提 PR 前 | 双视角测试（契约+容错）|
| `/code-review` | 里程碑结束时 | 架构合规性审查报告 |
| `/update-todo` | 每次对话结束前（强制） | 更新 TODO.md |
| `/opsx-explore` | 收到 GitHub Issue，准备设计 | 探索式分析报告 |
| `/opsx-propose` | 方案已确认，生成代码计划 | OpenSpec `design.md` + `tasks.md` |
| `/opsx-apply` | 执行代码任务 | 实际代码 + Commit |

---

## 五、架构规范体系 (Architecture Standards)

`.agent/rules/` 中定义了所有"硬约束"规则，AI 代码生成必须严格遵守：

| 规范文件 | 覆盖范围 |
|----------|---------|
| `project-structure.md` | 项目目录结构宏观规划，所有目录的责任边界 |
| `backend-design-standards.md` | 后端五层架构（路由/服务/智能/基础设施/数据），函数命名，禁止跨层调用规则 |
| `agent-design-standards.md` | **AI 智能层专用规范**：SwarmOrchestrator 注册、记忆分层读写、LLM 路由分级、RAG 安全底线 |
| `api-design-standards.md` | RESTful 命名，ApiResponse 必须包裹，分页参数规范 |
| `database-design-standards.md` | UUID4 主键，软删除，时间戳策略，索引设计 |
| `coding-standards.md` | 注释结构（JSDoc/Docstring），命名规范，禁用库清单（如禁止 `print()` 日志） |
| `frontend-component-standards.md` | Smart/Dumb 组件拆解，CSS Modules，Ant Design 优先复用 |
| `testing_guidelines.md` | 测试金字塔（Unit 70%/Integration 20%/E2E 10%），Mock 决策树，双视角方法 |
| `team-collaboration-standards.md` | Git 分支模型，Conventional Commits，PR 合并策略，AI↔GitHub Issue 双向绑定 |

---

## 六、分支与流水线体系 (Branch & Pipeline)

详细设计见 [`docs/architecture/branch-strategy.md`](architecture/branch-strategy.md)，以下是简要汇总：

| 分支类型 | 用途 | CI Pipeline | 强度 |
|---------|------|------------|------|
| `main` | 生产主干 | `backend/frontend-ci.yml` | 完整 |
| `develop` | 集成开发 | `develop-ci.yml` | Lint+Type+全量Test |
| `feature/issue-{ID}` | 个人功能 | `feature-ci.yml` | Lint+Unit Test（快） |
| `fix/issue-{ID}` | Bug 修复 | `feature-ci.yml` | 同上 |
| `hotfix/issue-{ID}` | 生产紧急修复 | `feature-ci.yml` | 同上 |
| `release/v{x.y.z}` | 发布候选 | `release-ci.yml` | 全量+SAST安全扫描 |
| `experiment/*` | 探索验证 | 无 CI | — |

---

## 七、技能体系 (Skills Library)

`.agent/skills/` 是赋予 AI 高级处理能力的技能套件：

| 技能 | 用途 | 关联规范 |
|------|------|---------|
| `generate-tests` | 为指定文件自动生成符合双视角规范的完整测试套件 | `testing_guidelines.md` |
| `generate-design-doc` | 从 REQ-NNN 自动生成四维 DES-NNN 设计说明书 | `design-and-implementation-methodology.md` |
| `openspec-explore` | 深度探索一个问题或架构影响，充当思考伙伴 | `project-workflow.md` |
| `openspec-propose` | 一键生成完整变更提案（设计 + 任务清单） | `project-workflow.md` |
| `openspec-apply` | 按 OpenSpec 任务清单逐项实现代码 | `agent-design-standards.md` |
| `openspec-archive` | 完成后归档变更记录到 CHANGELOG | `changelog-standards.md` |

---

## 八、闭环总结 (The Closed Loop)

一个完整的问题从提出到解决，必须经历以下闭环：

```
[提出] GitHub Issue (必须用 Template)
  ↓
[分析] /opsx-explore 深度分析
  ↓
[记录] REQ-NNN（需求）+ DES-NNN（设计）
  ↓
[计划] OpenSpec Tasks（代码任务清单）
  ↓
[实现] 切 feature/fix/hotfix 分支 + Conventional Commit
  ↓
[验证] generate-tests + CI Pipeline 全绿
  ↓
[审查] PR + Code Review (人类)
  ↓
[合并] Squash Merge → Closes #IssueID → Issue 自动关闭
  ↓
[归档] TODO.md 清理 + CHANGELOG 记录 + openspec-archive
  ↓
[下一轮] 下一个 Issue...
```

## 九、AI 核心理念：函数式 Agent 与 编译型 RAG (AI Philosophy)

除了研发流程，HiveMind 还有三个核心架构理念，指导所有 AI 逻辑的实现：

### 1. 行为解耦：Agent (副作用) × Skill (纯函数)
*   **Skill 必须纯净**: 它是无状态的工具。严禁在 Skill 实例中保存任何业务状态。
*   **Agent 驱动变迁**: Agent 是状态机的载体，负责通过调用 Skill 产生合法的副作用。
*   **开发准则**: 优先编写可测试的纯函数 Skill，再由 Agent 进行逻辑编排。

### 2. 数据治理：从"管理"到"编译" (Compilation)
*   **Ingestion = Compiler**: 我们不只是在存文档，而是在编译知识。
*   **治理指标**: 关注知识的词法分析（解析）、语法分析（结构化）和语义优化（分块与关联）。

### 3. 数据微服务化 (Data Microservices)
*   **KB = Service**: 每个知识库是一个独立治理的微服务单元。
*   **契约驱动**: RAG 输出必须遵守强 Schema 契约 (`KnowledgeResponse`)，严禁向 Agent 返回裸字符串。
*   **治理同步**: RAG 的治理遵循微服务治理逻辑：路由、发现、限流与熔断。

### 4. RAG 的 HMER 验证循环 (RAG Evaluation)
*   **RAG 同样也是实验**: 调整 Prompt、更换 Embedding 模型或改变 Chunk 策略，本质上都是"架构变更"。
*   **无度量不优化**: 所有的 RAG 优化必须建立在评估数据集 (Eval Dataset) 和基准测试 (Baseline) 之上。
*   **验证标准**: 每次 RAG 链路更新必须通过精确度 (Precision)、召回率 (Recall) 和响应延迟 (Latency) 的数据反思，证明其优于现网版本才能全量。

---

> **这个体系的核心价值不在于流程本身的繁复，而在于让每一行代码都有迹可循、每一个决策都经得起追溯，无论是今天的你，还是未来接手的 AI Agent。**

