# ⚙️ 后端模块设计规范 (Backend Module Design Standards)

> 关联文档: [`.agent/rules/project-structure.md`](project-structure.md) (宏观目录划分)

在 FastAPI + SQLModel 体系下，如何写好一个具体的后端模块（Service、API、Util），必须遵守本微观设计规范。

---

## 1. Controller / Route 层职责

`api/routes/xxx.py` 是控制层，**绝对不允许包含复杂的业务逻辑**。

### 1.1 职责边界
- **做**: 解析参数、检查基础权限、调用 Service 方法、将返回值包装为 `ApiResponse`、抛出适当的 HTTP 状态。
- **不做**: 拼接复杂 SQL、调用外部大模型、组装复杂的数据结构。

### 1.2 依赖注入原则
强制使用 `Depends` 注入数据会话 (Session) 和业务服务 (Service)，方便未来的单元测试 Mock 替换。

```python
# ✅ 正确示范
@router.post("/", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    session: AsyncSession = Depends(get_db_session),
    user_service: UserService = Depends() # 自动注入 UserService
):
    try:
        user = await user_service.create(session, request)
        return ApiResponse.success(data=user)
    except UserAlreadyExistsError as e:
        raise AppException(code=40001, message=str(e), status_code=400)
```

---

## 2. Service 层设计模式

`services/` 是业务的核心执行层。

### 2.1 依赖与传参
- **数据库 Session**: 必须通过方法参数显式传入 (例如 `async def run(self, session: AsyncSession)` )，不要在 Service 层内部强绑定全局单例的 Session，这会导致难以 Mock 以及事务难以控制。
- **Service 聚合**: 如果 A Service 需要调用 B Service，可以通过其 `__init__` 构造函数注入，避免循环依赖 (`Circular Import`)。

### 2.2 事务控制 (Transaction boundaries)
如果一个复杂的业务方法包含多个库表写入，**谁调用，谁负责 commit()**。
- **规则**: 在底层的纯写入方法中（例如 `crud_tool.create_user()`），只做 `session.add(obj)` 和 `session.flush()`，由最外层的 Service 执行 `session.commit()`，以此保证事务原子性。

---

## 3. 异常处理 (Exception Handling)

不要在 Service 中返回 tuple 或特殊字符串来表示错误。

### 3.1 异常的层次
在 `app.core.exceptions` 下建立应用的自定义异常基类，继承自 Python 原生 `Exception`。
所有的业务错误，都要定义专属类：
```python
class DocumentTooLargeError(Exception):
    pass

class UnauthorizedKnowledgeAccessError(Exception):
    pass
```

### 3.2 向上冒泡与转换
Service 遇到错误时直接抛出上述底层类。
在 `api/routes` 层或全局 `ExceptionHandlers` 中，捕捉这些类，并将它们转换为 `AppException` 返回前端：

```python
# main.py 中的全局处理器
@app.exception_handler(DocumentTooLargeError)
async def doc_large_handler(request, exc):
    return JSONResponse(
        status_code=413,
        content={"success": false, "code": 41300, "message": "Document exceeds 50MB"}
    )
```

---

## 4. 日志记录原则 (Logging)

统一使用 `loguru.logger`，绝对禁止使用 `print()` 或原生的 `logging`。
- **INFO**: 重要业务节点（"启动索引 Task 100", "用户注销"）。
- **WARNING**: 可恢复的异常，如调用外部 API 超时但成功重试。
- **ERROR**: 拦截到未处理的 Exception，必须带上 `logger.exception()` 来输出完整的 Traceback。
- **DEBUG**: 进入函数打印参数、SQL 语句片段。

---

## 5. 设计文档 (DES-NNN) 编写强制项
在书写某个需求的设计文档时，如果涉及到后端改造，必须明确写出：
1. **依赖关系图** (将要添加的 Service 会实例化哪些现有的组件/客户端？)
2. **将抛出的主要异常清单**。
