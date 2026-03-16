# 🧬 HiveMind 设计准则 (Design Principles)

作为 HiveMind 系统的架构师，在编写 DES-NNN 文档时必须遵守以下核心准则：

##1. 四层架构契约 (4-Tier Contract)
- **Persistence Layer**: 所有模型必须继承自 `BaseModel`，并位于 `backend/app/models/`。必须考虑数据库迁移 (Alembic)。
- **Service Layer**: 业务逻辑的唯一归宿。禁止在 API Route 中编写业务逻辑。
- **API Layer**: 仅负责请求校验、认证和响应包装。必须遵循 `ApiResponse` 统一结构。
- **Frontend Layer**: 严格区分 Smart (Container) 和 Dumb (UI) 组件。优先使用 `components/common/` 中的标准原子组件。

## 2. 避免循环依赖 (No Circular Deps)
- 模块设计必须是单向依赖：API -> Service -> Model。
- Service 之间如果存在循环调用，必须重构出第三个 Service 进行解断。

## 3. 错误预定义 (Exception Specification)
- 严禁使用通用的 `Exception`。
- 每个新功能模块必须定义自己的异常类，并注册到全局错误处理器中。

## 4. 复用性优先 (DRY)
- 在设计 API 之前，先检查 `services/retrieval` 或 `services/rag_gateway` 是否已有类似能力。
- 在设计前端组件前，必须 `grep` 现有组件库。

## 5. 安全性 (Security by Design)
- 敏感字段（如密码、秘钥）必须在 Pydantic 模型中标记为 `exclude=True`。
- 所有 API 必须显式声明所需的 `AuthorizationContext`。
