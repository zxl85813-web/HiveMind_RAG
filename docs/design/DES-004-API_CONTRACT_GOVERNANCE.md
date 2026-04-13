# 🛡️ DES-004: HiveMind API 契约与类型治理规范 (API Contract Governance)

> **修订版本**: V1.0 (2026-04-12)  
> **核心原则**: 后端 Pydantic 是一切 Schema 的**唯一事实来源 (SSoT)**。禁止在前端手动定义 API 交互模型。

---

1. 统一响应包 (Unified Response Envelope)

为了消除前后端处理逻辑的歧义，所有 API（无论成功还是失败）必须返回相同的顶级结构：

```typescript
interface UnifiedResponse<T = any> {
  success: boolean;       // 永远存在。true 表示业务成功，false 表示业务失败
  data?: T;               // 仅在 success: true 时存在
  message: string;        // 描述信息。成功时为 "OK"，失败时为错误描述
  error_code?: string;    // 仅在 success: false 时存在。大写蛇形，如 "NOT_FOUND"
  detail?: any;           // 额外元数据（如校验失败的字段明细）
}
```

### 1.1 成功示例
```json
{
  "success": true,
  "data": { "id": "123" },
  "message": "OK"
}
```

### 1.2 失败示例
```json
{
  "success": false,
  "message": "User not found",
  "error_code": "NOT_FOUND",
  "detail": { "user_id": "999" }
}
```

---

## 2. 字段生命周期治理 (Field Lifecycle)

### 2.1 命名规约
*   **后端 (Python/Pydantic)**: 使用 `snake_case`。
*   **传输层 (JSON)**: 保持 `snake_case` (Axios 拦截器处理转换 or 维持原样，需全站一致)。
*   **前端 (TypeScript)**: 对应的 interface 属性需与 JSON 保持一致 (建议全站统一使用 `snake_case` 以减少由于转译引起的认知负荷)。

### 2.2 魔数与枚举治理 (Literal Governance)
所有的状态字段（Status, Type, Category）必须在 `backend/app/common/protocol.py` 中定义为 `Literal` 或 `Enum`。
**严禁**在代码中直接使用 `"success"` 或 `"Success"` 等硬编码字符串。

---

## 3. 类型同步流水线 (Synchronization Pipeline) ✅ 已落地

为确保“契约不完善”的问题不再发生，已建立以下强制同步机制：

1.  **后端驱动**: 任何 API 的字段变更必须先在 Pydantic Model 中完成。
2.  **生成 OpenAPI**: 运行 `backend/scripts/export_openapi.py`。
3.  **前端消费**: 运行 `npm run sync-api` (执行 `frontend/scripts/sync-api.ps1`)。
4.  **架构引用**: 前端业务代码 **只能** 引用 `frontend/src/types/api.generated.ts` 中的类型。

---

## 4. 存量代码治理计划 (Backlog)

1.  [x] **响应结构统一化**: `ApiResponse` 与 `AppError` 均已回归 `success: boolean` 的大一统协议。
2.  [x] **Health API 规范化**: `health.py` 已接入标准响应模型。
3.  [ ] **全站类型收割**: 逐步移除前端 `agentApi.ts` 中手写的 interface，改为从 `api.generated.ts` 引入。
4.  [ ] **契约测试**: 建立 CI 门禁，在 PR 合并前自动对比 `docs/api/openapi.json` 是否发生非预期变更。

---
*Created by Antigravity AI - System Reliability Team*
