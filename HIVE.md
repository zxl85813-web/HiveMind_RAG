# HiveMind Project Governance (HIVE.md)

## 🔴 全局红线 (Global Redlines)
- **Async Only**: 所有 I/O 操作（DB, Network, File）必须使用 `async/await`。禁止使用同步阻塞调用。
- **No Print**: 禁止在 `backend/app` 下使用 `print()`。必须使用 `app.sdk.core.logging.logger`。
- **Explicit Returns**: 所有 public 函数必须有明确的类型注解 (Type Hints)。
- **Registry Required**: 所有的 Service 类必须使用 `@register_component` 装饰器。

## 🟠 架构建议 (Architecture Guidelines)
- **SDK First**: 优先使用 `app.sdk.core` 中的工具，不要重新发明轮子。
- **Traceability**: 每个复杂的逻辑块应包含一个 `trace_id` 的记录。
- **Error Handling**: 必须抛出 `HiveMindException` 的子类，禁止捕获万能 Exception 后静默处理。
