# 🤝 团队协作与代码提交规范 (Team Collaboration Standards)

> 关联文档: [`.agent/rules/project-workflow.md`](project-workflow.md) (多角色流转梳理)

在 HiveMind RAG 的多角色 (PO / Architect / Dev / Reviewer / AI Agent) 混合研发场景中，代码如何流动、如何提交、以及在遇到冲突时如何合并，需要严格的底线。

本文档规定了 Git Flow 协作分支模型、Commit 信息规范、PR 合并审查流，以及 **Agent Skills 与 GitHub Issues 的双向绑定机制**。

---

## 1. Git 分支管理策略 (Branching Strategy)

我们采用轻量级的 GitHub Flow 变种，以 `main` 分支作为唯一事实来源。

| 分支类型 | 命名规范 | 来源 | 合并到 | 描述与限制 |
| --- | --- | --- | --- | --- |
| **主分支** | `main` | - | - | **始终处于安全可发布状态**。禁止直接 push，必须通过 PR 保护。 |
| **功能分支** | `feature/issue-{ID}-{简述}` | `main` | `main` | 如 `feature/issue-42-rag-rbac`。处理带有新功能或架构修改的 Issue。 |
| **修复分支** | `fix/issue-{ID}-{简述}` | `main` | `main` | 如 `fix/issue-91-jwt-bug`。用于处理紧急或积累的代码修补。 |
| **探索分支** | `experiment/{动作}` | `main` | `main` (可选) | 用于概念验证 (PoC) 或引入破坏性极大、不确定是否保留的改动。 |

---

## 2. 代码提交规范 (Commit Convention)

所有入库的代码记录必须强依赖 **Conventional Commits** 规范。AI Agent 尤其需要严格遵守此项。这直接影响从 GitHub 到 OpenSpec 再到 Changelog 的自动化提取。

### 2.1 格式要求
```text
<type>(<scope>): <subject>

<body>

<footer>
```

*   **type（必填）**：定义变动的类型。
    *   `feat`: 新功能 (Feature)
    *   `fix`: 修复缺陷 (Bugfix)
    *   `docs`: 仅文档更改 (Documentation)
    *   `style`: 代码格式化 (不影响代码执行)
    *   `refactor`: 重构 (既不修复 bug 也不添加新功能的代码更改)
    *   `perf`: 性能优化
    *   `test`: 增加或修改测试用例
    *   `build`/`ci`: 构建系统或 CI 配置文件修改
    *   `chore`: 杂务，不修改 src 或测试文件的任务 (如更新 `.gitignore`、更新依赖)
*   **scope（必填）**：说明变动影响的范围，比如 `auth`, `ui`, `rag`, `agent`, `docs`。
*   **subject（必填）**：简短描述（不超过 50 字符）。以动词开头，使用祈使句（如 "add" 而不是 "added"），不要大写首字母，结尾不加句号。
*   **body（可选）**：详细描述这次修改的原因和机制。
*   **footer（极度重要）**：如果该 commit 解决了一个具体的 Issue，**必须**在这里关联：`Closes #12` 或者是 `Resolves #44`。

### 2.2 标准化示例
*   `feat(auth): implement real JWT validation via pyjwt`
    *   _body_: 移除了 mock 验证，接入了真正的 token 服务。
    *   _footer_: `Resolves #42`
*   `fix(ui): correct chat bubble padding on mobile screens`
    *   _footer_: `Fixes #18`

---

## 3. Pull Request 与合并审查单 (PR & Merge Pipeline)

所有的分支往 `main` 合并前，必须经过严谨的自动化体系和人类 Review。

### 3.1 PR 标题与描述
*   标题格式需匹配 Commit 规范：`feat(rag): add graphical entity extraction`
*   描述内容要求：必须声明 `Closes #XXX`，并附有截图/测试用例覆盖结论。

### 3.2 合并前必须通过的 CI Checks (代码自查护城河)
在 GitHub Actions 或本地 `/agent/checks/run_checks.ps1` 跑通前，**禁止强行合并**：
1.  **Linter**: 后端 `flake8` / 前端 `eslint` 不报 error。
2.  **Type Checker**: 后端 `mypy`。
3.  **Tests**: 触发双视角测试（Unit + Integration）。后端通过 `pytest`，并必须满足 Coverage `> 80%`。
4.  **Audit**: 审查是否有敏感词或裸露的 API Key 硬编码在代码中。

### 3.3 合并策略 (Merge Strategy)
*   推荐使用 **Squash and Merge**。保持 `main` 分支是线性且纯净的历史：1 个变动 = 1 个 PR = 1 个 Commit（其标题就是 Feature Name）。

---

## 4. Skills 与 GitHub Issues 双向绑定机制 (The Binding Loop)

这个体系是使得 AI Agent (如我们的 `OpenSpec` 工作流或 `generate-tests` Skill) 能在团队里真正与人类并肩作战的纽带。

### 4.1 "下发" 机制：Issue 驱动 Skill 触发
团队的人类 (PO / Reviewer) 不需要在终端敲复杂的命令。驱动研发的唯一凭证是 **GitHub Issue**：
1.  **人类建单**：人类在 GitHub 提一个 Issue: `#103 [Feature] Add multi-turn memory isolation`。
2.  **触发工作流**：我们定义当开发者（可以是 AI）接手这个单子时，强制运行一条命令打通 Skill：
    ```bash
    # 使用 OpenSpec Skill 拆解 Issue
    /opsx-explore --issue=103
    ```
3.  这会导致 Agent 去阅读 `#103` 的要求，去寻找相关的系统架构文件，并生成代码。在生成的每个 commit 中，Agent 必须自带 `Resolves #103` 尾缀。

### 4.2 "向上" 机制：Skill 生成 Issue 及报告
当 AI 技能在扫描和执行时遇到长期的、系统性的阻滞点（比如：依赖安装错误、测试集不够、遇到重大技术债），或者我们在执行 `/code-review` 时发现了坏味道，**AI 严禁自己吞掉这个错误或直接罢工**。

1.  **AI 创建 Issue**：Skill 的内部逻辑带有自动报告的功能。当 `generate-tests` 出现 `Blocked` 状态时，应当调用 GitHub API 自动建单或在对应的 Issue 下面留言：
    > ⚠️ **[AI Bot 回报]**: "未能为 `chat_service.py` 生成完整的测试，原因是 `DesensitizationEngine` 的依赖无法在 sqlite 内存库中 Mock。需要先完成 Issue #92 中的注入重构。"
2.  **关联 TODO.md**：所有通过 API 推送到 GitHub 的 Issue，必须以超链接或标号形式，被反向写回 `TODO.md` 中，如：`- [ ] 修复脱敏引擎的测试隔离问题 (#104)`。

### 4.3 `TODO.md` 的双向折叠（Single Truth）
我们的 `TODO.md` 是一个“快照”。它的存在不是为了取代 GitHub Issues，而是将散落在 GitHub 的卡片汇聚在开发者的视野里。
*   完成开发，PR 带有了 `Resolves #XXX` 并被 Merge 的那一刻，GitHub Issue 将自动标记为 Done。
*   在当天的收尾脚本或者开发结束前，执行 `/update-todo` 工作流时，系统（或协助的 AI）会主动清理 `TODO.md`，把带有 `#XXX` 且已关闭的任务自动标记为 ✅，并进入月底的 `CHANGELOG.md` 提取范畴。
