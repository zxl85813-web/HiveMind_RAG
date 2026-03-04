# 📦 HiveMind RAG — 功能注册表 (Function Registry)

> **⚠️ 重要**: 每次开发新功能/组件前，必须先查阅此文件，确认是否已存在可复用的代码。
> 每次新增功能后，必须在此文件中登记。

> 📅 最后更新: 2026-02-15

---

## 🐍 后端 (Backend)

### API 端点

| 方法 | 路径 | 描述 | 文件 | 状态 |
|------|------|------|------|------|
| GET | `/api/v1/health/` | 健康检查 | `api/routes/health.py` | ✅ 已实现 |
| GET | `/api/v1/health/ready` | 就绪检查 | `api/routes/health.py` | 🔲 占位 |
| POST | `/api/v1/chat/completions` | 对话补全 (SSE) | `api/routes/chat.py` | ✅ |
| GET | `/api/v1/chat/conversations` | 会话列表 | `api/routes/chat.py` | ✅ |
| GET | `/api/v1/chat/conversations/{id}` | 会话详情 | `api/routes/chat.py` | ✅ |
| DELETE | `/api/v1/chat/conversations/{id}` | 删除会话 | `api/routes/chat.py` | ✅ |
| POST | `/api/v1/knowledge/` | 创建知识库 | `api/routes/knowledge.py` | 🔲 占位 |
| GET | `/api/v1/knowledge/` | 知识库列表 | `api/routes/knowledge.py` | 🔲 占位 |
| GET | `/api/v1/knowledge/{id}` | 知识库详情 | `api/routes/knowledge.py` | 🔲 占位 |
| DELETE | `/api/v1/knowledge/{id}` | 删除知识库 | `api/routes/knowledge.py` | 🔲 占位 |
| POST | `/api/v1/knowledge/{id}/documents` | 上传文档 | `api/routes/knowledge.py` | 🔲 占位 |
| GET | `/api/v1/knowledge/{id}/documents` | 文档列表 | `api/routes/knowledge.py` | 🔲 占位 |
| DELETE | `/api/v1/knowledge/{id}/documents/{doc_id}` | 删除文档 | `api/routes/knowledge.py` | 🔲 占位 |
| GET | `/api/v1/agents/` | Agent 列表 | `api/routes/agents.py` | 🔲 占位 |
| GET | `/api/v1/agents/{id}` | Agent 详情 | `api/routes/agents.py` | 🔲 占位 |
| GET | `/api/v1/agents/{id}/memory` | Agent 共享记忆 | `api/routes/agents.py` | 🔲 占位 |
| GET | `/api/v1/agents/swarm/todos` | 蜂巢 TODO 列表 | `api/routes/agents.py` | ✅ |
| POST | `/api/v1/agents/swarm/todos` | 添加 TODO | `api/routes/agents.py` | 🔲 |
| GET | `/api/v1/agents/swarm/reflections` | 自省日志 | `api/routes/agents.py` | ✅ |
| WS | `/api/v1/ws/connect` | WebSocket 连接 | `api/routes/websocket.py` | ✅ |
| GET | `/api/v1/learning/subscriptions` | 订阅列表 | `api/routes/learning.py` | ✅ |
| POST | `/api/v1/learning/subscriptions` | 添加订阅 | `api/routes/learning.py` | ✅ |
| DELETE | `/api/v1/learning/subscriptions/{id}` | 删除订阅 | `api/routes/learning.py` | ✅ |
| GET | `/api/v1/learning/discoveries` | 发现列表 | `api/routes/learning.py` | ✅ |
| GET | `/api/v1/learning/discoveries/{id}` | 发现详情 | `api/routes/learning.py` | 🔲 |
| POST | `/api/v1/learning/discoveries/{id}/apply` | 应用发现 | `api/routes/learning.py` | 🔲 |

### Schema (Pydantic 数据模型)

| 名称 | 用途 | 文件 | 状态 |
|------|------|------|------|
| `ChatRequest` | 对话请求体 | `schemas/chat.py` | ✅ |
| `ChatMessage` | 单条消息 | `schemas/chat.py` | ✅ |
| `ConversationResponse` | 会话详情响应 | `schemas/chat.py` | ✅ |
| `ConversationListItem` | 会话列表项 | `schemas/chat.py` | ✅ |
| `ServerMessage` | WS 服务端消息 | `schemas/ws.py` | ✅ |
| `ClientMessage` | WS 客户端消息 | `schemas/ws.py` | ✅ |
| `ServerEventType` | WS 服务端事件枚举 | `schemas/ws.py` | ✅ |
| `ClientEventType` | WS 客户端事件枚举 | `schemas/ws.py` | ✅ |

