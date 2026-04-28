---
description: 前端开发规范 — 编辑 TSX/TS 文件时自动加载
inclusion: fileMatch
fileMatchPattern: "**/*.{tsx,ts}"
---

# 前端开发规范 (React / TypeScript)

编辑前端代码时，必须遵守以下规范。

## 前端组件设计规范
#[[file:.agent/rules/frontend-component-standards.md]]

## 前端设计系统
#[[file:.agent/rules/frontend-design-system.md]]

## 组件清单（复用优先）
#[[file:.agent/rules/component-inventory.md]]

## 速记要点

### 组件拆分规则
- Smart (Page/Container): 调用 API/Hooks，管理状态
- Dumb (View/Component): 纯 props 驱动，同 props 同 UI
- 超过 100 行 / 含 `.map()` / 局部状态 / 多处复用 → 必须抽组件

### 状态管理决策树
1. 能从现有状态推导？→ 不建 state，直接计算
2. 只在本组件用？→ `useState`
3. 服务端数据缓存？→ `@tanstack/react-query`
4. 跨页面全局 UI 状态？→ Zustand store

### 主题治理
- 颜色只能用 AntD token 或 `--hm-*` CSS 变量
- 禁止硬编码十六进制色值（`App.tsx` 和 `variables.css` 除外）
- 新组件必须在 dark/light 主题下验证可读性

### TypeScript 严格模式
- 禁止 `any`，用 `unknown` + 类型收窄
- 禁止 `enum`，用 `as const` 常量对象
- Props 必须用 `interface` + JSDoc 注释
- 使用具名导出，少用 `export default`
