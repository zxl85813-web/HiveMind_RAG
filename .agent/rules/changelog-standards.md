# 📜 变更文档与发布规范 (Changelog Standards)

> **关联流程**: [`.agent/workflows/update-todo.md`](../workflows/update-todo.md)

为了防止项目失控，每一次 Milestone（里程碑）和 Release（发布）都必须有一份精确的 CHANGELOG，以帮助整个全栈团队以及 AI 清楚地了解系统的进化状态。

---

## 1. TODO.md 与 CHANGELOG.md 的边界

- **`TODO.md`**: 是**当前进行时**。记载着正在开发的进行中任务、堵塞点（Blockers）、等待修理的 Bugs、还需要讨论的决策会议记录。它是一块动态看板。
- **`CHANGELOG.md`**: 是**过去完成时**。一旦一个 Bug 被确证修补并在 `main` 分支落定，或者一个 Milestone 发布完成，这部分的功能就要被写入 CHANGELOG，并且从 TODO 中剔除（或标记为 ✅ 并存档）。

---

## 2. CHANGELOG 格式规范
必须遵循 [Keep a Changelog 1.1.0](https://keepachangelog.com/zh-CN/1.1.0/) 的语法，格式清晰。

### 2.1 基础骨架模板

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.1.0] - 2026-03-01
### Added (新增)
- 知识库模块增加基于语义的查询功能 (REQ-003)。
- 前端新增 `StatCard` 和 `LoadingState` 通用组件，记录在 `component-inventory.md`。

### Changed (变更)
- **Breaking**: 将默认的向量库由 Pinecone 切换为 ChromaDB，所有现存部署需要跑迁移脚本。
- UI/UX：升级了深色模式下所有毛玻璃边框的透明度算法。

### Fixed (修复)
- 修复了因为 `limit` 传参为 string 导致的列表分页 500 报错 (BUG-101)。

### Removed (移除)
- 移除了冗余的 `OldFileParser` 相关接口，已被 `OfficeParser` 全面对接替代。
```

### 2.2 规定种类 (Categories)
同一版本下的改动，必须分门别类归结到以下字眼下：
- `Added`: 新添加的功能。
- `Changed`: 对现有功能的变更。
- `Deprecated`: 已经不建议使用，准备在以后的版本中移除的功能。
- `Removed`: 在此版本中移除了的功能。
- `Fixed`: 修复的 bug。
- `Security`: 修复的漏洞。

---

## 3. 从功能开发向发版的转化 (Release Workflow)

当一个 Milestone 完成，在通过 `code-review.md` 的检查单之后：

1. **版本提升 (Bump Version)**: 
   - Backend `pyproject.toml` 中的 `version` 字段。
   - Frontend `package.json` 中的 `version` 字段。
   - OpenSpec API 或文档约定的全局版本。
2. **移动变更**:
   - 将 `TODO.md` 中属于这一期的 ✅ 任务及修好的 🐛 缺陷，按照 "Added/Changed/Fixed" 提纯。
   - 打开 `docs/changelog/CHANGELOG.md`，新建一个诸如 `## [1.2.0] - 2026-04-10` 的头部配置。把提纯内容填进去。
   - **清理原 TODO**，把已合并发版的这些事项删除或留少部分作为回顾。
3. **编写发布说明 (Release Notes)**:
   - PR 合并到 `main` 且打 Tag 时，GitHub Release 需要原原本本地拷贝这份 CHANGELOG 中对应版本的内容。
