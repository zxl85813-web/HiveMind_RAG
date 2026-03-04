---
description: 编码规范 — 代码风格、命名、注释、一致性要求
---

# 📐 编码规范

## 1. 注释要求

### Python (后端)
```python
"""
模块级 docstring — 说明此文件的职责和位置。

所属模块: agents
依赖模块: core.config, services.ws_manager
注册位置: REGISTRY.md > Agent 模块 > SwarmOrchestrator
"""

class SwarmOrchestrator:
    """
    Agent 蜂巢编排器。
    
    职责:
    - 注册和管理 Agent
    - 构建 LangGraph 执行图
    - 路由用户请求到合适的 Agent
    
    使用方式:
        orchestrator = SwarmOrchestrator()
        orchestrator.register_agent(rag_agent)
        result = await orchestrator.invoke("用户问题")
    
    参见: REGISTRY.md > 后端 > agents > SwarmOrchestrator
    """

    async def invoke(self, user_message: str, context: dict | None = None):
        """
        处理用户请求。
        
        Args:
            user_message: 用户输入文本
            context: 上下文信息 (conversation_id, kb_ids 等)
            
        Returns:
            AsyncGenerator[str, None]: 流式响应 token
            
        Raises:
            AgentRoutingError: 当无法确定路由目标时
        """
```

### TypeScript (前端)
```typescript
/**
 * 对话消息气泡组件。
 * 
 * 基于 Ant Design X 的 Bubble 组件封装。
 * 
 * @module components/chat
 * @see REGISTRY.md > 前端 > 组件 > ChatBubble
 * 
 * @example
 * <ChatBubble message={msg} onRetry={handleRetry} />
 */
```

## 2. 一致性规则

### 后端一致性
| 场景 | 必须使用 | 禁止使用 |
|------|---------|---------|
| 配置管理 | `app.core.config.settings` | 硬编码、os.environ |
| 日志 | `loguru.logger` | print(), logging 标准库 |
| HTTP 客户端 | `httpx` (async) | requests, urllib |
| 数据验证 | Pydantic BaseModel / SQLModel | raw dict |
| 数据库操作 | SQLModel + async session | 原生 SQL (除 SQL Agent) |
| 依赖注入 | FastAPI Depends() | 全局变量 |
| 时间处理 | `datetime.now(timezone.utc)` | `datetime.now()`, `datetime.utcnow()` |
| ID 生成 | `uuid.uuid4()` | 自增 ID, 随机字符串 |

### 前端一致性
| 场景 | 必须使用 | 禁止使用 |
|------|---------|---------|
| UI 组件 | Ant Design / Ant Design X | 自制基础组件 (Button, Input 等) |
| 样式 | CSS Modules + Design Tokens | 内联 style, 全局 CSS 类名冲突 |
| 状态管理 | Zustand store | useState 管理跨组件状态, Redux |
| 服务端数据 | @tanstack/react-query | 手动 useEffect + fetch |
| HTTP 请求 | services/ 层的封装函数 | 组件内直接 axios/fetch |
| 路由 | react-router-dom v6 | window.location |
| 图标 | @ant-design/icons | 其他图标库, 内联 SVG |
| 颜色/间距 | Design Token 变量 | 硬编码 px / 色值 |

## 3. 命名规范

### 文件命名
```
# 后端 Python — snake_case
agents/swarm.py
api/routes/chat.py
schemas/chat.py

# 前端 TypeScript — PascalCase (组件), camelCase (其他)
components/chat/ChatBubble.tsx
hooks/useChat.ts
stores/chatStore.ts
services/chatApi.ts
utils/formatDate.ts
```

### 变量命名
```python
# Python — snake_case
user_message = "hello"
async def get_agent_status():

# TypeScript — camelCase, 组件 PascalCase
const userMessage = "hello";
const ChatBubble: React.FC = () => {};
```

## 4. 错误处理

### 后端
```python
# ✅ 正确: 使用统一异常类
from app.core.exceptions import NotFoundError, ValidationError

raise NotFoundError(resource="knowledge_base", id=kb_id)

# ❌ 错误: 直接抛 HTTPException（应在异常处理器中统一转换）
raise HTTPException(status_code=404, detail="...")
```

### 前端
```typescript
// ✅ 正确: 使用 react-query 的错误处理 + 统一 toast
const { error } = useQuery({ queryKey: ['chat'], queryFn: fetchChats });
if (error) return <ErrorDisplay error={error} />;

// ❌ 错误: try-catch 后 console.error 静默吞掉
```

## 5. 前后端对接与集成规范 (Integration Rules)

端到端测试中必须遵守以下规则，以避免全栈对接时的崩溃和阻塞：

### 5.1 数据格式契约 (Data Format Contract)
* **后端响应必须统一**：所有 FastAPI 的业务路由必须使用 `app.common.response.ApiResponse.ok(data=...)` 或 `ApiResponse.error(...)` 来包装返回值。
* **禁止裸露数据**：绝对禁止直接返回 List、Dict 或原始 ORM 模型给前端（会导致前端解析时出现 `Property 'data' does not exist on type '...'` 的报错）。
* **前端解析标准**：前端在使用 Axios (或其他 HTTP 库) 接收响应时，必须提取有效负载。如果是标准 Axios 包裹的 `ApiResponse`，提取逻辑为 `res.data.data`。

