# 🏭 开发治理 — 蜂巢的生产规范

> 蜂蜜之所以是蜂蜜，而不是蜂蜡或花粉，
> 是因为每一只蜜蜂在每一道工序上都遵循相同的规格。
> HiveMind 的开发治理体系，就是让人类和 AI 遵循同样的规格。

---

## 为什么 HiveMind 需要开发治理？

HiveMind 本身就是一个 AI Agent 平台。这意味着它的开发过程中，**AI 也是代码贡献者**。

当一个 AI Agent 可以生成、修改、审查代码时，"代码质量"和"架构一致性"的边界就变得模糊了。我们需要一套体系来约束人类开发者和 AI Agent 遵循同样的标准。

`.agent/` 目录就是这套体系的物理载体。它**不只是给人读的文档**，它是 AI Agent 可以直接读取和执行的规范集合。

---

## 治理体系全景

```
.agent/
├── rules/          # 🧱 AI 编码规范——约束 AI 代码生成的架构边界
├── workflows/      # 📋 标准化 SOP——每类任务的执行步骤
├── hooks/          # 🔒 Git Hooks 门禁——提交时的自动化检查
├── checks/         # ✅ 质量检查套件——Lint + Type Check + Pytest
├── skills/         # 🛠️ Agent Skill 定义——可复用的 AI 能力单元
└── templates/      # 📄 文档模板——需求/设计/变更的标准格式
```

---

## 标准化工作流（Workflows / SOP）

每一类开发任务都有对应的 SOP，AI Agent 在执行任务前会先读取 Workflow，按步骤执行：

| 工作流 | 触发场景 |
|:---|:---|
| `/develop-feature` | 开发新功能前，先查注册表再开发 |
| `/create-api` | 创建新的后端 API 端点 |
| `/create-component` | 创建新的前端 React 组件 |
| `/decompose-feature` | 拆解复杂功能为子任务 |
| `/design-database` | 设计或变更数据库表结构 |
| `/extract-requirement` | 从对话提取正式需求文档 |
| `/write-tests` | 为功能编写自动化测试 |
| `/code-review` | 里程碑代码审查与质量检查 |
| `/update-todo` | 对话结束前更新 TODO.md |

工作流文件位于 `.agent/workflows/*.md`，使用 YAML frontmatter + Markdown 格式，对 AI Agent 和人类开发者均可读。

---

## Git Hooks 门禁

每次 `git commit` 时，以下检查会自动运行：

| 检查项 | 规则 |
|:---|:---|
| **Commit Message 格式** | 强制 `Conventional Commits`（`feat:` / `fix:` / `docs:` 等） |
| **Issue 关联** | 提交消息必须关联到 GitHub Issue（`#NNN`） |
| **密钥扫描** | 禁止明文 API Key、密码出现在代码中 |
| **文件大小** | 拦截意外提交的大型二进制文件 |

Hook 文件位于 `.agent/hooks/`。

---

## AI 编码规范（Rules）

`.agent/rules/` 定义了 AI Agent 在生成代码时必须遵守的架构约束，例如：

- **模块边界**：不允许跨层直接调用（如 API 层不能直接访问 ORM）
- **依赖注入**：服务通过 FastAPI Dependency Injection 注入，不允许全局单例
- **异步规范**：IO 操作必须使用 `async/await`，禁止阻塞主线程
- **类型注解**：所有函数必须有完整的 Python 类型注解
- **错误处理**：不允许裸 `except Exception`，必须具体处理或上抛
- **主题一致性（前端）**：必须遵守 `.agent/rules/frontend-component-standards.md` 与 `.agent/rules/frontend-design-system.md` 中的主题治理规则（单一 token 源、禁止业务代码硬编码色值）

---

## 前端主题治理（新增）

为保证“主题可切换 + 视觉统一 + AI 可复用”，前端主题治理作为强制开发规范执行：

- 单一入口：`ConfigProvider.theme`（`frontend/src/App.tsx`）
- 单一变量层：`styles/variables.css`（`--hm-*`）
- 禁止硬编码：业务组件中禁止直接写十六进制色值（mock/variables/token 定义文件除外）