### 数据库模型 (SQLModel)

| 模型 | 表名 | 文件 | 状态 |
|------|------|------|------|
| `User` | users | `models/chat.py` | ✅ |
| `Conversation` | conversations | `models/chat.py` | ✅ |
| `Message` | messages | `models/chat.py` | ✅ |
| `KnowledgeBase` | knowledge_bases | `models/knowledge.py` | ✅ |
| `Document` | documents | `models/knowledge.py` | ✅ |

### Service (业务逻辑)

| 名称 | 职责 | 文件 | 状态 |
|------|------|------|------|
| `ConnectionManager` | WebSocket 连接管理 | `services/ws_manager.py` | ✅ |
| `KnowledgeService` | 知识库与文档管理 | `services/knowledge_base.py` | ✅ |

### Agent 模块

| 名称 | 职责 | 文件 | 状态 |
|------|------|------|------|
| `SwarmOrchestrator` | Agent 蜂巢编排 | `agents/swarm.py` | ✅ MVP |
| `AgentDefinition` | Agent 定义数据类 | `agents/swarm.py` | ✅ |
| `SharedMemoryManager` | 共享记忆管理 | `agents/memory.py` | ✅ |
| `TodoItem` | 共享 TODO 数据模型 | `models/agents.py` | ✅ |
| `ReflectionEntry` | 自省日志数据模型 | `models/agents.py` | ✅ |
| `LLMRouter` | 多 LLM 路由 | `agents/llm_router.py` | 🔲 框架 |
| `ModelConfig` | LLM 配置数据类 | `agents/llm_router.py` | ✅ |
| `MCPManager` | MCP 服务管理 | `agents/mcp_manager.py` | 🔲 框架 |
| `ExternalLearningEngine` | 外部学习引擎 | `agents/learning.py` | 🔲 框架 |
| `TechDiscovery` | 技术发现数据模型 | `agents/learning.py` | ✅ |
| `Subscription` | 订阅数据模型 | `agents/learning.py` | ✅ |

### Batch Engine (批处理与技能)

| 名称 | 职责 | 文件 | 状态 |
|------|------|------|------|
| `JobManager` | 任务编排与状态管理 | `batch/engine.py` | ✅ 核心 |
| `SkillRegistry` | 动态技能注册中心 | `skills/registry.py` | ✅ 核心 |
| `IngestionSkill` | 文件摄取技能 | `skills/ingestion/` | ✅ |

### 核心配置

| 名称 | 职责 | 文件 | 状态 |
|------|------|------|------|
| `Settings` | 全局配置 | `core/config.py` | ✅ |
| `settings` | 配置单例 | `core/config.py` | ✅ |
| `logger` | 统一日志 (loguru) | `core/logging.py` | ✅ |
| `setup_logging` | 环境切换日志配置 | `core/logging.py` | ✅ |
| `engine` / `async_session_factory` | 数据库引擎和会话工厂 | `core/database.py` | ✅ |
| `init_db` / `close_db` | 数据库生命周期管理 | `core/database.py` | ✅ |
| `get_db_session` | 数据库 Session 依赖注入 | `core/database.py` | ✅ |
| `AppError` / `NotFoundError` / ... | 统一异常层级 (6 种) | `core/exceptions.py` | ✅ |
| `register_exception_handlers` | 全局异常处理器注册 | `core/exceptions.py` | ✅ |
| `StorageBackend` | 文件存储抽象接口 | `core/storage.py` | ✅ |
| `VectorStore` | 向量存储抽象接口 | `core/vector_store.py` | ✅ |
| `GraphStore` | 知识图谱接口 (Neo4j) | `core/graph_store.py` | ✅ |
| `Reranker` | 重排序模型抽象接口 | `core/reranker.py` | ✅ |
| `LocalStorage` | 本地存储实现 | `core/storage.py` | ✅ |
| `MinIOStorage` | MinIO 存储 (框架) | `core/storage.py` | 🔲 |
| `RetrievalService` | 检索与重排序服务 | `services/retrieval.py` | ✅ |
| `get_storage` | 存储后端工厂 | `core/storage.py` | ✅ |
| `hash_password` / `verify_password` | 密码哈希 | `core/security.py` | ✅ |
| `create_access_token` / `decode_access_token` | JWT Token 管理 | `core/security.py` | ✅ |
| `get_db` | 依赖注入别名集合 | `core/deps.py` | ✅ |

