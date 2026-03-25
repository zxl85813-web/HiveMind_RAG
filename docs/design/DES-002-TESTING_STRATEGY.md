# 🧪 DES-002: HiveMind 全链路测试与质量保障策略

> **状态**: Active | **版本**: 2.0 (整合版)  
> **单一事实源**: 本文档替代了原有的 `docs/design/testing_guideline.md` 和 `docs/testing_plan.md`。

---

## 🏛️ 1. 核心测试哲学 (Core Philosophy)

### 1.1 文档驱动测试 (Design-Driven Testing)
**测试用例是设计文档的直接投影，而不是代码的附属品。**
*   **唯一事实来源**: 一切测试以 `docs/design/` 下的设计文档和接口规范为准。
*   **双视角验证**: 
    1.  **实现视角**: 验证代码是否按逻辑运行。
    2.  **契约视角**: 验证输出是否符合设计文档定义的 Schema 和业务契约。

### 1.2 智能体驱动 QA (Agentic QA)
引入 **QA Agent** 角色：在代码编写前，QA Agent 基于 `DES-NNN` 文档自动生成 `tests/` 套件。开发者的任务是让测试全绿，实现真正的“测试先行”。

---

## 📐 2. 测试金字塔与目录结构 (Test Pyramid)

所有后端测试均位于 `backend/tests/` 目录下：

| 层级 | 目录 | 黄金准则 | 工具 |
| :--- | :--- | :--- | :--- |
| **Unit** | `tests/unit/` | **隔离一切外部 I/O**。严禁连接 DB、Redis 或调用真实 LLM。 | `pytest`, `unittest.mock` |
| **Integration** | `tests/integration/` | 验证组件间连通性。允许连接测试专用数据库。 | `Testcontainers`, `SQLModel` |
| **E2E** | `tests/e2e/` | **完全模拟用户请求**。从 HTTP 路由入口触发。 | `FastAPI TestClient`, `Playwright` |

---

## 🤖 3. LLM / AI 系统专项规范

针对大模型的非确定性输出，必须遵守以下约定：

1.  **强制 Mock**: 在 Unit 测试中必须 Mock `LLMService`。禁止在 CI 流程中消耗真实 Token。
2.  **模糊断言 (Fuzzy Assertions)**: 避免 `assert resp == "exact string"`。应使用包含性断言 (`assert "target" in resp`)、结构校验或由另一个 LLM 片段进行语义评估。
3.  **流式拦截**: 针对 SSE 输出，必须验证 Chunk 的连续性和异常中断后的状态恢复逻辑。

---

## 📋 4. 关键测试场景清单

### 4.1 后端核心 (Backend)
*   **知识库服务**: 验证 ACL 权限隔离（Admin/User/部门）、版本递增、文档逻辑删除后的清理。
*   **Swarm 编排**: Mock Agent 节点，验证任务分发 DAG 是否按预期状态转移。
*   **脱敏服务**: 针对手机号、身份证、API Key 的识别准确率与脱敏方法（掩码/哈希）验证。

### 4.2 前端交互 (Frontend)
*   **状态一致性**: 验证 `chatStore` 在高频流式更新时不会出现闭包陷阱（Stale Closure）。
*   **组件韧性**: 验证 `ChatPanel` 长文本渲染、代码高亮，以及 `ErrorBoundary` 在组件崩溃时的自愈。
*   **网络容错**: 模拟 401/403/500 状态码，验证 UI 是否有对应的 Toast 提示。

### 4.3 全链路 (E2E)
*   **知识发现闭环**: 用户上传 PDF -> 自动解析/脱敏 -> Chat 提问 -> 验证引用标记能否正确溯源。
*   **权限管控流**: 验证用户 A 的私有文档对用户 B/C 的不可见性。

---

## 🚀 5. 性能指标与 SLO (Performance)

| 指标 | 目标 (Goal) | 观测点 |
| :--- | :--- | :--- |
| **首字响应 (TTFT)** | < 1.5s (1M Context) | SSE 第一个 Chunk 返回时间 |
| **检索延时** | < 500ms (10W级文档) | Hybrid Search (Vector + Graph) |
| **并发容量** | 50+ 并发对话流 | 峰值内存、连接池占用 |
| **自愈时间** | < 3s | 依赖服务 (Redis/Neo4j) 宕机后的降级响应 |

---

## ✅ 6. 完工标准 (DoD)

*   **P0 Case 通过率**: 100%。
*   **覆盖率基础**: 后端核心逻辑 > 85%，前端状态机 > 90%。
*   **自动回归**: 每次 PR 必须通过全量单元测试和 Smoke E2E 测试。
*   **文档同步**: 任何代码逻辑变更必须同步更新相应的测试用例说明。

---
> _“测试不是为了证明代码没有错误，而是为了确保代码正在做设计让它做的事。”_
