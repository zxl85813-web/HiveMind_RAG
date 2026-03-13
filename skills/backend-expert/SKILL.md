---
name: backend-expert
description: "标准化生成符合项目五层流水线架构的后端代码。当涉及创建 API 端点、定义 Pydantic Schema、实现 Service 业务逻辑或编写后端集成测试时必须使用。确保代码严格遵循：UUID4 ID 策略、全局软删除、loguru 日志规范、以及 FastAPI Depends 依赖注入。不要生成与项目架构冲突的单体文件。"
---

# Backend Expert Skill

该 Skill 旨在将业务需求转化为遵循项目[后端设计规范](file:///c:/Users/linkage/Desktop/aiproject/.agent/rules/backend-design-standards.md)的高质量生产代码。

## 1. 核心流水线 (Code Generation Pipeline)

当你创建一个新功能时，必须按以下顺序生成/修改代码：

### 第一步：Schema 定义 (`backend/app/schemas/`)
- **原则**：区分 `Request`(输入) 和 `Response`(输出)。
- **命名**：`XxxCreateRequest`, `XxxUpdateRequest`, `XxxResponse`。
- **规范**：所有 Response 必须继承自基础模型，并包含 `id: UUID`, `created_at`, `updated_at`。

### 第二步：Service 实现 (`backend/app/services/`)
- **动词规范**：方法名必须以 `get_`, `list_`, `create_`, `update_`, `remove_` 开头。
- **依赖处理**：必须在 `__init__` 中注入依赖，方法内部必须接受 `AsyncSession`。
- **审计**：`create/update` 方法必须显式接受 `user_id` 并赋值给 `created_by/updated_by`。
- **事务**：底层方法只做 `flush`，顶层编排方法负责 `commit`。

### 第三步：Route 挂载 (`backend/app/api/routes/`)
- **职责**：仅负责参数解析、权限校验和调 Service。
- **注入**：使用 `Depends(get_xxx_service)` 获取 Service 实例。
- **返回**：所有返回必须包装在 `ApiResponse.success(data=...)` 中。

### 第四步：前端同步
- 运行同步脚本，将 Pydantic 模型转换为前端 TypeScript 类型（详见“自动化脚本”部分）。

## 2. 强制技术约束 (Hard Constraints)

- **ID 策略**：全表统一使用 `UUID4` (Python 层生成)，禁止使用自增 Int。
- **软删除**：核心表必须查询 `is_deleted=False`，删除操作调用 `remove_`（逻辑删除）。
- **日志**：禁止使用 `print()`，统一使用 `loguru.logger`，Exception 必须包含 `logger.exception`。
- **配置**：通过 `from app.core.config import settings` 访问配置，禁止读取 `os.environ`。

## 3. 示例代码片段 (Patterns)

### 典型的 Service 方法
```python
async def create_document(
    self, 
    session: AsyncSession, 
    data: DocumentCreateRequest, 
    user_id: UUID
) -> Document:
    # 1. 权限与前置校验 (_check_xxx)
    await self._check_kb_access(session, user_id, data.kb_id)
    
    # 2. 模型填充
    db_obj = Document.model_validate(data)
    db_obj.id = uuid4()
    db_obj.created_by = user_id
    
    # 3. 持久化
    session.add(db_obj)
    await session.flush()
    return db_obj
```

## 4. 辅助脚本 (Helper Scripts)

- **类型同步**：运行 `python backend/scripts/sync_ts_types.py`。
- **代码脚手架**：运行 `python backend/scripts/gen_scaffold.py --name "feature_name"`。

## 5. 登记与文档
- 完成后必须提示用户更新 `REGISTRY.md`。
- 生成 `docs/reviews/` 下的自检清单。
