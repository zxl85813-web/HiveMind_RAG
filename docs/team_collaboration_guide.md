# 🤝 Github 协同开发指南 (1-3人小团队)

对于你和一两个朋友一起开发 `HiveMind RAG` 这个项目，我们可以充分利用 GitHub 提供的轻量级但强大的协作功能，结合我们体系中已有的规范，让合作即顺畅又规范。

以下是我为你整理的协作全景图和推荐功能：

---

## 1. 核心大动脉：Issue 驱动开发 (Issue-Driven)
**你们不需要每天开早会，GitHub Issue 就是你们的在线看板和会议室。**

*   **功能**: `GitHub Issues` + `Project Boards`
*   **怎么玩**:
    1.  把你要做的东西（比如我们刚才讨论的 *Code Vault* 功能）或 Bug 拆解成一条条的 Issue。
    2.  利用 GitHub 的 **Assignees**，明确把 Issue 分派给你或你的朋友。
    3.  使用我们在项目里预设的 Labels (比如 `bug`, `feature`, `P1`, `RAG_Core`) 让大家一眼知道优先级和模块。
    4.  *(进阶)* 开启一个简单的 **GitHub Project (Kanban)**，设立 `To Do`, `In Progress`, `Reviewing`, `Done` 四个大列，Issue 状态一目了然。

## 2. 兵分两路，殊途同归：分支与 Pull Request (PR)
**绝不要三个人都在 `main` 主分支上提代码，这会造成灾难性的代码冲突。**

*   **功能**: `Branching` + `Pull Requests (PR)` + `Code Review`
*   **怎么玩**:
    1.  你的朋友要开发某个功能（比如 Issue #5），他需要从 `main` 检出一个新分支：`feature/issue-5-code-vault`。
    2.  他在自己的分支上随便折腾、随便 commit。
    3.  等他做完了，在 GitHub 上提一个 **Pull Request (请求合并到 main)**。
    4.  **强制规则**：在 PR 的描述里写上 `Closes #5`。只要这个 PR 被合并，Issue #5 就会自动关闭！
    5.  你作为项目的主导者，可以在 PR 页面里阅读他写的代码，提供评论 (Comment)，甚至要求他修改 (Request Changes)。

## 3. 防守底线：分支保护与自动化审查 (Branch Protection & GitHub Actions)
**为了防止朋友（或你）不小心写了有 Bug 的代码冲坏主流程。**

*   **功能**: `Branch Protection Rules` + `GitHub Actions` 
*   **怎么玩**:
    1.  **开启分支保护**：进入 GitHub 仓库 Settings -> Branches，为 `main` 分支添加保护规则。勾选 **Require a pull request before merging**（禁止直接 Push，必须提 PR）和 **Require approvals**（必须至少 1 个人点 Approve 才能合并）。
    2.  **设置状态检查**：我们项目里已经有 `.agent/checks/code_quality.py` 的质量检查脚本或者 `pytest`。我们可以配置一个简单的 GitHub Action (CI 流水线)，**每次有人提交 PR，云端服务器自动帮你们跑完 Lint 和测试**。如果报错变成了 ❌ 红叉，GitHub 直接锁死 Merge 按钮，不让人合进去代码。

## 4. 知识沉淀与讨论：GitHub Discussions / Wiki
*   **功能**: `Discussions` 或 `Wiki`
*   **怎么玩**:
    像我们之前讨论的各种复杂的架构（为什么要用 Neo4j、什么是 3 层记忆结构），直接放在代码里新人可能看不懂。可以开启 GitHub 的 Discussions 板块作为团队论坛，或者整理在 `docs/` 下推送到仓库里让大家查阅。

### 🚀 给你的落地建议：
如果你打算这周起拉朋友进场，你们的日常循环应该是这样的：
1. **你** 在 GitHub 建 Issue 并分配给他。
2. **他** 领取 Issue，在本地切出 `feature/issue-xxx` 开始写（也可以让 AI 帮他写）。
3. **他** 提一个 PR 到 `main`。
4. **GitHub Action (CI)** 自动运行，告诉你代码有没有编译错误。
5. **你** 登陆 GitHub，点开 PR 进行 Code Review，觉得不错点 `Approve`。
6. 点击 `Squash and Merge`，代码进入主分支，自动关闭卡片。
