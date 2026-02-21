---
description: 创建新的后端 API 端点的标准流程
---

# 🔌 创建后端 API 端点流程

## 前置检查

### 1. 查 REGISTRY.md API 列表
// turbo
```bash
cat REGISTRY.md
```
确认没有重复端点。

### 2. 确认归属路由文件
API 端点必须在 `backend/app/api/routes/` 下已有文件中添加:
- `chat.py` — 对话相关
- `knowledge.py` — 知识库管理
- `agents.py` — Agent 管理
- `websocket.py` — WebSocket
- `learning.py` — 外部学习
- `health.py` — 健康检查

**如需新路由文件**，必须先讨论并更新 project-structure.md。

## 创建步骤

### 3. 定义 Schema (schemas/)
```python
# schemas/xxx.py
"""
{领域} API 请求/响应 Schema。
参见: REGISTRY.md > 后端 > Schema > {名称}
"""

class XxxRequest(BaseModel):
    """请求体。"""
    field: str = Field(..., description="字段说明")

class XxxResponse(BaseModel):
    """响应体。"""
    id: str
    # ...
```

### 4. 实现 Service 层 (services/)
```python
# services/xxx_service.py
"""
{领域} 业务逻辑。
参见: REGISTRY.md > 后端 > Service > {名称}
"""

class XxxService:
    async def create(self, data: XxxRequest) -> XxxResponse:
        # 业务逻辑在这里
        pass
```

### 5. 添加路由 (api/routes/)
```python
@router.post("/", response_model=XxxResponse)
async def create_xxx(
    request: XxxRequest,
    service: XxxService = Depends(get_xxx_service),
):
    """
    创建 XXX。
    
    参见: REGISTRY.md > 后端 > API > POST /api/v1/xxx
    """
    return await service.create(request)
```

### 6. 更新 shared/types.ts
同步添加 TypeScript 类型定义。

### 7. 更新前端 services/
添加对应的 API 调用函数。

### 8. 更新 REGISTRY.md
登记新的 API、Schema、Service。
