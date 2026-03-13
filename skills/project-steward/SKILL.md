---
name: project-steward
description: "项目的数字管家，负责维护工程合规性、文档同步和注册表更新。当完成代码开发、需要发布版本、或需要整理项目待办事项时激活。确保代码变更在 REGISTRY.md, TODO.md 和 CHANGELOG.md 中有准确对应的记录。"
---

# Project Steward Skill

该 Skill 负责处理枯燥但在长期维护中至关重要的非代码任务，确保项目的“数字资产”始终处于最新且有序的状态。

## 1. 核心自动化流 (Workflows)

### A. 智能注册表维护 (Registry Sync)
当检测到代码变更（`.py`, `.ts`, `.tsx`, `.pydantic`）时：
1. **增量扫描**：通过 `REGISTRY.md` 确定已有条目，识别新增的 `Service`, `Schema`, `API` 或 `Front-end Component`。
2. **规范注入**：
   - **后端**：在 `## 后端资产` 表格中增加一行，包含名称、路径、负责人（默认为当前用户）和状态。
   - **前端**：在 `## 前端组件` 列表中登记组件功能和所属页面。
3. **一致性检查**：如果 Service 被重命名，自动提议修改 `REGISTRY.md` 对应的条目。

### B. 需求闭环与 TODO 治理
1. **REQ 映射**：在 `docs/requirements/REQ-NNN.md` 中，根据代码提交记录自动勾选已完成的任务项。
2. **TODO.md 强制同步**：对话结束前，检查是否有新增的临时任务或技术债，将其记录到根目录 `TODO.md` 的 `## Backlog` 中。
3. **过期清理**：建议清理超过两周未变动的 `In Progress` 任务。

### C. 发布与变更日志 (Release Coordination)
1. **语义化分析**：根据 `git diff` 或本轮对话涉及的功能点，自动起草 `docs/changelog/` 下的新文件。
2. **版本号计算**：
   - `Patch`: 仅涉及 Bug 修复（如：修复了 401 报错）。
   - `Minor`: 新增非破坏性功能（如：增加 FeedBack API）。
   - `Major`: 基础架构变更（如：迁移向量数据库、重构五层流）。

## 2. 强制文档准则 (Stewardship Rules)

- **Markdown 哲学**：所有文档修改必须保持原有的 Emoji 标题风格（如 🔌, ⚙️, 🧪）。
- **链接完整性**：在 `CHANGELOG.md` 中引用的需求 ID 必须包含指向 `docs/requirements/` 的相对链接。
- **无死链接**：同步注册表时，确保引用的代码文件路径在当前工程中真实存在。

## 3. 常用操作组合

| 意图 | 推荐指令 |
|------|------------|
| **功能上线** | `Update Registry` -> `Check REQ-NNN` -> `Tick TODO.md` |
| **版本收官** | `Generate Changelog` -> `Update project-structure.md` (如果目录有变) |
| **日常理算** | `Purge Completed TODOs` -> `Audit Registry Consistency` |
