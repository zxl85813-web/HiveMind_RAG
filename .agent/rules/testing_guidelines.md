# Testing Guidelines & Mock Strategies

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
