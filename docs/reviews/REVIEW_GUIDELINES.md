# 🔍 HiveMind 代码评审准则 (Code Review Guidelines)

> **核心宗旨**: 评审不是为了寻找瑕疵（Nitpicking），而是为了**知识分发 (Knowledge Transfer)** 和 **架构保鲜 (Architecture Freshness)**。

---

## 1. 评审者检查清单 (Reviewer Checklist)

评审一份 PR 时，请按顺序检查以下四个维度：

### 第一维度：架构契约 (Contract & Registry)
- [ ] 该变更是否已在 `REGISTRY.md` 登记？
- [ ] 是否违反了 `DES-004` 的 API 契约协议？
- [ ] 是否存在手动定义的前端类型（必须使用 `sync-api` 生成）？

### 第二维度：逻辑健壮性 (Logic & Safety)
- [ ] **错误处理**: 是否有针对网络超时、外部服务失败的 `try-except` 或 `ErrorBoundary`？
- [ ] **资源占用**: 数据库连接是否释放？循环中是否存在不必要的 API 调用？
- [ ] **并发安全**: 是否在 `async` 函数中错误使用了同步阻塞操作？

### 第三维度：智体亲和性 (Agent Compatibility)
- [ ] **可测性**: 该代码是否方便 Subagent 编写单元测试？（逻辑是否解耦）
- [ ] **可观测性**: 关键决策逻辑是否有明确的 `trace_id` 加注？

### 第四维度：代码风格 (Readability)
- [ ] 逻辑是否过于复杂？是否存在“投机性编程”（写了目前不需要的代码）？
- [ ] 变量命名是否具有语义（而非 a, b, temp）？

---

## 2. 评论礼仪 (Etiquette)

- **对事不对人**: 使用 "我们" 或 "可以通过...来改进" 而不是 "你的代码有问题"。
- **区分建议级别**:
    - `[P0] (Must Fix)`: 涉及到架构缺陷、契约破坏或业务 Bug。
    - `[P1] (Strongly Suggest)`: 涉及到代码优化、性能改进。
    - `[NIT] (Nitpick)`: 个人偏好、拼写错误。
- **正向激励**: 给好的设计点赞 (LGTM 🚢)。

---

## 3. 拦截策略 (Gate Enforcement)

- **L3 层级自动拦截**: 任何降低 RAGAS 测试得分、或破坏 `REGISTRY.md` 完整性的变更，应被 CI 自动拒绝。
- **同步要求**: 任何后端 Models 的变更，必须同时包含前端类型的同步输出。

---
*Created by Antigravity AI - HiveMind Governance Team*
