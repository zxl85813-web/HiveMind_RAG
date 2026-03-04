# 🧩 前端组件设计规范 (Frontend Component Design Standards)

> 关联文档: [`.agent/rules/frontend-design-system.md`](frontend-design-system.md) (整体设计系统), [`.agent/workflows/create-component.md`](../workflows/create-component.md) (生成流程)

在复杂的 AI 协同平台（React + TypeScript）中，组件的原子化和可重用性至关重要。

---

## 1. 组件树拆分解耦原则

### 1.1 聪明组件 (Smart) vs 愚蠢组件 (Dumb)
- **Container / Page (Smart)**: 
  - *命名*: 必须带 `Page` (作为路由入口) 或 `Container`。
  - *职责*: 调用 API/Hooks (`useXxx`) 请求数据，管理全局状态，处理复杂的副作用。
  - *禁止*: 编写大量原生 HTML / CSS（应下放到子组件）。
- **View / Component (Dumb)**:
  - *命名*: 尽量使用名词 (`ChatBubble`, `DocumentCard`, `StatusTag`)。
  - *职责*: 完全由 `props` 驱动。同样的 props 必须渲染出同样的 UI。(Pure Component)。
  - *禁止*: 在内部自己做 `useEffect(() => fetch(...))`，除非它是专门封装的带数据获取逻辑的高级通用组件 (如 `UserAvatarFetcher`)。

### 1.2 何时必须抽出新组件？
一段 JSX 只要**符合以下任一条件**，必须抽离为独立组件：
1. 超过了 100 行。
2. 包含一个需要被循环映射的项（如 `.map(item => <Row... >)`）。
3. 状态是完全局部的（如图表中的 tooltip 浮层）。
4. 在超过一处的不同页面都会用到。

---

## 2. API 参数 (Props) 设计规范

### 2.1 强制 TypeScript
Props 必须使用 `interface`，并加上 JSDoc 注释。如果该组件会被通用，注释会作为悬浮提示！

```tsx
interface UserProfileProps {
  /** 用户的唯一标识符 */
  userId: string;
  /**
   * 是否高亮显示其为 VIP
   * @default false
   */
  isVip?: boolean;
  /**
   * 点击关注按钮的回调
   * 如果不传，则不渲染按钮
   */
  onFollowClick?: (userId: string) => void;
}
```

### 2.2 命名与受控 (Controlled) 制约
涉及可变状态如 `value` 的组件，原则上**必须受控**。
提供 `value` 必须同时提供 `onChange(newValue)`：

```tsx
// ✅ 好的命名约定
interface SearchInputProps {
  value: string;
  onChange: (val: string) => void;
  onSubmit?: () => void;
}
```

---

## 3. 状态管理决策树 (State Management)

当面对新状态时，**从上到下**依次判断：

1. **可以从现存状态推导出来吗？** 👉 如果能，不要新建 state，直接在 render 函数计算 (或包一层 `useMemo`，若逻辑特别重)。
2. **状态只被这一个组件及其后代所需吗？** 👉 是的话用 `useState`。需要跨越 3 层以上传递才可考虑 `Context`。
3. **状态是远程服务器数据的缓存吗？** 👉 是的话，使用数据获取 Hook (本项目一般用自定义 `useRequest` 或直接 `useEffect` 但通过 Redux/Zustand 持久化，理想状态采用 `React Query` 或 `SWR` 思想)。
4. *都不属于*，它是一个客户端全局跨界面的 UI 交互状态（如"侧边栏是否展开"、"当前正在思考的全局 Agent 进度"） 👉 使用全局状态管理器 (Zustand)。

---

## 4. 样式复用与隔离

- **CSS Modules 优先**: 永远在同一个文件旁加同名的 `<ComponentName>.module.css`。这样类名会自动加 Hash 避免冲突。
- **动态类名**: 组合类名时使用数组 `['cls1', isTrue && 'cls2'].filter(Boolean).join(' ')` 或引入 `clsx`。
- **强制 Design Token**: 禁止写死 `#f0f0f0`，必须用全局样式表中定义好的 `var(--ant-color-border-secondary)` 或我们在 `AppLayout` 中覆写的 `variables.css`。

---

## 5. 通用组件汇报机制 (Component Tracker)

在 `DES-NNN` (设计阶段) 和编码阶段：
1. **优先复用**: 先查找 `components/common/` 目录以及浏览 [`.agent/rules/component-inventory.md`](component-inventory.md) 看看是否已经造过相同的轮子。
2. **需要但没有**: 停下！去项目的 `TODO.md` 追加一条记录：
   `- [ ] 🔧 COMPONENT_NEEDED: [组件名] - [组件简要描述用途]`
   并询问设计方/PO 是否应该把它做到 `common/` 里供大家复用。
