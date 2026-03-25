# 🏗️ DES-001: HiveMind Web 前端架构设计说明书

> **状态**: Active | **版本**: 2.0 (整合版)  
> **单一事实源**: 本文档替代了原有的 `frontend_architecture.md`, `frontend_architecture_guidelines.md` 和 `ai-first-frontend.md`。

---

## 🧭 1. 核心设计哲学 (Core Philosophies)

### 1.1 AI-First 理念
**Chat 不是一个辅助组件，而是应用的中枢神经。**
*   **传统 SaaS**: 用户通过菜单 → 找到页面 → 手动操作。
*   **AI-First**: 用户通过对话 → AI 理解意图 → 自动导航/执行/展示。
*   **布局逻辑**: 窗口设计需时刻支持“传统功能区”与“沉浸式 AI 对话”的无缝切换。

### 1.2 赛博精致 (Cyber-Refined) 美学
*   **视觉规范**: 建立层次分明的暗色玻璃态 (Glassmorphism)，使用强烈的品牌青色/蓝色点缀。
*   **主题治理**: 严禁在业务组件中硬编码十六进制色值，必须使用 `@/styles/variables.css` 中的 CSS 变量。

---

## 📐 2. 布局架构 (Layout Architecture)

前端采用 **"Shell + Content"** 架构，并支持 **双轨模式 (Dual-Mode)**。

### 2.1 双轨模式切换
1.  **传统模式 (Classic View)**: 左侧导航栏 + 中央作业页 + 右侧常驻 ChatPanel。适用于密集型管理操作。
2.  **AI 模式 (AI-First View)**: 隐藏导航栏，右侧 ChatPanel 升维至居中全局铺满。由对话推动业务流。

### 2.2 结构图示
```mermaid
graph TD
    User([User]) -->|访问应用| Shell[App Shell (AppLayout)]
    
    subgraph "持久层 (Global)"
        Shell --> Header[Header / TopBar]
        Shell --> SideNav[侧边导航]
        Shell --> ChatPanel[🤖 Chat Panel (AI Copilot)]
        Shell --> WebSocket[WebSocket Client]
    end
    
    subgraph "内容层 (Routed Outlet)"
        Shell --> Outlet[React Router Outlet]
        Outlet --> Dashboard[/]
        Outlet --> Knowledge[/knowledge]
        Outlet --> Agents[/agents]
    end
```

---

## 🗃️ 3. 状态管理策略 (State Strategy)

采用 **二元治理 (Dual Governance)**，严禁服务端状态与客户端状态混淆。

| 状态类型 | 工具 | 管辖范围 | 示例 |
| :--- | :--- | :--- | :--- |
| **Server State** | `TanStack Query` | 后端 API 数据、缓存、SWR、自动重试 | 知识库列表、文档详情 |
| **Client State** | `Zustand` | 跨组件 UI 交互、全局 AI 会话状态 | `isChatOpen`, `themeMode` |
| **Local State** | `React.useState` | 组件内部闭环逻辑 | 输入框内容、Loading 标识 |
| **Form State** | `AntD Form` | 复杂表单校验与收集 | 知识库创建表单 |

---

## 🌐 4. 网络与通信 (Network & LLM Layer)

### 4.1 网络拦截
*   **唯一通道**: 统一在 `services/api.ts` 配置 Axios 实例。
*   **错误守卫**: 任何 4xx/5xx 异常必须通过拦截器触发全局 `message/notification` 反馈，禁止闷声失败。

### 4.2 AI 交互标准 (Ant Design X)
*   **禁止手写**: 严禁手动处理 SSE 解析、AborkController 或正则表达式拆解指令。
*   **全量 SDK**: 必须使用 `@ant-design/x` 的 `useXAgent` 和 `useXChat` 协议套件。

---

## ⚡ 5. AI Action 指令系统

AI 的回答不仅是文本，更可包含结构化指令（X-Skill）：

```typescript
type AIActionType = 
  | 'navigate'       // 导航 (路径跳转)
  | 'open_modal'     // 打开模态框 (如创建知识库)
  | 'highlight'      // 高亮页面元素 (引导操作)
  | 'execute'        // 后台任务执行
  | 'suggest'        // 推荐卡片

interface AIAction {
  type: AIActionType;
  label: string;
  target: string;
  params?: Record<string, unknown>;
}
```

---

## ⚙️ 6. 工程化红线 (Engineering Specs)

1.  **代码分割**: 所有路由入口必须使用 `React.lazy()` 异步加载，严禁同步引用大页面减少 TTI。
2.  **错误边界**: 必须在 `main.tsx` 及 AI 生成内容的特定组件外层包裹 `<ErrorBoundary>`。
3.  **类型闭环**: 新增组件前必须先定义 `types/` 接口，执行 `npm run typecheck` 检查。
4.  **样式隔离**: 优先使用 `*.module.css`，禁止内联高内聚 Style。

---

## 📂 7. 目录结构规范

```bash
frontend/src/
├── components/
│   ├── common/         # AppLayout, Footer
│   ├── chat/           # ChatPanel, Bubble (AI 核心)
│   └── canvas/         # AntV G6/X6 可视化组件
├── core/               # 🆕 智能中枢层 (Architecture Heart)
│   ├── MonitorService  # 遥测与健壮性治理
│   ├── IntentManager   # 预测性预取引擎
│   └── LocalEdgeEngine # IndexedDB 本地持久化
├── pages/              # 路由页面 (必须 React.lazy)
├── stores/             # Zustand (Client State)
├── services/           # Axios (Server State 获取入口)
├── styles/             # CSS Variables & Global CSS
└── App.tsx             # 路由分发与 ErrorBoundary
```

---

## 🛰️ 8. 核心智能层 (Core Intelligent Layer)

为了支撑 Phase 4 的高性能与零延迟体验，应用引入了独立于 UI 的 **Core 层**。

### 8.1 预测性预取 (Predictive Prefetching)
*   **机制**: `IntentManager` 监听高频交互信号（Hover, Focus, Input）。
*   **策略**: 识别到意图后停留 >150ms 自动触发 `TanStack Query` 的 `prefetchQuery`。
*   **对齐状态**: 
    *   ✅ 已在 `ChatPanel` 历史列表实现。
    *   ⬜ 计划在侧边栏导航 (SideNav) 实现。

### 8.2 遥测健壮性 (Telemetry Resilience)
*   **双重保障**: `MonitorService` 封装了 `fetch(keepalive: true)` 与 `navigator.sendBeacon` 的双重降级逻辑。
*   **场景**: 确保页面暴力关闭时的 HMER 指标对账完整性。

### 8.3 本地边缘引擎 (Local Edge)
*   **存储**: 基于 IndexedDB 实现。
*   **定位**: 非实时数据的二级缓存，实现秒开体验。
```

---
> _“让每一行代码都有据可查，让每一处设计都服务于智能。”_
