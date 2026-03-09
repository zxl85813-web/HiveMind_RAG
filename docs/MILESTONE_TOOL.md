# GitHub Milestone 工具

用于把 `TODO.md` 指定章节自动同步到 GitHub Milestone，并可选创建任务 Issues。

## 脚本位置

- `backend/scripts/create_github_milestone_from_todo.py`

## 功能

- 解析 `TODO.md` 某个章节下的任务条目（默认章节：`### 0.2 本周执行序列（按依赖排序）`）
- 创建（或复用同名）Milestone
- 可选为每个任务创建 Issue，并自动挂到该 Milestone 下
- 默认 `dry-run`，不会改 GitHub

## 前置条件

1. 设置 GitHub Token（需有 repo 权限）
2. 提供仓库名 `owner/name`

PowerShell 示例：

```powershell
$env:GITHUB_TOKEN="<your_token>"
```

## 使用示例

### 1) 仅预览（不修改 GitHub）

```powershell
C:/Users/linkage/Desktop/aiproject/.venv/Scripts/python.exe backend/scripts/create_github_milestone_from_todo.py
```

### 2) 创建 Milestone

```powershell
C:/Users/linkage/Desktop/aiproject/.venv/Scripts/python.exe backend/scripts/create_github_milestone_from_todo.py \
  --apply \
  --repo zxl85813-web/HiveMind_RAG \
  --milestone-title "M7 Agent TODO Sprint" \
  --due-on 2026-03-31
```

### 3) 创建 Milestone + 自动建 Issues

```powershell
C:/Users/linkage/Desktop/aiproject/.venv/Scripts/python.exe backend/scripts/create_github_milestone_from_todo.py \
  --apply \
  --repo zxl85813-web/HiveMind_RAG \
  --milestone-title "M7 Agent TODO Sprint" \
  --create-issues \
  --labels "todo-sync,agent,planning"
```

## 常用参数

- `--todo`：TODO 文件路径（默认 `TODO.md`）
- `--section`：要解析的章节标题（精确匹配）
- `--milestone-title`：Milestone 标题
- `--milestone-description`：Milestone 描述
- `--due-on`：截止日期（`YYYY-MM-DD`）
- `--repo`：仓库名（`owner/name`）
- `--token-env`：Token 环境变量名（默认 `GITHUB_TOKEN`）
- `--create-issues`：是否为条目创建 Issues
- `--labels`：创建 Issue 时附加标签（逗号分隔）
- `--apply`：执行写入（不加则 dry-run）
