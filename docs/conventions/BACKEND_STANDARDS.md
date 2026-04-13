# 🐍 HiveMind 后端工程规范 (Backend Standards)

> **修订版本**: V1.1 (2026-04-12)  
> **适用范围**: Python 3.11+ / FastAPI / Pydantic V2

---

## 1. 架构与目录规范 (Architecture)

遵循“业务隔离，核心共享”的原则：
- `app/api/routes`: 仅负责路由分发、依赖注入与入参基础校验。
- `app/services`: 业务逻辑核心。所有副作用（DB、LLM、文件）必须在此闭环。
- `app/sdk`: 通用智体能力底座。禁止在此引用业务 Service。
- `app/common`: 协议与 DTO 模型。

## 2. API 响应与契约 (API Contract)

### 2.1 强制使用 `ApiResponse`
所有端点必须返回 `app.common.response.ApiResponse` 类型。严禁返回原始 `dict`。
```python
@router.get("/items", response_model=ApiResponse[list[Item]])
async def list_items():
    return ApiResponse.ok(data=await service.get_items())
```

### 2.2 命名转换
- 内部逻辑使用 `snake_case`。
- 传输层建议统一使用 `snake_case`（与 Pydantic 默认对齐），由前端通过 `sync-api` 生成对应类型。

## 3. 并发编程规范 (Concurrency)

### 3.1 Async/Await 准则
- **I/O 密集型** (API 调用, DB 读写): 必须使用 `async def` 和 `await`。
- **CPU 密集型** (复杂计算, AST 解析): 使用 `def` 或 `run_in_executor`。
- **禁令**: 严禁在 `async def` 中使用 `time.sleep()`，请使用 `asyncio.sleep()`。

## 4. 异常治理 (Error Management)

### 4.1 异常分层
- **业务预期内异常**: 抛出 `app.sdk.core.exceptions.AppError` 及其子类。
- **第三方服务异常**: 抛出 `ExternalServiceError` 并标注服务名 (如 "LLM", "Neo4j")。
- **统一处理器**: 所有异常由 `exceptions.py` 捕获并转译为 `success: false` 的标准 JSON 格式。

## 5. 智体开发规范 (Agent-Specific)

- **Token 敏感**: 所有的提示词 (Prompt) 注入点必须经过 `TokenService` 预估，严禁溢出。
- **状态持久化**: Swarm 执行过程必须有 Checkpoint (如 `SqliteSaver`)，确保后端重启可恢复。
- **可观测性**: 关键决策点必须使用 `logger.info` 并包含 `trace_id`。

---
*Created by Antigravity AI - Engineering Governance Team*