### 5.2 跨域与网络配置 (CORS & Networking)
* **环境显式配置**：在增删前端测试端口或部署地址时，**必须**同步更新后端 `.env` 文件中的 `CORS_ORIGINS` 和 `BACKEND_CORS_ORIGINS`，明确包含诸如 `http://localhost:5173` 或 `http://127.0.0.1:5173` 等地址。
* **检查中间件**：后端需要有一个全局生效的 `CORSMiddleware` 注册在 `FastAPI` 实例上，禁止在子 Router 内部重复或遗漏配置跨域规则。

### 5.3 鉴权降级与隔离 (Auth Downgrade for Debugging)
* **集成测试降级**：在不需要严格验证权限的核心业务链路贯通测试中，对于带有 `Depends(get_current_user)` 依赖的接口，应提供一个通用的 mock ID（如通过在路由或 dep 文件里设置默认 mock response），确保前端能在不携带真实 JWT Token 时顺利联调通过网络请求。
* **避免无声失败**：当发生鉴权错误（401/403）时，前后端必须给出明确的日志或提示，禁止因为一处接口 403 导致整页 Crash（React 前端需配合 ErrorBoundary 和可选链调用 `?.`）。

## 6. Python 深度编码规范 (Python Deep Standards)

### 6.1 Import 排序 (Import Sorting)
必须遵循严格的块级排序逻辑 (与 `isort` / `ruff` 默认规则一致)：
1. 标准库导入 (`import os`, `import sys`)
2. 第三方库导入 (`from fastapi import ...`, `import pydantic`)
3. 本地项目导入 (`from app.core import ...`, `from app.models import ...`)
> 块与块之间保留一个空行。

### 6.2 函数与类型提示 (Functions & Type Hints)
- **强制类型标注**: 所有函数的参数和返回值类型必须标注。
- **禁止滥用 kwargs**: 严禁毫无理由地使用 `**kwargs` 穿透传参，必须提供明确的 Schema 或具名参数，以便 IDE 提示和静态检查。
```python
# ✅ 正确
async def process_text(text: str, max_length: int = 100) -> str:

# ❌ 错误
def process_text(text, **kwargs):
```

### 6.3 类设计原则 (Class Design)
- **单一职责**: 一个类只做一件事。如果有类名变成 `XxxManagerAndHandler`，说明需要拆分。
- **组合优于继承**: 尽量使用依赖注入或组合的方式复用逻辑，避免产生超过 3 层的深层继承树。

### 6.4 异步编程边界 (Async Programming)
- **禁止在 async 中阻塞**: 在 `async def` 函数中，绝对禁止调用同步的阻塞 IO 函数（如 `requests.get`, 同步版的 `time.sleep`, 或者原生的 `open(file)`。必须使用 `httpx.AsyncClient`, `asyncio.sleep`, `aiofiles`）。

### 6.5 安全编码 (Security)
- 严禁使用 `eval()` 或 `exec()` 解析动态输入。
- 环境变量必须通过 `app.core.config.settings` 强类型获取，禁止使用 `os.environ.get()`，以防类型转换错误或由于缺失默认值导致线上崩溃。
- 使用 ORM (SQLModel) 进行所有数据库操作，防范 SQL 注入风险。

## 7. TypeScript & React 深度规范 (TS/React Deep Standards)

### 7.1 React Hooks 规范
- **穷举依赖**: `useEffect`、`useCallback`、`useMemo` 的依赖数组 (`deps`) 必须**完全穷举**所有在外部作用域声明并于内部使用的变量/函数。如果不希望触发 re-render，应该用 `useRef` 包裹而不是从依赖数组中删掉变量。
- **不要滥用 Memo**: 只有在传递给复杂子组件（且该组件被 `React.memo` 优化）或进行大量复杂计算时，才使用 `useMemo`/`useCallback`。普通计算直接写在 render 流中。

### 7.2 严格类型 (Strict Typing)
- **禁止 Any**: 全局禁止使用 `any`。遇到未知类型时使用 `unknown`，并在使用前做类型收窄 (Type Narrowing)。
- **Enum 替代方案**: TypeScript 原生 `enum` 会导致转译出的 JS 体积膨胀和双向映射的问题。建议使用常量对象 + `as const` 来代替枚举：
```typescript
// ✅ 推荐的类 Enum 写法
export const Role = {
  ADMIN: 'admin',
  USER: 'user',
} as const;
export type RoleType = typeof Role[keyof typeof Role]; // 'admin' | 'user'
```

### 7.3 国际化规范 (i18n Implementation)
- **禁止硬编码中文**: UI 上用户可见的所有中文字符串，必须提取至本地化包，并通过 `t()` 函数渲染。
- **Key 命名法**: `<Page名>.<组件块>.<词元>`，例如 `'dashboard.stats.totalUsers'` 或 `'common.button.submit'`。

### 7.4 文件与目录结构附加约束
除了第 3 节中提到的基础大小写外：
- 组件必须使用 `PascalCase` 的目录和 `index.ts` 导出模式？不，本项目默认直接使用 `Component.tsx` 为文件名，以避免 IDE tab 页里全是 `index.tsx` 的困境。
- 导出建议使用具名导出：`export const MyButton = () => ...`，少用 `export default` 以便于全局搜索和重构。
