# 🏗️ HiveMind 前端架构与开发主旨白皮书 (Frontend Architecture Guidelines)

> **状态**: Active  
> **版本**: 2.0 (AI-First 与工程化重构对齐版)  

本白皮书旨在为 HiveMind 的前端开发提供**不可妥协的设计红线**和**最佳工程实践指南**。所有前端开发者（包括参与开发的 AI 智能体）在编写代码、设计组件和处理数据流时，必须严格遵守以下规范。

---

## 🧭 0. 核心开发主旨 (Core Philosophies)

1. **AI-First 理念，而非 "AI-Added"**
   * AI 不是悬浮在页面角落的一个挂件，而是系统的心智引擎。布局需时刻支持“传统面板功能”与“沉浸式 AI 对话”的双流切换。
2. **极简且精确的美学诉求 (Cyber-Refined)**
   * 我们推崇**赛博精致**。摒弃“大白底+圆角”的通用硅谷风，建立层次分明的暗色玻璃态 (Glassmorphism) 与强烈的品牌青色/蓝色点缀。（详见 `frontend-design` Skill）。
3. **领域分层，职责分明**
   * 组件库各司其职（基础 UI 交给 Ant Design，智能交互交给 Ant Design X），状态管理分级控制，坚决抵制大杂烩式（Spaghetti）的代码交织。

---

## 📐 1. 结构与生命周期架构 (Layout & Lifecycle)

### 1.1 双轨模式视窗 (Dual-Mode View)
应用布局 (AppLayout) 天然分叉为两种心智模式，两者通过顶级 Store 进行无缝切换：
* **传统模式 (Classic View)**：左侧导航栏 + 大面积中央作业区（路由出口） + 分栏常驻的右侧 ChatPanel 助手。
* **AI 模式 (AI-First View)**：隐藏左侧导航栏，右侧 ChatPanel “升维”至居中全局铺满，由大模型对话推动整个业务流。

### 1.2 性能生命线：代码分割 (Code Splitting)
对于所有路由级页面入口（如 `DashboardPage`、`KnowledgePage` 等大体量页面），**严禁在 `App.tsx` 中直接同步引用**。
* **规则**：必须通过 `React.lazy()` 进行异步加载，并在路由分发口 (`<Routes>`) 外部包裹带 Loading 动画的 `<Suspense>` 组件。减少系统的首屏初始化耗时 (TTI)。

### 1.3 维稳底线：错误边界 (Error Boundaries)
* **规则**：必须在根组件（`main.tsx` 或 `App.tsx`）及特定的重量级路由（如由 AI 生成的卡片、图谱分析组件）外层包裹 `<ErrorBoundary>`。
* **目的**：隔离局部 React 渲染崩溃引发的**全局白屏**，允许向用户提供优雅降级的错误提示及重置功能。

---

## 🗃️ 2. 数据流与状态架构 (State Management Flow)

我们对前端的状态实施**二元治理（Dual Governance）**，严格禁止客户端状态和请求状态混为一谈。

### 2.1 业务服务端状态 (Server State) —— `@tanstack/react-query`
* **管辖范围**：所有与后台 API 对接的拉取请求、带缓存机制的数据流、增删改查刷新等。
* **实践**：在业务逻辑里通过自定义 hooks（如 `useKnowledgeBases()`）暴露通过 `useQuery` / `useMutation` 注册的底层动作。Zustand *不得存储* 需要由 React-Query 掌管的远端数据集。

### 2.2 UI 客户端状态 (Client State) —— `zustand`
* **管辖范围**：跨无关联组件的纯前端交互状态，如：主题切换模式 (AI / Classic)、当前全局拦截错误提示词状态、侧边抽屉宽度等。
* **实践**：精简粒度，尽可能利用 Component Local State (`useState`)，只把不得不穿透多个组件层级的 UI 标记送入 Zustand。

---

## 🌐 3. 网络与大模型通信 (Network & LLM Layer)

### 3.1 强管控边界的 Axios
**严禁使用原生 `fetch` 与手写无拦截器的 `axios`。**
在 `services/api.ts` 中维护唯一的前端网络通道：
1. **全局错误拦截**：网络层级直接对接 Ant Design `message`/`notification`。任何如 401（Token 失效）、403、500 异常必须有弹窗反馈（Toast），决不可闷声失败。
2. **纯净的 Mock 环境区隔**：Mock 数据拦截逻辑须在 Vite 构建层面通过 `main.tsx` 入口分离，保持向线上构建时 `api.ts` 的轻量无污染。

### 3.2 大模型交互的标准封装 (Ant Design X 原生化)
* **抛弃手工作坊**：停止用手动 `AborkController`、自建 `messages` 数组和正规表达式 (`[ACTION:...]`) 去拦截并解析 SSE (Server-Sent Events) 数据流中的意图。
* **全量倒向 X SDK**：必须引入 `@ant-design/x` 的原生方案（`useXAgent`, `useXChat`, `XRequest`），把底层协议处理移交给专业框架，开发精力专注于卡词、UI、拦截。

---

## 🧩 4. 组件与技能生态 (Component & Skill Ecosystem)

基于我们在 `.cursorrules` 中敲定的法则，前端所有的组件树和挂件开发，必须从以下三种生态中获取正确的对应层级：

| 领域 / 来源 | 适用场景与职责 | 开发红线与审查卡点 |
| :--- | :--- | :--- |
| **基础积木**<br>(Ant Design) | 表格(Table)、表单(Form)、空状态(Empty)、布局(Flex) 等结构性容器。 | 不准自己手敲大片原生 `<button>`,`<input>`,`<table>`。 |
| **赛博皮相**<br>(Frontend Design Skill) | 给所有组件上色、设定排版、质感。添加深色质感、模糊背景、动画微交互。 | 必须使用 `.module.css` 和全局 CSS 变量。严禁内联高内聚的 `style={{...}}` 以及随意手写颜色十六进制代码。 |
| **神经元交互**<br>(Ant Design X & X-Skills)| 一切处于对话窗口 (ChatPanel) 的消息气泡、输入框、指令与卡片 (卡片内容为 LLM 执行产生)。 | 严禁通过正则表达式在聊天流中截取字符串渲染图腾组件。必须将其视为大模型的工具回传，包装为标准 X-Skill。 |

---

## ⚙️ 5. 目录与工程规范 (Engineering Specs)

```text
frontend/src/
 ├── assets/      # 静态图库、字体文件
 ├── components/  # 组件库区域 (严格按领域划分，如 /common, /chat, /agents)
 ├── hooks/       # React Custom Hooks
 ├── pages/       # 顶级路由页面容器 (必须在此通过 React.lazy 按需加载)
 ├── services/    # 纯函数层，负责所有的 Axios 请求配置 (如 chatApi.ts)
 ├── stores/      # 仅限 Zustand 的 Client State
 ├── styles/      # 核心 Design Tokens, css var, mixin (如 mixins.module.css)
 ├── types/       # 全局 TypeScript 基础接口类型宣告
 └── App.tsx      # 全局主入口，承担 ErrorBoundary 与 Router 防护职责
```

**自省清单 (Self-Check List before PR)**:
1. 你的组件是否把复杂的网络错误咽下去了没有报 Toast？
2. 你新加的大页面是否忘了在 router 中配置 React.lazy 造成了 JS 包体积膨胀？
3. 对于带有 AI 意图反馈的卡片组件，你是否按 X-Skill 标准开发？样式是否使用了 CSS 变量？
4. 文件改动后，你是否在终端运行过 `npm run typecheck`（类型严格校验）？

---

> _“好架构的诞生，始于对一切可能走向混沌的代码的坚决说不。”_