---

## ⚛️ 前端 (Frontend)

### 页面

| 名称 | 路径 | 描述 | 文件 | 状态 |
|------|------|------|------|------|
| `DashboardPage` | `/` | 概览首页 (统计+快捷入口) | `pages/DashboardPage.tsx` | ✅ |
| `KnowledgePage` | `/knowledge` | 知识库管理 | `pages/KnowledgePage.tsx` | ✅ 占位 |
| `AgentsPage` | `/agents` | Agent 蜂巢监控面板 | `pages/AgentsPage.tsx` | ✅ |
| `LearningPage` | `/learning` | 技术动态/外部学习 | `pages/LearningPage.tsx` | ✅ |
| `SettingsPage` | `/settings` | 系统设置 (LLM/Agent/API Key) | `pages/SettingsPage.tsx` | ✅ 基础 |
| ~~`ChatPage`~~ | ~~`/chat`~~ | ~~已废弃 — Chat 现在是ChatPanel~~ | `pages/ChatPage.tsx` | 🚭 废弃 |

### 通用组件 (components/common/)

| 名称 | 基于 | 描述 | 状态 |
|------|------|------|------|
| `AppLayout` | Layout + ChatPanel | AI-First 全局布局 (顶栏+内容+Chat面板) | ✅ |
| `PageContainer` | Typography + Flex | 页面统一容器 (标题+描述+操作+内容) | ✅ |
| `StatCard` | Card + Statistic | 统计数据卡片 (图标+颜色预设) | ✅ |
| `EmptyState` | Card + Typography | 统一空状态展示 | ✅ |
| `StatusTag` | Tag | 统一状态标签 (8 种状态) | ✅ |

### 领域组件

| 名称 | 领域 | 描述 | 目录 | 状态 |
|------|------|------|------|------|
| `ChatPanel` | chat | AI 对话面板 (永驻右侧, 上下文感知) | `components/chat/` | ✅ |
| `ActionButton` | chat | AI 操作按钮 (导航/执行/弹窗) | `components/chat/` | ✅ |
| `AgentCard` | agents | Agent 状态卡片 | `components/agents/` | ✅ |

### 样式系统 (styles/)

| 文件 | 描述 | 状态 |
|------|------|------|
| `variables.css` | CSS 变量 (渐变/布局/间距/阴影/动画/层级) | ✅ |
| `mixins.module.css` | 可复用 CSS Module 模式 (毛玻璃/渐变文字/布局工具) | ✅ |
| `animations.css` | 共通动画关键帧 | ✅ |

### Hooks

| 名称 | 描述 | 文件 | 状态 |
|------|------|------|------|
| — | 待实现 (useSSE, useWebSocket, useChat) | — | 🔲 |

### Stores (Zustand)

| 名称 | 描述 | 文件 | 状态 |
|------|------|------|------|
| `useChatStore` | 对话状态 (消息、会话、生成状态) | `stores/chatStore.ts` | ✅ |
| `useWSStore` | WebSocket 连接状态、通知 | `stores/wsStore.ts` | ✅ |

### Services (API 调用)

| 名称 | 描述 | 文件 | 状态 |
|------|------|------|------|
| `api` | Axios 实例 (拦截器/认证/错误处理) | `services/api.ts` | ✅ |
| `chatApi` | 对话 API (CRUD + SSE 流式) | `services/chatApi.ts` | ✅ 框架 |

### Types

| 名称 | 描述 | 文件 | 状态 |
|------|------|------|------|
| 全类型定义 | Chat, Agent, KB, WS, Todo, Discovery | `types/index.ts` | ✅ |



---

## 🧩 Skills

### 核心 Agent Skills

