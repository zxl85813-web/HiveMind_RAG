# 📦 前端通用组件库清单 (Component Inventory)

> 关联规范: [`.agent/rules/frontend-component-standards.md`](frontend-component-standards.md)
> 所有列在 `components/common/` 里的组件都应在此处记录，并在整个项目范围内复用。

## 1. 为什么需要通用组件？
保持 UI/UX 的一致性，避免重复写相同的 Padding、Color、Error 态、Loading 态。

---

## 2. 通用组件名录

### 📊 布局与容器 (Layout & Containers)

#### `PageContainer`
- **用途**: 每个独立大页面（如 Agents 页、设置页）的最外层容器，自带标题栏、可选的额外操作区（Extra）和标准化留白。
- **Props**: `title` (string), `extra?` (ReactNode), `children` (ReactNode)。
- **使用时机**: 创建新的顶级路由页面时，**必须**使用它包裹内容。

#### `AppLayout`
- **用途**: 根界面的壳子，包含了顶侧双导航、UserProfile 按钮以及整体背景色板设定。

---

### 🟢 状态与反馈 (Status & Feedback)

#### `LoadingState`
- **用途**: 居中显示加载动画与提示语，代替你手推的 `Spin` + 剧中 div。
- **Props**: `tip?` (string, 默认 "Loading...")
- **使用时机**: 所有需要占据大块屏幕面积的正在加载的状态（非按钮级别小 Loading）。

#### `ErrorDisplay`
- **用途**: 标准错误提示板，接管并统一格式化 Error 对象（甚至是 Axios error）。包含友好的图标和重试按钮。
- **Props**: `error` (Error | unknown), `onRetry?` (() => void)
- **使用时机**: API 连接断开、组件崩溃（配合 ErrorBoundary）、数据拉取失败时。

#### `EmptyState`
- **用途**: 当列表或详情为空时的标准防沉浸界面。
- **Props**: `image?` (string), `title` (string), `description?` (string), `action?` (ReactNode)
- **使用时机**: 知识库没有任何文档、聊天记录为空。

---

### 🏷️ 信息展示 (Data Display)

#### `StatCard`
- **用途**: 仪表盘常用的数值展示卡券。包含 title, 主 value, 趋势（trend）。
- **Props**: `title` (string), `value` (string | number), `icon?` (ReactNode), `trend?` ('up' | 'down'), `trendValue?` (string)
- **使用时机**: 渲染诸如"知识库总数"、"今日对话次数"等数据汇总卡片时。

#### `StatusTag`
- **用途**: 一种预设了多种状态颜色（成功/警报/灰）的标签（Tag）封装。
- **Props**: `status` ('success' | 'warning' | 'error' | 'default'), `text` (string)
- **使用时机**: 渲染流水线状态（Completed, Indexing, Failed）。

---

### 🎬 交互型组件 (Interactions)

#### `ConfirmAction`
- **用途**: 高危操作（如删除知识库）时的 Popconfirm 或 Modal 二次确认。它是一个高阶包装组件，可以包裹任何按钮。
- **Props**: `title` (string), `description?` (string), `onConfirm` (() => Promise<void>), `children` (ReactNode 触发器)
- **使用时机**: 只要涉及到 Delete 操作，就必须拿它来包裹删除按钮。

#### `MockControl`
- **用途**: 用于快速切换开发环境的 Mock 开关的悬浮窗（不在生产环境打包构建内出现）。

---

## 3. 当找不到想要的通用组件时怎么办？

绝对不要在 `components/<domain>/` 下私自造一个看起来很通用但只局限于某个业务的"按钮"或"标签"！

1. 在项目中打开终端，执行 `// turbo` 工作流：申请全新组件记录。
2. 按照 `request-component.md` 的规范，在 `TODO.md` 中标记：
   `- [ ] 🔧 COMPONENT_NEEDED: <组件名> - <用途>`
3. 等待后续决策，决定是由 AI Agent 原型化，还是由人类开发者手动开发并加入到 `common/` 中。

---

> ⚠️ 注意: 以上组件都在 `frontend/src/components/common/index.ts` 中集中导出。
> 别忘了引入方式是: `import { LoadingState } from '@/components/common';`
