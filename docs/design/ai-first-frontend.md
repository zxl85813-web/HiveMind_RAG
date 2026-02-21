# AI-First 前端架构设计

## 核心理念

**Chat 不是一个页面，而是整个应用的中枢神经。**

传统 SaaS: 用户通过菜单 → 找到页面 → 手动操作  
AI-First:  用户通过对话 → AI 理解意图 → 自动导航/执行/展示

## 布局架构

```
┌───────────────────────────────────────────────────────────┐
│  ⬡ HiveMind    知识库  Agents  动态  设置          🔔  ● │ ← Header
├──────────────────────────────────┬────────────────────────┤
│                                  │                        │
│         Main Content             │      AI Chat Panel     │
│         (路由页面)                │      (永驻右侧)        │
│                                  │                        │
│   - Dashboard (默认首页)          │   对话上下文跟随页面    │
│   - 知识库管理                    │   AI 可以:             │
│   - Agent 监控                   │   · 导航到指定页面      │
│   - 技术动态                     │   · 打开模态框          │
│   - 设置                        │   · 在页面中高亮元素     │
│                                  │   · 执行后台操作         │
│                                  │   · 推送建议卡片         │
│                                  │                        │
│                                  ├────────────────────────┤
│                                  │  📎 [输入你的问题...]    │
└──────────────────────────────────┴────────────────────────┘
```

### 关键设计决策

1. **Chat Panel 永驻右侧** — 不是浮动窗口，是布局的固有部分
2. **可折叠** — 用户可以折叠 chat panel，全屏查看页面内容
3. **上下文感知** — Chat 知道用户在哪个页面，自动调整建议
4. **默认首页是 Dashboard** — 不再是空白 ChatPage
5. **Chat 驱动导航** — AI 回答中嵌入 ActionButton，点击可跳转

## AI Action 系统

AI 的回答不只是文字，还可以包含结构化的操作指令：

```typescript
// AI 可以在回答中嵌入的 Action 类型
type AIActionType = 
  | 'navigate'       // 导航到指定页面
  | 'open_modal'     // 打开模态框 (如创建知识库)
  | 'highlight'      // 在页面中高亮某个元素
  | 'execute'        // 执行后台操作 (如上传文件)
  | 'suggest'        // 推荐操作 (卡片形式展示)
  | 'show_data'      // 内联展示数据 (表格/图表)

interface AIAction {
  type: AIActionType;
  label: string;           // 按钮文字
  target: string;          // 路由路径 or 操作 ID
  icon?: string;           // 图标
  params?: Record<string, unknown>;
}
```

### 示例交互流:

```
用户: "帮我创建一个知识库"
AI:   "好的，我来帮你创建知识库。请填写以下信息：
       [📚 创建知识库] ← ActionButton → 导航到 /knowledge 并打开创建弹窗"

用户: "最近有什么新的开源项目？"
AI:   "让我查看一下技术动态...
       [↗ 查看技术动态] ← 跳转 /learning
       目前有 3 个值得关注的项目: ..."

用户: "Agent 都在干嘛？"
AI:   "当前 Agent 状态:
       🧭 Supervisor - 空闲
       📚 RAG Agent - 处理中...
       [🐝 查看完整监控] ← 跳转 /agents"
```

## Chat Panel 状态

```typescript
interface ChatPanelState {
  isOpen: boolean;           // 面板展开/折叠
  width: number;             // 面板宽度 (可拖拽)
  context: ChatContext;      // 当前上下文
}

interface ChatContext {
  currentPage: string;       // 当前页面路由
  pageTitle: string;         // 页面标题
  selectedItems?: string[];  // 用户在页面选中的项目
  availableActions: string[];// 当前页面可用的 AI 动作
}
```

## 路由结构变更

```
Before (Chat 是页面):
  / → redirect to /chat
  /chat → ChatPage (独立页面)
  /knowledge → KnowledgePage
  ...

After (Chat 是面板):
  / → Dashboard (概览首页)
  /knowledge → Knowledge (Chat Panel 跟随)
  /agents → Agents (Chat Panel 跟随)
  /learning → Learning (Chat Panel 跟随)
  /settings → Settings (Chat Panel 跟随)
```

## 文件结构

```
components/
  chat/                    ← AI Chat Panel 核心
    ChatPanel.tsx           # 右侧永驻面板容器
    ChatPanel.module.css
    ChatMessages.tsx        # 消息列表 (支持 ActionButton)
    ChatInput.tsx           # 输入区 (附件/快捷命令)
    ChatContext.tsx          # 上下文感知指示器
    ActionButton.tsx         # AI 操作按钮
  common/
    AppLayout.tsx            # 更新: Header + Content + ChatPanel
  dashboard/
    DashboardPage.tsx        # 新首页: 概览 + 快捷入口
```