| 名称 | 描述 | 目录 | 状态 |
|------|------|------|------|
| `rag_search` | 知识库检索与问答（语义搜索/混合检索/多库查询） | `skills/rag_search/` | ✅ 完善 |
| `web_search` | 网络搜索增强（搜索策略/内容提取/多源验证） | `skills/web_search/` | ✅ 完善 |
| `data_analysis` | SQL 查询与数据分析（安全查询/统计分析/可视化） | `skills/data_analysis/` | ✅ 完善 |

### 文档处理 Skills

| 名称 | 描述 | 目录 | 状态 |
|------|------|------|------|
| `docx` | Word 文档创建/编辑/分析（含修订追踪和批注） | `skills/docx/` | ✅ 已集成 |
| `pdf` | PDF 处理全套（合并/拆分/文字提取/OCR/水印） | `skills/pdf/` | ✅ 已集成 |
| `pptx` | PowerPoint 演示文稿处理（读取/编辑/创建/QA） | `skills/pptx/` | ✅ 已集成 |
| `xlsx` | Excel 电子表格处理（公式/格式/财务模型） | `skills/xlsx/` | ✅ 已集成 |

### 设计与创意 Skills

| 名称 | 描述 | 目录 | 状态 |
|------|------|------|------|
| `frontend-design` | 高品质前端 UI 设计（美学指导/HiveMind 设计系统） | `skills/frontend-design/` | ✅ 已集成 |
| `canvas-design` | 高品质视觉设计（PDF/PNG 艺术产出） | `skills/canvas-design/` | ✅ 已集成 |
| `algorithmic-art` | p5.js 算法艺术生成（交互式生成艺术） | `skills/algorithmic-art/` | ✅ 已集成 |
| `brand-guidelines` | HiveMind 品牌视觉规范（配色/字体/间距） | `skills/brand-guidelines/` | ✅ 已集成 |
| `theme-factory` | 主题样式工厂（10+ 预设主题） | `skills/theme-factory/` | ✅ 已集成 |

### 工程工具 Skills

| 名称 | 描述 | 目录 | 状态 |
|------|------|------|------|
| `mcp-builder` | MCP Server 构建指南 | `skills/mcp-builder/` | ✅ 已集成 |
| `skill-creator` | Skill 元技能（创建其他 Skills 的指南） | `skills/skill-creator/` | ✅ 已集成 |
| `webapp-testing` | Playwright Web 应用测试 | `skills/webapp-testing/` | ✅ 已集成 |
| `web-artifacts-builder` | React/Tailwind 独立 HTML 制品构建 | `skills/web-artifacts-builder/` | ✅ 已集成 |
| `slack-gif-creator` | Slack 优化 GIF 动图制作 | `skills/slack-gif-creator/` | ✅ 已集成 |

### 写作协作 Skills

| 名称 | 描述 | 目录 | 状态 |
|------|------|------|------|
| `doc-coauthoring` | 结构化文档协作撰写工作流 | `skills/doc-coauthoring/` | ✅ 已集成 |
| `internal-comms` | 内部沟通文档撰写（状态报告/周报/ADR） | `skills/internal-comms/` | ✅ 已集成 |


---

## 🔧 MCP Servers

| 名称 | 描述 | 目录 | 状态 |
|------|------|------|------|
| — | 尚未实现 | — | 🔲 |

---

## 📐 共通化记录

> 记录已识别的共通化模式，避免重复造轮子。

### 后端共通模式
| 模式 | 说明 | 使用位置 |
|------|------|---------|
| CRUD Service 基类 | 通用增删改查 | 待实现 — 所有 Service 应继承 |
| 分页响应 Schema | 统一分页格式 | 待实现 — 所有列表 API |
| 异常处理 | 统一错误响应格式 | 待实现 — core/exceptions.py |
| 事件发布 | 内部事件总线 | 待实现 — 用于 WS 推送触发 |

### 前端共通模式
| 模式 | 说明 | 使用位置 |
|------|------|---------|
| useSSE Hook | SSE 流式连接封装 | 待实现 — 对话页面 |
| useWebSocket Hook | WS 持久连接封装 | 待实现 — 全局 |
| ErrorDisplay 组件 | 统一错误展示 | 待实现 — 所有页面 |
| LoadingState 组件 | 统一加载态 | 待实现 — 所有数据加载 |
| ConfirmAction 组件 | 统一确认弹窗 | 待实现 — 所有危险操作 |

