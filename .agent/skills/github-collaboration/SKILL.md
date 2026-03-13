---
name: github-collaboration
description: 整合 GitHub Discussions 和 Projects 进研发展开流程，实现从本地自省到团队协作的高级联动
---

# 🤝 GitHub 全面协作技能 (Skill)

> **使用场景**: 
> 1. 当 `ReflectionAgent` 发现了一个深刻的架构 Gap 或技术洞察，需要向团队发起讨论时 (Discussions)。
> 2. 当需要建立一个可视化的 Kanban 面板来追踪 `TODO.md` 中的多阶段任务进度时 (Projects)。

## 🛠 前提条件

1.  确保 `backend/.env` 中已设置具有 `read:project`, `write:discussion` 等权限的 `GITHUB_TOKEN`。
2.  确保 `backend/app/scripts/github_collab.py` 脚本已就绪。

## 📝 执行步骤

### 场景 A: 发起团队讨论 (Discussions)
当你在自省日志中发现了一个需要团队决策的问题：
1.  **提取内容**: 确定讨论的标题和主要观点。
2.  **调用技能**:
    ```powershell
    python backend/app/scripts/github_collab.py discuss --title "关于 RAG 缓存失效策略的建议" --body "..." --category "Ideas"
    ```

### 场景 B: 同步至项目面板 (Projects)
将 `TODO.md` 中的看板状态同步到 GitHub Project (V2)：
1.  **运行同步**:
    ```powershell
    python backend/app/scripts/github_collab.py sync-project --project-name "HiveMind Roadmap"
    ```
- 脚本会自动将标记为 `⬜` 的任务放入 `Todo` 状态。
- 将标记为 `🟡` 的任务放入 `In Progress` 状态。
- 将标记为 `✅` 的任务放入 `Done` 状态。

## 🛡️ 最佳实践
- **自动闭环**: 讨论得出结论后，应通过 `project-steward` 将结论沉淀为本地 ADR 文档。
- **状态对齐**: 始终以 `TODO.md` 为状态真值，脚本负责单向同步到 GitHub Projects 以便团队视察。
