# 🧪 HiveMind 测试标准 (Testing Standards)

## 1. 工具链 (Tooling)
- **Backend**: 必须使用 `pytest`。异步代码使用 `pytest-asyncio`。
- **Frontend**: 必须使用 `vitest` + `Testing Library`。

## 2. Mocking 准则
- 严禁在单元测试中调用真实的外部 API 或 数据库。
- 使用 `unittest.mock` 或 `pytest-mock` 模拟 Service 层和 Repository 层。
- 对于外部 HTTP 调用，使用 `httpx` 的 `ASGITransport` 或专门的 Mock 库。

## 3. 测试覆盖维度
- **Happy Path**: 验证正常输入下的预期输出。
- **Edge Cases**: 边界值（空字符串、极长内容、零、负数）。
- **Error Handling**: 验证预定义的 Exception 是否被正确抛出。
- **Security**: 验证鉴权逻辑是否能阻断未授权请求。

## 4. 命名规范
- 文件名: `test_<module_name>.py`。
- 函数名: `test_<function_name>_<scenario>_<expected_outcome>`。
  - 例如: `test_add_todo_empty_title_raises_error`。
