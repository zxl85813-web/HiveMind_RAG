# 🤝 贡献指南 — HiveMind RAG

感谢你对 HiveMind RAG 的贡献！本文档描述了我们的协作开发规范，请在提交代码前仔细阅读。

---

## 🌿 分支策略

```
main                 ← 受保护的主要分支，所有代码必须通过 PR 合入
 ├── feature/xxx     ← 新功能分支 (e.g. feature/semantic-cache)
 ├── fix/xxx         ← Bug 修复分支 (e.g. fix/upload-oom)
 ├── refactor/xxx    ← 重构分支
 ├── docs/xxx        ← 文档分支
 └── chore/xxx       ← 配置/工具变更
```

### 规则
- `main` 分支始终保持可部署状态。
- **严禁直接向 `main` 推送代码**，所有变更必须通过 Pull Request。
- 分支命名规范：`<type>/<kebab-case-description>`。
- 合并后删除特性分支。

---

## 🔄 开发完整生命周期

以下是从"想法"到"代码合并"的完整流程：

```
                    ┌─────────────┐
                    │  1. 需求产生  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │ 2. 架构评估  │ ← 是否需要 ADR？
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
           ┌────── │ 3. 设计文档  │ ── 需要ADR ──┐
           │       └──────┬──────┘              │
           │              │                     ▼
           │              │           ┌─────────────────┐
           │              │           │ 创建 ADR PR      │
           │              │           │ → Review → 合并 │
           │              │           └────────┬────────┘
           │              │                    │
           │       ┌──────▼──────┐  ◄──────────┘
  不需要ADR ├──→   │ 4. OpenSpec  │
           │       │   Propose    │
           │       └──────┬──────┘
           │              │
           │       ┌──────▼──────┐
           └──→    │ 5. 编码实现  │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │ 6. 单元测试  │ ← 覆盖率 ≥ 80%
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │ 7. 提交 PR   │ ← 填写 PR 模板
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │ 8. CI 检查   │ ← Lint + Type + Test + Coverage
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │ 9. Code      │ ← 至少 1 人 Approve
                   │    Review    │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐   ← 仅当涉及 models/core/alembic
                   │10. 架构审查  │
                   │  (可选)      │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │11. 合并到    │
                   │    main      │
                   └──────┬──────┘
                          │
                   ┌──────▼──────┐
                   │12. 更新文档  │ ← REGISTRY.md + TODO.md
                   └─────────────┘
```

---

## 📝 代码规范速查

### Python (Backend)

| 工具 | 用途 | 配置 |
|------|------|------|
| **ruff** | Linting | `pyproject.toml` [tool.ruff] |
| **black** | 格式化 | `pyproject.toml` [tool.black] |
| **mypy** | 静态类型 | `pyproject.toml` [tool.mypy] |
| **pytest** | 测试 | `pyproject.toml` [tool.pytest] |
| **pytest-cov** | 覆盖率 | `fail_under = 80` |

```bash
# 本地快速检查
cd backend
ruff check .
black --check .
mypy app/ --ignore-missing-imports
pytest --cov=app --cov-fail-under=80
```

### TypeScript (Frontend)

| 工具 | 用途 | 配置 |
|------|------|------|
| **eslint** | Linting | `eslint.config.js` |
| **prettier** | 格式化 | `.prettierrc` |
| **tsc** | 类型检查 | `tsconfig.app.json` (strict: true) |
| **vitest** | 单元测试 | `vite.config.ts` |

```bash
# 本地快速检查
cd frontend
npm run lint
npm run typecheck
npm run test:unit
```

---

## 📏 Code Review 规则

### PR 要求
1. **PR 不超过 500 行有效代码变更**（不含 lock 文件、自动生成代码和迁移文件）。
2. **至少 1 个 Approving Review**。
3. **所有 CI 检查绿色通过**。
4. **0 个未解决的 Review 评论**。

### Review 检查项

#### 🔍 逻辑审查
- 代码是否正确实现了需求？
- 边界条件是否处理？
- 错误处理是否完善？

#### 🏗️ 架构审查 (标签: `needs-architecture-review`)
当审查涉及核心模块变更时，请额外关注：
- 是否违反 `project-structure.md` 中的模块边界规则？
- 数据库变更是否有对应的 Alembic 迁移？
- 是否引入了循环依赖？
- Big-O 复杂度是否合理？
- 安全边界是否被破坏？

#### 🧪 测试审查
- 新功能是否有充分的单元测试？
- 测试是否覆盖了正常路径和异常路径？
- 是否存在脆弱测试 (flaky tests)？

#### 📖 文档审查
- 公共 API 是否有 docstring？
- `REGISTRY.md` 是否已更新？
- 是否需要更新 `TODO.md`？

---

## 🏗️ 架构决策记录 (ADR)

当你的变更涉及以下范围时，**必须先提交 ADR**：

- 新增或修改数据库表 (`backend/app/models/`)
- 变更核心基础设施 (`backend/app/core/`)
- 引入新的外部依赖或第三方 API
- 改变模块间的通信模式
- 新增顶层目录

ADR 存放位置: `docs/architecture/decisions/`
ADR 格式: 参见 `0000-use-madr.md`

### ADR 流程
1. 在 GitHub 创建 Issue (使用 `🏗️ 架构提案` 模板)
2. 编写 ADR 文件并提交 PR
3. 获得架构审查 Approve
4. 合并 ADR PR
5. 基于已批准的 ADR 开始 OpenSpec 变更流程

---

## 🔧 OpenSpec 协作流程

我们使用 [OpenSpec](https://github.com/Fission-AI/OpenSpec) 管理 AI 辅助开发：

| 命令 | 用途 |
|------|------|
| `/opsx-propose` | 提出新变更，生成 proposal + design + tasks |
| `/opsx-apply` | 按任务列表逐项实施代码 |
| `/opsx-explore` | 探索想法、调研问题 |
| `/opsx-archive` | 归档已完成的变更 |

所有 OpenSpec 变更文件存放在 `openspec/changes/<name>/` 下。

---

## 📝 提交信息规范

使用 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### 类型

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档变更 |
| `style` | 代码格式（不影响逻辑） |
| `refactor` | 重构（不改变功能） |
| `test` | 测试相关 |
| `chore` | 配置/工具变更 |
| `perf` | 性能优化 |

### 示例
```
feat(rag): add semantic cache for repeated queries
fix(chat): resolve SSE connection timeout on slow networks
docs(adr): add ADR-0001 for GraphRAG integration
test(backend): add unit tests for indexing pipeline
chore(ci): configure backend CI with 80% coverage gate
```
