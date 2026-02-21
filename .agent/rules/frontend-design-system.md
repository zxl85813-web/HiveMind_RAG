---
description: 前端设计系统规范 — Cyber-Refined 风格
---

# 🎨 前端设计系统规范

## 核心原则
**设计方向: Cyber-Refined (赛博精致)**
- 顶部导航布局 (非侧边栏)
- 深色主题 (深青蓝背景)
- 品牌色: 青绿 `#06D6A0` + 蓝 `#118AB2`
- 字体: Sora (UI) + JetBrains Mono (代码)

**⚠️ 禁止的 "AI Slop" 风格:**
- ❌ Inter / Roboto / Arial 字体
- ❌ 紫色渐变 (`#6C5CE7`) 作为主色
- ❌ 白底 + 浅灰的 generic 风格
- ❌ 千篇一律的 Card Grid 布局

**参考来源:**
- 布局: blueberry-industry.com (顶部导航、Fintech 风格)
- 理念: Anthropic frontend-design skill (辨识度、大胆配色)

## 1. Design Token 体系

### 选色 (通过 Ant Design ConfigProvider)
```typescript
// App.tsx — 所有颜色在此定义
const theme = {
  token: {
    colorPrimary: '#06D6A0',     // 品牌色 (青绿)
    colorSuccess: '#06D6A0',     // 成功
    colorWarning: '#FFD166',     // 警告
    colorError: '#EF476F',       // 危险
    colorInfo: '#118AB2',        // 信息

    colorBgContainer: '#111827', // 容器
    colorBgElevated: '#1F2937',  // 浮层
    colorBgLayout: '#0A0E1A',   // 最深背景

    colorText: '#F8FAFC',
    colorTextSecondary: '#94A3B8',
    colorTextTertiary: '#475569',

    fontFamily: "'Sora', sans-serif",
    borderRadius: 10,
  },
};
```

### 项目级 CSS 变量 (styles/variables.css)
```css
/* 使用 --hm-* 前缀，补充 Ant Design */
.myElement {
  background: var(--hm-glass-bg);
  backdrop-filter: var(--hm-glass-blur);
  border: var(--hm-border-subtle);
  box-shadow: var(--hm-shadow-glow);
  animation: fadeInUp var(--hm-duration-normal) var(--hm-ease-out);
}

/* ❌ 禁止硬编码 */
.bad { color: #333; background: white; }
```

## 2. 布局规范

**顶部导航:**
- Header 使用 glassmorphism (毛玻璃)
- 固定在顶部 (position: fixed)
- Logo 左侧 + 导航菜单水平排列 + 右侧操作区
- 内容区居中，最大宽度 1280px

**页面结构:**
- 所有页面必须使用 `<PageContainer>` 包裹
- 禁止自行构造页面标题和头部

## 3. 组件使用规则

### 通用组件 (必须使用)
| 需求 | 使用 | 禁止 |
|------|------|------|
| 页面容器 | `<PageContainer>` | 自行写 Title + actions |
| 统计卡片 | `<StatCard>` | 自行 Card + Statistic |
| 空状态 | `<EmptyState>` | 自制空状态 UI |
| 状态标签 | `<StatusTag>` | 自行 Tag + Icon 组合 |

### Ant Design 组件 (不重复造轮子)
| 需求 | 使用 | 禁止 |
|------|------|------|
| 按钮 | `<Button>` from antd | `<button>` 原生标签 |
| 输入 | `<Input>` | `<input>` |
| 表格 | `<Table>` | 手写 `<table>` |
| 弹窗 | `<Modal>` | 自制弹窗 |
| 消息 | `message.success()` | alert() |
| 布局 | `<Flex>` / `<Space>` | 手写 flex |

### Ant Design X (AI 对话)
| 需求 | 使用 |
|------|------|
| 对话气泡 | `<Bubble>` / `<Bubble.List>` |
| 用户输入 | `<Sender>` |
| 欢迎页 | `<Welcome>` |
| 快捷提示 | `<Prompts>` |

## 4. 样式编写

### CSS Modules = 默认
```
components/chat/
  ChatBubble.tsx
  ChatBubble.module.css  ← 样式同名文件
```

### 样式层级
1. `styles/variables.css` — CSS 变量 (--hm-*)
2. `styles/animations.css` — 动画关键帧
3. `styles/mixins.module.css` — 可复用 CSS 模式 (compose 引用)
4. `*.module.css` — 组件私有样式

### 复用共通样式
```css
/* 通过 composes 引用 */
.myCard {
  composes: glassCard from '../../styles/mixins.module.css';
}
```

## 5. 动画
```css
/* ✅ 使用项目变量 */
.element {
  transition: all var(--hm-duration-normal) var(--hm-ease-out);
  animation: fadeInUp var(--hm-duration-normal) var(--hm-ease-out);
}

/* ❌ 禁止硬编码动画值 */
.bad { transition: all 0.3s ease; }
```
