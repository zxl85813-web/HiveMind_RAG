# 🤝 贡献指南 — HiveMind RAG

感谢你对 HiveMind RAG 的贡献！本仓库采用 **Issue 驱动 + Agent 辅助** 的开发模式。

> [!TIP]
> **深度治理手册**: 本文档仅包含快速上手概要。全量的 SOP、编码规范、架构准则和质量门禁，请务必阅读单一事实源：
> 👉 **[docs/DEV_GOVERNANCE.md](docs/DEV_GOVERNANCE.md)**

---

## 🌿 1. 分支策略 (Branch Strategy)

所有代码变更必须通过 Pull Request。

*   **main**: 受保护的生产分支，禁止直推。
*   **develop**: 开发集成分支。
*   **feature/issue-{ID}**: 新功能分支。
*   **fix/issue-{ID}**: Bug 修复分支。

**命名规范**: `<type>/issue-<ID>-<short-description>`

---

## 🔄 2. 极简贡献流程

1.  **领取任务**: 在 [GitHub Issues](https://github.com/zxl85813-web/HiveMind_RAG/issues) 中通过评论领取任务。
2.  **创建分支**: 从 `develop` 切出你的特性分支。
3.  **遵循规范**: 你的代码必须通过 `.agent/rules/` 下的架构约束，并遵守 `docs/DEV_GOVERNANCE.md` 里的 SOP。
4.  **提交代码**: 使用 **Conventional Commits** 规范提交。
5.  **发起 PR**: 关联 Issue ID (如 `Closes #123`)，并通过所有 CI 质量门禁。

---

## ✅ 3. 提交前 Checklist (30s 自查)

- [ ] **资产登记**: 如果新增了 API 或模块，是否已在 [REGISTRY.md](REGISTRY.md) 登记？
- [ ] **任务更新**: `TODO.md` 是否已通过 `/update-todo` 正确标注当前任务状态？
- [ ] **质量检查**: 本地是否已运行 `./.agent/checks/run_checks.ps1`？
- [ ] **文档关联**: PR 描述是否指向了对应的设计文档 (DES-NNN)？

---

## 🔗 4. 核心参考链接

| 内容 | 链接 |
|:---|:---|
| **开发治理手册** | [docs/DEV_GOVERNANCE.md](docs/DEV_GOVERNANCE.md) |
| **功能注册表** | [REGISTRY.md](REGISTRY.md) |
| **任务看板** | [TODO.md](TODO.md) |
| **架构演进记录** | [docs/changelog/CHANGELOG.md](docs/changelog/CHANGELOG.md) |
| **共学体系** | [docs/COLLABORATIVE_LEARNING.md](docs/COLLABORATIVE_LEARNING.md) |

---
> _“让每一行代码都有据可查，让每一处设计都服务于群体进化。”_