---

> 💡 **状态图例**: ✅ 已实现 | 🔲 占位/框架 | 🚧 开发中 | ❌ 已废弃

---

## 🔗 文档 ↔ 代码 追溯矩阵 (Traceability)

> 每个需求都可以追溯到设计文档、代码实现和测试用例。

| 需求 | 设计文档 | 核心代码 | 测试 | API 文档 | 状态 |
|------|---------|---------|------|---------|------|
| REQ-001 Agent 蜂巢 | DES-001 (待) | `agents/swarm.py` | 待编写 | `docs/api/agents.md` (待) | 🔲 |
| REQ-002 共享记忆 | DES-002 (待) | `agents/memory.py` | 待编写 | `docs/api/agents.md` (待) | 🔲 |
| REQ-003 对外学习 | DES-003 (待) | `agents/learning.py` | 待编写 | `docs/api/learning.md` (待) | 🔲 |
| REQ-004 多 LLM | — | `agents/llm_router.py` | 待编写 | — | 🔲 |
| REQ-005 MCP+Skills | — | `agents/mcp_manager.py`, `agents/skills.py` | 待编写 | — | 🔲 |
| REQ-006 通信 | ADR-001 ✅ | `routes/chat.py`, `routes/websocket.py`, `services/ws_manager.py` | 待编写 | `docs/api/chat.md` (待) | 🔲 |
| REQ-007 开发治理 | — | `.agent/rules/*`, `.agent/workflows/*` | N/A | `docs/README.md` ✅ | 🟢 |
| REQ-008 RAG Pipeline & 质量体系 | REQ-008 ✅ | `services/retrieval/`, `services/indexing.py` | 待编写 | — | 🔲 |
| REQ-009 RAG 进阶能力 | REQ-009 ✅ | `services/retrieval/`, `core/graph_store.py`, `services/memory/` | 待编写 | — | 🔲 |
| REQ-010 数据脱敏体系 | REQ-010 ✅ | 待实现 | 待编写 | — | 🔲 |

---

## 📖 文档索引

| 类型 | 文档 | 描述 |
|------|------|------|
| 📋 需求 | `docs/requirements/REQ-001-agent-swarm.md` | Agent 蜂巢架构 |
| 📋 需求 | `docs/requirements/REQ-002-shared-memory.md` | 共享记忆与自省 |
| 📋 需求 | `docs/requirements/REQ-003-external-learning.md` | 对外学习机制 |
| 📋 需求 | `docs/requirements/REQ-004-multi-llm.md` | 多 LLM 路由 |
| 📋 需求 | `docs/requirements/REQ-005-mcp-skills.md` | MCP 与 Skills |
| 📋 需求 | `docs/requirements/REQ-006-communication.md` | 混合通信 |
| 📋 需求 | `docs/requirements/REQ-007-dev-governance.md` | 开发治理 |
| 🏗️ 架构 | `docs/design/architecture.md` | 整体架构设计 |
| 📝 决策 | `docs/changelog/decisions/ADR-001-sse-ws-hybrid.md` | SSE+WS 方案 |
| 📝 变更 | `docs/changelog/CHANGELOG.md` | 版本变更记录 |
| 📏 规则 | `.agent/rules/project-structure.md` | 项目结构规范 |
| 📏 规则 | `.agent/rules/coding-standards.md` | 编码规范 |
| 📏 规则 | `.agent/rules/frontend-design-system.md` | 前端设计系统 |
| 🔍 代码检查 | `.agent/checks/code_quality.py` | 类 SonarQube 质量检查系统 |
| 🔍 代码检查 | `.agent/checks/run_checks.ps1` | PowerShell 快捷检查脚本 |

---

## 🔄 工作流索引

| Slash Command | 描述 | 触发时机 |
|--------------|------|---------|
| `/develop-feature` | 开发新功能标准流程 | 每次开发新功能前 |
| `/create-component` | 创建前端组件 | 需要新增前端组件时 |
| `/create-api` | 创建后端 API | 需要新增 API 端点时 |
| `/extract-requirement` | 从对话中提取需求 | 用户提出新需求时 |
| `/decompose-feature` | 分解复杂功能 | 功能复杂度高时 |
| `/code-review` | 代码自省与自查 | 达到版本里程碑时 |
