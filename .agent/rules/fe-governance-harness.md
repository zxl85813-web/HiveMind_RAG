# 🛡️ Front-end Governance Harness (FE-GOV)

本文档定义了针对 HiveMind 前端架构治理的**“工程缰绳” (Engineering Harness)**。旨在通过自动化约束、结构化校验和强制性反馈循环，确保多用户隔离、连接生命周期管理以及持久化存储的一致性。

依据 [DEV-FE-GOV.md](../../docs/changelog/devlog/DEV-FE-GOV.md) 的治理目标，本 Harness 强制执行以下规则。

---

## 1. 核心约束域 (Governance Domains)

### 1.1 多用户 session 隔离 (Multi-User Isolation)
*   **缰绳规则：** 任何涉及 `useAuthStore` 或 `TokenVault` 的修改，**必须**同步校验下游持久化层的命名空间。
*   **自动化要求：** 必须通过 `frontend/e2e/isolation.spec.ts`。在执行 `/code-review` 或声称任务完成前，该测试必须为 ✅。
*   **静态检查：** 严禁在 `localStorage` 或 `IndexedDB` 中使用硬编码的静态 Key。所有 Key 必须通过 `tenant_prefix()` 辅助函数动态生成。

### 1.2 连接生命周期治理 (Connection Lifecycle)
*   **缰绳规则：** 所有的长连接（WebSocket, SSE）必须注册到 `ConnectionManager`。
*   **熔断触发：** 当 `401 Unauthorized` 发生或用户登出时，Harness 验证系统会检查 `AbortController.abort()` 是否被正确触发。
*   **验证：** 必须覆盖 `frontend/e2e/lifecycle.spec.ts` 中的“长连接瞬间熔断”场景。

### 1.3 追踪链路对账 (Tracing Reconciliation)
*   **缰绳规则：** 前端发出的每一个请求（通过 `AppClient`）必须携带 `x-hivemind-request-id`。
*   **对账校验：** E2E 测试必须验证断言：前端捕获的错误 Trace ID 与后端 Telemetry 系统记录的 Trace ID 严格对齐。

---

## 2. 自动化反馈循环 (Harness Loops)

### 2.1 任务前置检查 (Pre-Task Guardrails)
在修改涉及认证、存储或网络层的代码前，Agent 必须：
1.  **链路发现**：查询 Neo4j 架构图谱，确认受影响的下游组件（如：修改 `ConnectionManager` 会影响哪些 `ChatPanel` 实例）。
2.  **现场审计**：确认当前目录是否存在 `AGENTS.md` 定义的局部治理准则。

### 2.2 完工“自检”锚点 (Post-Task Verification)
当 Agent 声称“功能已实现”时，Harness 系统强制要求执行以下验证：
```bash
# 强制执行 E2E 隔离性回归测试
npx playwright test frontend/e2e/isolation.spec.ts frontend/e2e/lifecycle.spec.ts
```
**禁止依据“看起来没问题 (Vibe coding)”得出结论。**

---

## 3. 架构锚点 (Architectural Anchors)

本 Harness 与以下组件深度绑定：
- **存储**：`frontend/src/lib/auth/TokenVault.ts` (核心隔离点)
- **网络**：`frontend/src/lib/api/ConnectionManager.ts` (核心治理点)
- **对账**：`backend/scripts/seed_demo_eval.py` (提供测试基线数据)

---

## 4. 异常处理 (Backpressure)

如果验证失败，Agent **不得**尝试直接关闭任务，必须进入 `systematic-debugging` 流程：
1.  **复现**：通过增加观测日志提取失败时的 `SessionState`。
2.  **对比**：将当前失败状态与 `seed_demo_eval.py` 中的预期状态对比。
3.  **修复**：在满足本 Harness 规则的前提下重构代码。

---
> [!IMPORTANT]
> **本文档是强约束文件。** 任何跳过本 Harness 验证的代码合并均被视为对架构治理的违规。
