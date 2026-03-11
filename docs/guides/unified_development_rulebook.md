# Unified Development Rulebook

> 单一入口文档：统一 .agent、OpenSpec、.cursorrules 与协作治理文档，减少重复规则和冲突解释成本。

## 1. 适用范围

本手册适用于以下开发资产：

- `.agent/rules/*`: 架构与编码硬约束
- `.agent/workflows/*`: 可执行 SOP
- `.agent/hooks/*`: 本地提交门禁
- `.agent/checks/*`: 本地质量检查脚本
- `openspec/config.yaml` + `openspec/changes/*`: 变更契约与任务执行
- `.cursorrules`: AI 助手行为约束
- `CONTRIBUTING.md`: 分支/PR/提交/审查规范
- `docs/DEV_GOVERNANCE.md`: 治理总说明
- `docs/guides/collaboration_and_delivery_playbook.md`: 团队协作与交付手册

## 2. 规则优先级（冲突时按此执行）

1. `Git Hooks + CI + Branch Protection`（强制门禁）
2. `.agent/rules/*`（架构与代码硬规则）
3. `openspec/config.yaml` + 变更工件（proposal/design/tasks）
4. `.agent/workflows/*`（执行路径和步骤）
5. `.cursorrules`（助手行为建议，需与上层规则一致）
6. `README/说明性文档`（参考信息）

## 3. 单一标准开发流程（One Flow）

1. 创建/确认 GitHub Issue（任务唯一入口）
2. 若是中大型需求：先走 OpenSpec（proposal/design/tasks）
3. 研发前检查 `REGISTRY.md`，避免重复造轮子
4. 按 `.agent/rules/*` 实施代码
5. 完成后更新 `REGISTRY.md` 与 `TODO.md`
6. 本地检查：`.agent/checks/run_checks.ps1`（或分端检查）
7. 提交遵守 Conventional Commits，建议附 `Resolves/Closes #ID`
8. PR 通过 CI 与 Review 后合并

## 4. 门禁矩阵（当前真实行为）

### 4.1 pre-commit

来源：`.agent/hooks/pre-commit`

- 阻断提交：检测疑似密钥/API key/密码硬编码
- 阻断提交：前端暂存文件触发 `theme-check.mjs --staged` 失败
- 非阻断：提示可运行本地检查脚本（当前未强制执行 run_checks）

### 4.2 commit-msg

来源：`.agent/hooks/commit-msg`

- 阻断提交：不符合 Conventional Commits 格式
- 默认阻断提交：未包含 `Resolves/Closes/Fixes/Relates #ID`（由 `hooks.requireIssueRef=true` 控制）
- 可降级为警告：执行 `git config hooks.requireIssueRef false`

### 4.3 CI 与协作

来源：`CONTRIBUTING.md`、`docs/guides/collaboration_and_delivery_playbook.md`

- 强约束：不得直推 main，必须走 PR
- 强约束：CI 通过 + 至少 1 个批准
- 约束建议：PR 关联 Issue（`Closes #ID`）

## 5. 关键冲突与统一结论

### 冲突 A: Issue 关联是“强制”还是“建议”

- 文档层（治理/协作）倾向强制
- 真实 hook 行为是警告不阻断

统一结论：

- 团队规范按“强制关联 Issue”执行
- 本地 hook 保持“警告”作为柔性提醒
- 最终由 PR 规范和审查流程兜底

### 冲突 B: 复杂需求先写 DevLog 还是先走 OpenSpec

- `.cursorrules` 提到 `docs/changelog/devlog/` 先行
- 项目现行体系以 OpenSpec 为主线

统一结论：

- OpenSpec 是默认主流程
- DevLog 可作为补充记录，不作为默认强制入口

## 6. AI 助手执行约定（精简版）

1. 先查 `REGISTRY.md`，再创建新模块/路由/组件
2. 涉及多文件或复杂改动：先完善 OpenSpec 变更再实施
3. 严格遵守层级边界与类型/测试规范
4. 修改完成后同步更新文档资产（至少 `TODO.md`、必要时 `REGISTRY.md`）
5. 不绕过门禁，除非明确紧急并可追溯说明

## 7. 推荐日常命令

```powershell
# 安装 Git hooks 路径
powershell -ExecutionPolicy Bypass -File .agent/hooks/install-hooks.ps1

# 查看/调整 Issue 关联强制开关
git config --get hooks.requireIssueRef
git config hooks.requireIssueRef false

# 全量质量检查
powershell -ExecutionPolicy Bypass -File .agent/checks/run_checks.ps1

# 快速检查（lint + theme）
powershell -ExecutionPolicy Bypass -File .agent/checks/run_checks.ps1 -Quick
```

## 8. 维护规则

- 任何新增治理规则，优先落在 `.agent/rules/*` 或 OpenSpec 配置
- 若影响 AI 行为，再同步 `.cursorrules`
- 本文档作为“统一入口”，用于汇总，不替代细则原文
