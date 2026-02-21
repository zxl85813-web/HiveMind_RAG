---
name: brand-guidelines
description: "HiveMind 平台品牌视觉规范 — 统一的配色、字体和设计标准。当创建任何需要品牌一致性的设计产出时使用，包括：文档样式、演示文稿、UI组件、营销材料等。"
---

# HiveMind 品牌视觉规范

## Overview

HiveMind RAG Platform 的官方品牌标识和视觉设计标准。

**Keywords**: 品牌, 视觉标识, 配色, 字体, 设计规范, UI 主题

## 品牌色彩系统

### 主色 (Primary)

| 名称 | 色值 | 用途 |
|------|------|------|
| Indigo 600 | `#4F46E5` | 主按钮、链接、品牌强调 |
| Indigo 700 | `#4338CA` | 悬停态、深色强调 |
| Indigo 50 | `#EEF2FF` | 浅色背景、选中态 |

### 辅色 (Secondary)

| 名称 | 色值 | 用途 |
|------|------|------|
| Emerald 500 | `#10B981` | 成功状态、Agent 在线 |
| Amber 500 | `#F59E0B` | 警告、待处理 |
| Red 500 | `#EF4444` | 错误、危险操作 |

### 中性色 (Neutral)

| 名称 | 色值 | 用途 |
|------|------|------|
| Dark | `#111827` | 主文本、深色背景 |
| Light | `#F9FAFB` | 浅色背景 |
| Mid Gray | `#6B7280` | 次要文本 |
| Light Gray | `#E5E7EB` | 边框、分割线 |
| White | `#FFFFFF` | 卡片背景、亮色表面 |

### 渐变方案

```css
/* 主品牌渐变 */
background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 50%, #EC4899 100%);

/* 深色主题渐变 */
background: linear-gradient(135deg, #1E1B4B 0%, #312E81 50%, #4F46E5 100%);

/* 毛玻璃效果 */
background: rgba(255, 255, 255, 0.08);
backdrop-filter: blur(20px);
border: 1px solid rgba(255, 255, 255, 0.12);
```

## 字体系统

### 中文环境

| 用途 | 字体 | 备选 |
|------|------|------|
| 标题 | HarmonyOS Sans SC Bold | PingFang SC Bold |
| 正文 | HarmonyOS Sans SC | PingFang SC, Microsoft YaHei |
| 代码 | JetBrains Mono | Fira Code, Consolas |

### 英文环境

| 用途 | 字体 | 备选 |
|------|------|------|
| 标题 | Inter Bold / Outfit Bold | system-ui |
| 正文 | Inter | -apple-system, Segoe UI |
| 代码 | JetBrains Mono | Fira Code |

### 字号规范

| 层级 | 字号 | 行高 | 用途 |
|------|------|------|------|
| H1 | 28-32px | 1.3 | 页面主标题 |
| H2 | 22-24px | 1.35 | 区域标题 |
| H3 | 18-20px | 1.4 | 卡片标题 |
| Body | 14-16px | 1.6 | 正文 |
| Caption | 12px | 1.5 | 辅助说明 |
| Code | 13px | 1.5 | 代码 |

## 设计应用规则

### 文本样式

- 标题使用 Bold 或 Semi-Bold 字重
- 正文使用 Regular 字重
- 深色背景上使用白色/浅色文字
- 浅色背景上使用深色文字
- 确保对比度满足 WCAG AA 标准（最低 4.5:1）

### 形状与间距

- 圆角统一使用 `8px`（小组件）、`12px`（卡片）、`16px`（模态框）
- 间距系统基于 4px 网格：4, 8, 12, 16, 24, 32, 48, 64
- 卡片阴影：`0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06)`
- 悬停阴影：`0 10px 15px rgba(0,0,0,0.1), 0 4px 6px rgba(0,0,0,0.05)`

### 图标风格

- 线条图标优先（outline style）
- 线条粗细 1.5-2px
- 与文字对齐时保持视觉居中
- 推荐图标库：Lucide Icons, Heroicons
