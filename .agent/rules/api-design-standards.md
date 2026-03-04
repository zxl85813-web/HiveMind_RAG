# 🔌 API 设计与命名规范 (API Design Standards)

> **关联流程**: [`workflows/create-api.md`](../workflows/create-api.md)

API 是前后端（以及未来 Agent 之间）协作的唯一契约。所有新增的 API 端点必须严格符合本规范。

---

## 1. RESTful URL 设计原则

### 1.1 命名使用名词复数
- ✅ 对的: `GET /api/v1/users`, `POST /api/v1/knowledge-bases`
- ❌ 错的: `GET /api/v1/getUser`, `POST /api/v1/create_knowledge`

### 1.2 动作由 HTTP Method 决定
使用正确的 Method，禁止用 POST 走天下：
- `GET`: 查询/读取资源。幂等。
- `POST`: 创建新资源。
- `PUT`: 完整更新（替换整个对象）。幂等。
- `PATCH`: 局部更新（仅修改请求中的字段）。
- `DELETE`: 软删除/硬删除资源。

### 1.3 嵌套资源
用于表示明确的所属关系。例如获取指定知识库下的所有文档：
- ✅ `GET /api/v1/knowledge-bases/{kb_id}/documents`

### 1.4 非资源型操作 (动作指令)
如果某个操作实在难以抽象为资源（如"开始向量化"），可在资源后附加动词（复数名词 + 具体动词）：
- ✅ `POST /api/v1/documents/{doc_id}/vectorize`
- ✅ `POST /api/v1/search` (当作全局资源)

---

## 2. API Schema 规范 

### 2.1 命名规则
- 请求体: `{Action}{Resource}Request`，例如 `CreateUserRequest`, `UpdateDocumentRequest`
- 响应体: `{Resource}Response` 或 `{Resource}ListResponse`，例如 `UserResponse`

### 2.2 参数组织 (Path / Query / Body)
- 唯一标识（ID类）必须放在 Path: `GET /api/v1/users/{user_id}`
- 分页、排序、筛选条件必须放在 Query: `GET /api/v1/users?page=1&size=20&role=admin`
- 敏感信息或复杂结构必须放在 Body (只适用于 POST/PUT/PATCH)。

### 2.3 分页与排序
如果返回的是列表，必须封装标准的分页字典：
```json
{
  "total": 120,
  "page": 1,
  "size": 20,
  "items": [ ... ]
}
```
并且在 Query 中允许以下参数控制：
- `page` (默认 1)
- `size` (默认 20, 上限 100)
- `sort_by` (例：`created_at`)
- `desc` (默认 `true` / 常用新数据在前)

---

## 3. 标准化响应封装 (ApiResponse)

无论成功还是失败，后端返回的 HTTP JSON 结构必须是确定的（通过 `common.response` 封装）：

### ✅ 成功格式 (HTTP 200, 201)
```json
{
  "success": true,
  "code": 20000,
  "message": "Operation successful",
  "data": { "id": "uuid..." }
}
```

### ❌ 失败格式 (HTTP 4xx, 5xx)
```json
{
  "success": false,
  "code": 40015,
  "message": "Quota exceeded or validation failed",
  "data": null,
  "error_details": { // 仅针对 422 验证错误等提供明细
     "field": "Must be greater than 0"
  }
}
```

---

## 4. 错误码体系规划 (Error Codes)

项目禁止直接使用 HTTP StatusCode 作为唯一判断依据，而应在业务 `code` 中承载更多语义。建议规划：
- `2xxxx` 成功类
- `400xx` 客户端错误（参数校验 40001、未见认证 40002、权限不足 40003）
- `404xx` 资源不存在（文档未找到 40401，知识库未找到 40402）
- `500xx` 内部服务端异常（数据库报错 50001，三方大模型超时 50002）

> 开发 API 时，若要抛出预料之内的业务错误，直接在 Service/API 层抛出对应带有具体业务 Code 的基类 Exception，由 FastAPI 的 Exception Handler 拦截并包装成上述"失败格式"。

---

> 💡 **可扩展性与规则豁免**:
> 本文档定义的是标准场景下的通用规范。如果在极其特殊的业务或性能要求下必须突破这些规则，请参见 [`design-and-implementation-methodology.md`](design-and-implementation-methodology.md) 中的"特例豁免机制"（例如强制要求在代码中写明注释或生成 ADR）。
