# 🧪 综合测试规范与策略指南 (Testing Guidelines)

本文档定义了 HiveMind RAG 项目的测试体系、层级结构、命名规范以及在复杂环境下的 Mock 策略。遵循本项目 [研发方法论](design-and-implementation-methodology.md) 中的**“双视角”测试原则**。

---

## 0. 总则与测试框架体系

### 0.1 测试分层金字塔 (Testing Pyramid)
我们期望的自动化测试分布如下：
1. **单元测试 (Unit) - 70%**: 针对独立的工具函数、计算逻辑和单个的 Service 方法。无网络请求，极少真实数据库交互。执行速度必须在毫秒级。
2. **集成测试 (Integration) - 20%**: 覆盖 API 路由层 (`api/routes`) 到 Service 再到数据库的贯通。使用内存型数据库（如 SQLite `sqlite+aiosqlite:///:memory:`）。可以 Mock 外部大模型请求。
3. **端到端测试 (E2E) - 10%**: 真实的 Frontend 通过浏览器驱动 (Playwright) 挂载到真实的 Backend。仅覆盖主干流程（如知识库上传、发起聊天），用于验收。

### 0.2 覆盖率要求 (Coverage Requirements)
- **全局要求**: 整体代码覆盖率必须达到 `80%` (`fail_under = 80`)。
- **新增代码**: 每次提交的增量代码覆盖率必须达到 `90%`。没有测试覆盖的 PR 将被 CI 直接拒绝。

### 0.3 文件命名与组织架构
测试文件必须镜像存放于 `tests/` 或组件所在同级目录，名称严格对齐：
- **后端 (Pytest)**: 放在 `backend/tests/` 下。例如，测试 `app/services/chat_service.py` 的文件必须是 `backend/tests/unit/services/test_chat_service.py`。所有的测试函数必须以 `test_` 开头。
- **前端 (Vitest)**: 组件测试放在对应组件目录的 `__tests__` 下或直接同级。例如，测试 `ChatBubble.tsx` 必须命名为 `ChatBubble.test.tsx`。

### 0.4 Mock 决策树 (When to Mock?)
当你在写测试并犹豫是否要 Mock 一个依赖时，按以下顺序决策：
1. **是系统级的依赖库 (如 os.time, uuid) 吗？** 👉 如果必须固定返回值，用 `mock.patch`。
2. **是耗时的 I/O 或昂贵的第三方服务吗 (如 LLM 调用、发送邮件)？** 👉 **必须 Mock**。禁止在跑测试时真实扣费。
3. **是本系统内部的另一个 Service 或复杂逻辑吗？** 👉 **先尝试不用 Mock**。尽可能构造前置数据（Fixtures），让测试穿透业务逻辑，这叫“宽隔离”。只有当构建状态过于困难或引发级联死循环时，才局部 Mock 掉深层的方法。
4. **是数据库 (Session) 吗？** 👉 在 Unit 测试如果纯测计算可以 Mock (麻烦，见下文踩坑记录)；在 Integration 测试**禁止 Mock Session**，必须连那个用内存起起来的虚拟 SQLite 库真实跑 DDL 和 DML！

### 0.5 “双视角”测试的落实要求
每次为新 API 写测试时，你至少需要准备这两类 Case：
- **契约视角 (Contract/Black-box)**: 给正确的 Input，断言 Status Code 是 200 且拿到了遵循 `ApiResponse` 约定的 JSON。给非法的 Input（如越权、断链 ID），断言返回 400 且包裹出错信息。
- **容错视角 (Logic/White-box)**: 人为用 Mock 抛出一个深层次错误（如假装在保存数据时 `SQLAlchemyError` 宕机），断言你的系统会妥善 catch 这个异常，并返回安全的 500 信息而不仅是把整个进程搞挂。

---

## 1. 常见陷阱与具体的 Mock 策略 (Pitfalls & Advanced Mocking)

## 1. Pydantic V2 Model Initialization (Strict Validation)
Pydantic V2 is strict about required fields during instantiation. 
**Rule:** When testing functions that take Pydantic models (like `RetrievalContext` or `ChatRequest`), you **MUST** provide all required fields directly in the constructor. Do not instantiate the object and then dynamically add fields later. 
**Example (Incorrect):**
```python
ctx = RetrievalContext(query="test")
ctx.kb_ids = ["kb1"] # Will raise ValidationError mapping 'kb_ids' is missing during __init__
```
**Example (Correct):**
```python
ctx = RetrievalContext(query="test", kb_ids=["kb1"])
```

