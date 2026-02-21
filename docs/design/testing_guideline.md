# HiveMind Testing & QA Guidelines

## 1. 核心测试哲学 (Core Philosophy: Design-Driven Testing)

在 HiveMind 项目中，**Test Case (测试用例) 是设计文档的直接投影，而不是代码的附属品。**

*   **🚫 错误做法（代码驱动测试）**: 写完了业务代码，为了提高覆盖率，对着代码的分支结构反向猜测逻辑去补写 `assert`。这会导致“虽然覆盖率 100%，但把一开始设计时的架构漏洞也固化在了测试里”。
*   **✅ 正确做法（文档驱动测试/TDD）**: 一切测试以 `docs/design/` 下的设计文档和接口规范为 **唯一事实来源 (Single Source of Truth)**。即使业务代码实现了花哨的功能，只要设计文档里没提，测试就不应该涉及（或需要倒逼更新设计文档）。

---

## 2. Agentic QA Workflow (智能体驱动测试流)

为了贯彻上述哲学，我们将引入 **QA Test Expert Agent (测试专家智能体)** 流程。未来的开发周期如下：

1.  **架构师 Agent (或人类)**: 产出 `docs/design/xxx.md` (如之前的 `multi_tier_memory.md`)。
2.  **QA 测试专家 Agent**:
    *   **完全不看** `backend/app/` 下的实现代码！
    *   只审阅 `xxx.md` 设计文档，根据其中描述的“输入、输出、边界条件、核心业务逻辑”，产出一套严格的 `test_xxx.py` (包含 Mock 规划和边界断言)。
3.  **开发专家 Agent (或人类)**:
    *   拿到 `test_xxx.py`，执行 `pytest`，看到满屏红色（Error）。
    *   开始编写/重构 `backend/app/` 下的业务代码。
    *   直到所有依据“设计文档”编排的测试全绿（Passed）。

---

## 3. 测试分类与目录结构规范

所有测试必须放置于 `backend/tests/` 下，严格按照以下三层结构划分：

### 3.1 Unit Tests (单元测试) `tests/unit/`
*   **黄金准则**: **隔离一切外部 I/O。**
*   **限制**: 不能连接真实的 PostgreSQL, Redis, Elasticsearch, Neo4j。不能调用真实的 LLM 耗费 Token。
*   **手段**: 大量使用 `unittest.mock` 拦截 `httpx`, `AsyncOpenAI` 或使用内存级数据库（如 `sqlite:///:memory:`）。
*   **目标**: 验证纯粹的代码逻辑（算法、数据结构路由、异常处理抛出）。

### 3.2 Integration Tests (集成测试) `tests/integration/`
*   **黄金准则**: 验证组件间的连通性（模块 A 是否能把正确格式的包发给数据库 B）。
*   **允许**: 可以连接本机的开发数据库或使用 Testcontainer。
*   **限制**: 避免端到端的重度模拟，只验证**特定链路**（例如：测试 `IndexingService` 是否能把数据切分并正确存入 ChromaDB）。

### 3.3 End-to-End (E2E) 测试 `tests/e2e/`
*   **黄金准则**: 完全模拟一个前端用户请求。
*   **手段**: 使用 FastAPI 的 `TestClient` 或 `AsyncClient`，向 `/api/v1/xxx` 发送 HTTP 请求并断言。

---

## 4. LLM / AI 系统的专有测试约定

由于大语言模型输出的**非确定性 (Non-deterministic)**，测试时必须遵循以下规则：

### 4.1 Mocking 规则
在单元测试和快速 CI 流程中，**禁止调用真实大模型**。
*   如果要测“根据 LLM 返回的 JSON 更新数据库”，必须直接 `patch("app.core.llm.LLMService.chat_complete", return_value='{"status": "ok"}')`。

### 4.2 模糊断言 (Fuzzy Assertions)
如果在 E2E 测试中非得测一次真实 LLM 链路（例如验证 Prompt 效果）：
*   **绝不能**做精确相等断言: `assert resp == "你好"` ❌
*   **应当做**结构、包含性、或另一个 LLM 评估: `assert "你好" in resp` 或 `assert is_valid_json(resp)` ✅
