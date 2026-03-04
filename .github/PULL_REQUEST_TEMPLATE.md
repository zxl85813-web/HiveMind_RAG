## 📝 变更描述

<!-- 简要描述这个 PR 做了什么 -->

## 🔗 关联

- **OpenSpec Change:** `openspec/changes/<name>/` <!-- 如有 -->
- **ADR:** `docs/architecture/decisions/NNNN-*.md` <!-- 如涉及架构变更 -->
- **Issue:** #NNN <!-- 如有关联 Issue -->
- **需求文档:** `docs/requirements/REQ-NNN-*.md` <!-- 如有 -->

## 📋 变更类型

- [ ] 🐛 Bug 修复 (fix)
- [ ] ✨ 新功能 (feat)
- [ ] ♻️ 重构 (refactor)
- [ ] 📖 文档 (docs)
- [ ] 🧪 测试 (test)
- [ ] 🔧 配置/工具 (chore)

## ✅ 自检清单 — 提交前必读

### 代码质量

- [ ] 代码遵循 `.agent/rules/coding-standards.md` 编码规范
- [ ] 通过了 `ruff` / `eslint` 检查（无 Warning 遗留）
- [ ] 通过了 `black` / `prettier` 格式化检查
- [ ] 通过了 `mypy` / `tsc --noEmit` 类型检查
- [ ] 无 `TODO` / `FIXME` / `HACK` 注释遗留（或已记录到 TODO.md）

### 测试

- [ ] **新增/修改了对应的单元测试**
- [ ] 后端：`pytest --cov=app --cov-fail-under=80` 通过
- [ ] 前端：`npm run test:unit` 通过
- [ ] 手动测试已验证核心流程

### 文档

- [ ] `REGISTRY.md` — 已注册新增/变更的功能和组件
- [ ] `TODO.md` — 已更新相关条目状态
- [ ] 代码包含完整注释（模块 docstring / 类 docstring / 方法 docstring）

### ⚠️ 架构审查 (如涉及以下文件则必填)

> 修改了 `backend/app/models/`, `backend/app/core/`, `backend/alembic/`,
> 或 `docs/architecture/` ？请勾选以下项：

- [ ] 已创建或引用对应的 ADR (`docs/architecture/decisions/`)
- [ ] 已添加 `needs-architecture-review` 标签
- [ ] 该变更不违反 `.agent/rules/project-structure.md` 中的模块边界规则

## 📸 截图 / 录屏（如涉及 UI）

<!-- 粘贴截图或 GIF -->

## 💡 Review 重点

<!-- 引导 reviewer 注意哪些地方需要重点审查 -->