## 2. Async Generators Mocking (The "AsyncMock Hell")
Handling `async for` loops and streaming responses in Python `unittest.mock` is notoriously tricky and will lead to `RuntimeWarning: coroutine was never awaited` if done incorrectly.
**Rule:** An async generator is a standard synchronous function that returns an asynchronous iterator. Therefore, you must use a standard `MagicMock` whose `return_value` is explicitly set to an async generator function result, **NOT** an `AsyncMock`.

**Example (Incorrect):**
```python
mock_llm.chat_stream = AsyncMock(return_value=my_generator())
```
**Example (Correct):**
```python
async def mock_stream_gen():
    yield "Hello"
    yield " World"
mock_llm.chat_stream = MagicMock(return_value=mock_stream_gen())
```

## 3. Asynchronous Database Sessions Mocking
Similar to streaming, mocking `get_db_session()` which yields an `AsyncSession` requires a proper async generator approach.
**Rule:** If `get_db_session()` yields a session using `async for session in get_db_session():`, mock it with `side_effect` pointing to an async generator function.
**Example (Correct):**
```python
mock_session = AsyncMock()
async def mock_get_db_gen():
    yield mock_session
mock_get_db.side_effect = mock_get_db_gen
```

## 4. Avoiding Deeply Coupled Static Methods
When writing business logic like `ChatService.chat_stream`, avoid hardcoding `get_db_session()` inside the method body. This forces the test to use deep patching (`patch("app.services.chat_service.get_db_session")`).
**Recommendation (For Future Development):** Move toward **Dependency Injection** (e.g., FastAPIs `Depends`) or pass the `session` and `llm` clients directly into the class `__init__` or method signature. This drastically reduces the need for complex, brittle `unittest.mock.patch` trees.

## 5. Scope-Leak Detection (Variable Shadowing)
Unit tests act as extreme linting tools. They will catch issues like local scope shadowing. 
**Rule:** Keep `import` statements at the top of the file unless absolutely necessary. A local `import json` inside a deeply nested `try/except` block can mask global imports and raise `UnboundLocalError` across await boundaries or early returns.

## 6. Prefer Integration Testing over Granular Mocks for Core Pipelines
**Recommendation:** For heavy routing pipelines like `chat_stream`, prefer an integration test using the `sqlite+aiosqlite:///:memory:` configured in `pytest.ini`. Mock **only** external HTTP boundaries (like LLM API calls). Let the real database handles, retrieval logic, and agent state run through the in-memory SQLite instances.

## 7. End-to-End (E2E) Integration Testing Experience

When connecting the real Frontend to the real Backend (疏通测试), mock functions and unit tests often fall short. We've compiled the following heuristics based on actual system integration experience:

### 7.1 Testing Data Contracts (API Responses)
- **The "Naked Array" Trap:** UI components (like `List` or `.map()`) will fatal crash if they receive an `undefined` or object instead of an array.
- **Rule:** Frontend integration tests and component tests MUST verify data extraction paths. If the backend is wrapped in an `ApiResponse` contract (`{success, data, message, code}`), all mocked API resolutions and E2E asserts must mimic this structure (`res.data.data`), NOT raw arrays.

### 7.2 System Resilience & Error Boundaries
- **The Blank Page of Death:** A single unhandled promise rejection or mapping error in a deep child component (e.g., fetching a Knowledge Base list) can tear down the entire React concurrent tree.
- **Testing Rule:** Write E2E/Integration tests that intentionally trigger 403, 404, or CORS issues (e.g., misconfigured backend) on non-critical paths. Verify that the UI displays a generic Error Boundary or Ant Design `message.error()` rather than crashing the `/agents` page completely.

### 7.3 CORS & Network Debugging
- E2E testing requires the browser to enforce real security constraints.
- **Validation:** Always test UI-Backend connectivity on the exact ports that will be used in development and production (e.g., `5173`). An API that passes backend `pytest` can still fail in real-world E2E if `CORS_ORIGINS` in `.env` lacks the Frontend's origin.

### 7.4 Auth Downgrade for Unblocking UI Tests
- When bridging heavy frontend systems before user authentication is fully implemented, do not let 403 blocks halt development.
- **Recommendation:** Implement a temporary "Mock User" bypass inside `Depends(get_current_user)`. Ensure all downstream dependencies (Knowledge Base ownership, Chat History) hinge smoothly on this hardcoded Mock ID until the full authorization token workflow is ready for E2E validation.
