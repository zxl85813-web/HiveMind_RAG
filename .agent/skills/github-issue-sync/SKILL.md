---
name: github-issue-sync
description: 将本地需求文档 (REQ-NNN) 和 TODO 任务同步到 GitHub Issues
---

# 🚀 GitHub Issue 同步技能 (Skill)

> **使用场景**: 当在 `docs/requirements/` 创建了新需求，或在 `TODO.md` 中添加了新任务，且用户希望在 GitHub 上追踪这些进度时。

## 🛠 前提条件

1.  确保 `backend/.env` 中已设置 `GITHUB_TOKEN`。
2.  确保 Git 的 remote origin 已正确配置。
3.  确保脚本 `backend/app/scripts/sync_github_issues.py` 已存在并可运行。

## 📝 执行步骤

### 步骤 1: 准备内容
- 如果是同步新需求，请确保 `docs/requirements/REQ-NNN-slug.md` 文件内容完整。
- 如果是同步子任务，请在脚本中明确定义标题和描述。

### 步骤 2: 更新同步脚本
- 编辑 `backend/app/scripts/sync_github_issues.py`，将新的需求标题及其子任务添加到 `subtasks` 列表中。
- **重要**: 脚本会读取 `docs/github_issue_map.json` 映射文件以防止重复创建。

### 步骤 3: 运行同步器
// turbo
```powershell
python c:\Users\linkage\Desktop\aiproject\backend\app\scripts\sync_github_issues.py
```

### 步骤 4: 验证与关联
- 检查控制台输出，确认 "Success" 消息和 Issue 链接。
- 更新本地 `REQ-NNN.md` 文件，添加 GitHub Issue 链接：
  ```markdown
  | **GitHub Issue** | [#123](https://github.com/owner/repo/issues/123) |
  ```

## 🛡️ 最佳实践
- **原子化 Issue**: 一个子任务对应一个 Issue。
- **标签化管理**: 使用 `requirement`, `task`, `bug` 等标签进行分类。
- **双向追溯**: 始终将 GitHub Issue 编号反向关联到本地 Markdown 文档中。
