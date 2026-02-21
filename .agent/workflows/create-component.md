---
description: 创建新的前端组件的标准流程
---

# ⚛️ 创建前端组件流程

## 前置检查

### 1. 查 REGISTRY.md 组件列表
// turbo
```bash
cat REGISTRY.md
```
确认没有相同/相似组件。

### 2. 确认组件归属目录
组件必须放到 `frontend/src/components/` 下的子目录:
- `common/` — 通用 (Layout, Sidebar, ErrorDisplay)
- `chat/` — 对话相关
- `knowledge/` — 知识库管理
- `agents/` — Agent 监控
- `learning/` — 技术动态

### 3. 检查 Ant Design 是否已提供
去 [Ant Design 文档](https://ant.design/components/overview-cn) 确认是否已有对应组件。
**如果 Ant Design / Ant Design X 已有，直接使用，不要二次封装**（除非需要注入特定业务逻辑）。

## 创建步骤

### 4. 创建组件文件
```
components/{domain}/
  MyComponent.tsx          ← 组件代码
  MyComponent.module.css   ← 组件样式 (CSS Modules)
```

### 5. 组件模板
```typescript
/**
 * {组件名} — {一句话描述}
 *
 * 基于: {Ant Design 的 XX 组件 / 自定义}
 * @module components/{domain}
 * @see REGISTRY.md > 前端 > 组件 > {组件名}
 */

import React from 'react';
import styles from './MyComponent.module.css';

interface MyComponentProps {
  // Props 必须有 JSDoc 注释
  /** 主要内容 */
  content: string;
}

export const MyComponent: React.FC<MyComponentProps> = ({ content }) => {
  return (
    <div className={styles.container}>
      {content}
    </div>
  );
};
```

### 6. 样式模板
```css
/* MyComponent.module.css */
/* 使用 Ant Design CSS 变量，禁止硬编码 */

.container {
  padding: var(--ant-padding);
  border-radius: var(--ant-border-radius);
  background: var(--ant-color-bg-container);
}
```

### 7. 更新 REGISTRY.md
在注册表中登记新组件。

