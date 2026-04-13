# ⚛️ HiveMind 前端工程规范 (Frontend Standards)

> **修订版本**: V1.1 (2026-04-12)  
> **适用范围**: React 19 / TypeScript 5 / Vite / Ant Design X

---

## 1. 类型治理原则 (Type Governance)

### 1.1 零手动 Interface (ZMI)
- 所有的 API 数据结构 **严禁** 在前端手动定义 `interface` 或 `type`。
- 必须运行 `npm run sync-api` 从后端的 OpenAPI 定义自动生成 `api.generated.ts`。
- 业务代码应从生成的 `components["schemas"]` 中提取类型。

### 1.2 严格 Null 检查
- 必须处理 `undefined` 和 `null` 的情况。在调用层使用 Optional Chaining 或 Nullish Coalescing。

## 2. 组件与架构 (Architecture)

### 2.1 容器/展示模式 (Container/Presenter)
- **Pages**: 负责从 Hook 中获取数据，控制展示逻辑。
- **Components**: 应当是纯粹的（Pure Components）或高可复用的受控组件。
- **Core**: 所有的基础设施（AuthRep, Monitor, IntentManager）应放在 `src/core` 下。

### 2.2 状态管理
- **Server State**: 使用 `@tanstack/react-query`。禁止在 useEffect 中手动管理 fetch 状态。
- **Global State**: 使用 `Zustand`。保持 Store 扁平且聚焦。

## 3. UI/UX 治理 (AI Frontend Strategy)

- **流式响应**: 对话界面必须使用 `SSE` 流式渲染，并提供打字机效果。
- **降级处理**: RAG 检索失败时，组件应通过 `ErrorBoundary` 捕获并显示“自愈”提示。
- **反馈闭环**: 所有的 AI 生成内容必须附带 Feedback (点赞/点踩) 入口。

## 4. 性能与安全性

- **渲染优化**: 避免在 Map 循环中使用 index 作为 key，使用唯一 ID。
- **SourceMap 保护**: 生产环境构建后，`scripts/post-build.js` 必须自动移除并归档 `.map` 文件。

---
*Created by Antigravity AI - Engineering Governance Team*