建议在提交前执行：

```bash
rg "#[0-9A-Fa-f]{3,8}" frontend/src --glob "!frontend/src/styles/variables.css" --glob "!frontend/src/mock/**"
```

如需豁免，必须在代码中标注 `THEME_EXCEPTION` 并在 PR 描述中解释原因。

---

## 质量检查套件

一键执行所有质量检查：

```bash
./.agent/checks/run_checks.ps1
```

包含：

| 检查 | 工具 |
|:---|:---|
| 代码风格 | `ruff` (Python) / `eslint` (TypeScript) |
| 类型检查 | `mypy` (Python) / `tsc` (TypeScript) |
| 单元测试 | `pytest` |
| 覆盖率报告 | `pytest-cov` |

---

## 需求与变更管理

### 需求文档 (REQ-NNN)

需求文档位于 `docs/requirements/REQ-NNN.md`，使用标准模板创建，内容包括：背景、目标、功能点、验收标准、设计约束。

```bash
# 创建新需求（触发 extract-requirement 工作流）
# AI Agent 会自动填充 REQ 文档并更新 REGISTRY.md 和 TODO.md
```

### 变更追踪（OpenSpec）

较大的架构变更通过 `openspec/` 目录管理，包含完整的提案→设计→实施→归档流程。所有的提案必须通过 **HMER 验证循环 (设想-度量-实验-反思)**。在提出特性、重构（如引入分层缓存或推测性加载）时，除了完成代码实现，更需要编写测试方法或探针，在试运行阶段采集性能指标和报错率，最终根据实验效果生成 ADR，决定提交合并或回滚。

---

## 模块注册表（REGISTRY.md）

`REGISTRY.md` 是整个项目的"目录"——记录所有模块、服务、Skill、API 端点的存在及其状态。

**规则：任何新模块在开发前必须先在 REGISTRY.md 中注册。** 这防止了重复造轮子，也让 AI Agent 在开发新功能时能快速感知已有能力。

---

## 团队协作与交付自动化（已合并）

以下协作与交付内容已统一收敛到：

- [collaboration_and_delivery_playbook.md](./guides/collaboration_and_delivery_playbook.md)

其中包含：

- Issue 驱动协作与 PR 规则
- 分支保护与 CI 门禁
- GitHub 自动化（Dependabot、Projects、PR 自动标注）
- TODO 到 Milestone 的同步脚本使用方式
- 高可用里程碑任务模板（路由熔断、CQRS、前端韧性、Code Vault）

执行要求（强制）：

- 所有功能开发必须绑定 Issue，并在 PR 中使用 `Closes #ID`
- `main` 分支禁止直推，必须经 PR + 状态检查
- Sprint 计划必须落到 Milestone 或 TODO（至少一处可追踪）

---

## 代码位置索引

| 组件 | 路径 |
|:---|:---|
| 工作流 SOP | `.agent/workflows/` |
| AI 编码规范 | `.agent/rules/` |
| Git Hooks | `.agent/hooks/` |
| 质量检查脚本 | `.agent/checks/` |
| 需求文档 | `docs/requirements/REQ-NNN.md` |
| 模块注册表 | `REGISTRY.md` |
| TODO 看板 | `TODO.md` |
| 协作与交付手册 | `docs/guides/collaboration_and_delivery_playbook.md` |
| 统一规则手册 | `docs/guides/unified_development_rulebook.md` |

---

## 相关文档

- [← 返回 README](../README.md)
- [🧭 Agent 治理：指挥系统](AGENT_GOVERNANCE.md)
- [🍯 数据治理：知识酿造流程](DATA_GOVERNANCE.md)
- [🧬 共学体系：自省↔互学↔共进](COLLABORATIVE_LEARNING.md)
- [🎓 学习路径：L0-L4 边做边学地图](LEARNING_PATH.md)
- [📘 统一规则手册：开发执行单一入口](guides/unified_development_rulebook.md)
- [贡献指南](../CONTRIBUTING.md)
