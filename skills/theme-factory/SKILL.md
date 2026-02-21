---
name: theme-factory
description: "HiveMind 平台 UI 主题切换系统 — 提供多套预设主题（配色 + 字体），用户可在设置页面切换。当需要修改或添加平台主题时使用此 Skill。包括：(1) 预设主题管理 (2) 自定义主题创建 (3) CSS 变量覆盖方案 (4) 主题切换逻辑实现。触发关键词：换肤、主题、暗色模式、亮色模式、配色切换。"
---

# Theme Factory — HiveMind UI 换肤系统

## Overview

为 HiveMind 平台提供多套 UI 主题。每个主题定义一组 CSS 变量覆盖值，通过 `data-theme` 属性切换。

**核心原则**: 主题只覆盖颜色和渐变变量，不改变布局、间距、圆角、动画等结构性变量。

## 技术架构

### 切换机制

```html
<!-- HTML 根元素添加 data-theme 属性 -->
<html data-theme="cyber-refined">  <!-- 默认主题 -->
<html data-theme="ocean-depths">    <!-- 切换到海洋主题 -->
```

### CSS 变量覆盖

每个主题通过 `[data-theme="xxx"]` 选择器覆盖 `:root` 中的颜色变量：

```css
/* 默认主题 (Cyber Refined) 定义在 :root 中 */
:root { /* ... variables.css 中的默认值 ... */ }

/* 主题覆盖 — 只改颜色相关变量 */
[data-theme="ocean-depths"] {
    --hm-color-bg-deepest: #0B1929;
    --hm-color-bg-base: #132F4C;
    --hm-color-bg-elevated: #1E3A5F;
    --hm-color-bg-float: #274D74;
    
    --hm-color-brand: #2D8B8B;
    --hm-color-brand-hover: #259090;
    --hm-color-brand-dim: rgba(45, 139, 139, 0.12);
    --hm-color-accent: #A8DADC;
    --hm-color-accent-dim: rgba(168, 218, 220, 0.12);
    
    --hm-color-success: #2D8B8B;
    --hm-color-warning: #F1C232;
    --hm-color-danger: #E06C75;
    --hm-color-info: #61AFEF;
    
    --hm-gradient-brand: linear-gradient(135deg, #2D8B8B, #A8DADC);
    --hm-gradient-brand-subtle: linear-gradient(135deg, rgba(45, 139, 139, 0.15), rgba(168, 218, 220, 0.15));
    --hm-gradient-surface: linear-gradient(180deg, #132F4C 0%, #0B1929 100%);
    --hm-gradient-glow: radial-gradient(ellipse at 50% 0%, rgba(45, 139, 139, 0.08) 0%, transparent 60%);
    
    --hm-shadow-glow: 0 0 24px rgba(45, 139, 139, 0.12);
    --hm-shadow-glow-strong: 0 0 40px rgba(45, 139, 139, 0.2);
    --hm-border-brand: 1px solid rgba(45, 139, 139, 0.25);
    --hm-glass-bg: rgba(19, 47, 76, 0.75);
}
```

### 前端切换逻辑

```typescript
// stores/themeStore.ts
interface ThemeState {
  current: string;
  setTheme: (theme: string) => void;
}

export const useThemeStore = create<ThemeState>()(
  persist(
    (set) => ({
      current: 'cyber-refined',
      setTheme: (theme) => {
        document.documentElement.setAttribute('data-theme', theme);
        set({ current: theme });
      },
    }),
    { name: 'hivemind-theme' }  // localStorage 持久化
  )
);
```

## 预设主题目录

所有主题定义在 `themes/` 目录，可直接转为 CSS 变量覆盖。

| # | 主题标识 | 名称 | 适合场景 |
|---|---------|------|----------|
| 0 | `cyber-refined` | Cyber Refined (默认) | 当前默认暗色主题，青绿色 |
| 1 | `ocean-depths` | 海洋深处 | 专业冷静，商务风 |
| 2 | `sunset-boulevard` | 日落大道 | 温暖活力，创意团队 |
| 3 | `forest-canopy` | 森林华盖 | 自然沉稳，环保科技 |
| 4 | `modern-minimalist` | 现代极简 | 简洁现代，通用场景 |
| 5 | `golden-hour` | 黄金时刻 | 温暖秋季，文档密集 |
| 6 | `arctic-frost` | 极地寒霜 | 清冷明亮，数据分析 |
| 7 | `desert-rose` | 沙漠玫瑰 | 柔和优雅，女性化 |
| 8 | `tech-innovation` | 科技创新 | 高对比度，技术演示 |
| 9 | `botanical-garden` | 植物园 | 清新有机，健康科技 |
| 10 | `midnight-galaxy` | 午夜星河 | 深紫神秘，创意/游戏 |

## 添加新主题

### 步骤

1. 在 `themes/` 下创建新的 `.css` 文件
2. 定义 `[data-theme="your-theme"]` 选择器
3. 覆盖所有颜色相关的 CSS 变量
4. 在 `themes/index.ts` 中注册主题元数据
5. 测试所有页面在新主题下的显示效果

### 必须覆盖的变量清单

```css
/* 背景色 (4个) */
--hm-color-bg-deepest, --hm-color-bg-base, --hm-color-bg-elevated, --hm-color-bg-float

/* 品牌色 (5个) */
--hm-color-brand, --hm-color-brand-hover, --hm-color-brand-dim
--hm-color-accent, --hm-color-accent-dim

/* 语义色 (4个) */
--hm-color-success, --hm-color-warning, --hm-color-danger, --hm-color-info

/* 渐变 (4个) */
--hm-gradient-brand, --hm-gradient-brand-subtle, --hm-gradient-surface, --hm-gradient-glow

/* 光效/边框 (3个) */
--hm-shadow-glow, --hm-shadow-glow-strong, --hm-border-brand

/* 毛玻璃 (1个) */
--hm-glass-bg
```

## 注意事项

- **文字色保持不变** — `text-primary`, `text-secondary`, `text-muted` 所有暗色主题通用
- **如需亮色主题** — 需额外覆盖 `text-*` 变量和 `border-subtle`, `border-light`
- **间距/圆角/动画不可覆盖** — 这些属于全局设计系统，不随主题变化
- **每个主题必须通过对比度测试** — 确保文字在各背景色上满足 WCAG AA (4.5:1)
