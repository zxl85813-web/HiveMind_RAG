---
description: 项目结构规范 — 严禁随意添加或更改目录
---

# 📁 项目结构规范

## 核心原则
**目录结构是固定的。未经讨论和审批，严禁创建新的顶层目录或子目录。**

## 顶层目录

```
hivemind-rag/
├── .agent/                # 🤖 AI 开发治理
│   ├── rules/             #   编码规范、设计系统、结构约束
│   └── workflows/         #   标准开发流程
├── backend/               # 🐍 FastAPI 后端服务
├── frontend/              # ⚛️ React 前端应用 (AI-First)
├── shared/                # 🔗 前后端共享协议
├── mcp-servers/           # 🔌 MCP Server 集合
├── skills/                # 🧩 Skills 技能包
├── docs/                  # 📖 项目文档
├── docker/                # 🐳 容器编排
├── REGISTRY.md            # 📦 功能注册表 (开发前必查)
├── TODO.md                # 📋 待办清单
└── README.md              # 📄 项目首页
```

---

## 后端模块架构 (backend/app/)

### 设计原则

后端按**职责域**拆分为独立模块，每个模块有清晰的边界和单一职责。
模块之间只能通过接口交互，不得交叉引用内部实现。

```
backend/
├── .env.example               # 环境变量模板
├── pyproject.toml             # 依赖和工具配置
├── mcp_servers.json           # MCP Server 注册配置
├── alembic.ini                # 🆕 数据库迁移配置
├── alembic/                   # 🆕 迁移脚本目录
├── scripts/                   # 🆕 运维脚本 (create_admin.py, seed_db.py)
└── app/
    ├── main.py                # FastAPI 应用入口 + 生命周期
    │
    │  ════════════════════════════════════════════
    │  第一层: API 网关 (入口)
    │  ════════════════════════════════════════════
    ├── api/                   # 🌐 API 网关层
    │   ├── __init__.py        #   路由注册 (所有 router 汇总)
    │   ├── deps.py            #   路由级依赖注入 (get_current_user 等)
    │   └── routes/            #   路由定义 (每资源一个文件, thin)
    │       ├── health.py      #     健康检查
    │       ├── auth.py        #     认证端点
    │       ├── chat.py        #     对话端点
    │       ├── knowledge.py   #     知识库端点
    │       ├── agents.py      #     Agent 端点
    │       ├── learning.py    #     外部学习端点
    │       ├── admin.py       #     管理端点
    │       └── websocket.py   #     WebSocket 端点
    │
    │  ════════════════════════════════════════════
    │  第二层: 业务逻辑 (Where things happen)
    │  ════════════════════════════════════════════
    ├── services/              # 💼 业务服务层
    │   ├── __init__.py
    │   ├── chat_service.py    #   对话业务
    │   ├── kb_service.py      #   知识库业务
    │   ├── user_service.py    #   用户业务
    │   ├── ws_manager.py      #   WebSocket 管理
    │   └── evaluation/        #   🆕 评估体系 (Eval v2)
    │       ├── __init__.py    #     EvaluationService (L1/L2/L3 评测)
    │       ├── graders/       #     独立评估器架构
    │       │   ├── base.py    #       BaseGrader (CoT + 多采样 + 置信度)
    │       │   ├── faithfulness.py  # 忠实度 (逐句 claim 验证)
    │       │   ├── relevance.py     # 相关性 (逆向问题生成)
    │       │   ├── correctness.py   # 正确性 (GT 事实对比)
    │       │   └── context.py       # 上下文精确度 + 召回率
    │       ├── multi_grader.py      # 多裁判评估器
    │       ├── rag_assertion_grader.py  # 硬规则断言层
    │       └── ab_tracker.py        # A/B 实验追踪器
    │
    │  ════════════════════════════════════════════
    │  第三层: Agent 蜂巢 (AI 核心)
    │  ════════════════════════════════════════════
    ├── agents/                # 🐝 Agent 蜂巢集群
    │   ├── __init__.py
    │   ├── swarm.py           #   Supervisor 编排器
    │   ├── base.py            #   Agent 基类
    │   ├── rag_agent.py       #   RAG Agent
    │   ├── web_agent.py       #   Web 搜索 Agent
    │   ├── code_agent.py      #   代码生成 Agent
    │   └── reflection.py      #   自省 Agent
    │
    ├── prompts/               # 🗣️ Prompt 资产管理 (🆕)
    │   ├── __init__.py
    │   ├── loader.py          #   加载器 (YAML/JinjaRv2)
    │   ├── base/              #   基础 Prompt
    │   ├── agents/            #   Agent 专用 Prompt
    │   └── templates/         #   动态模板
    │
    │  ════════════════════════════════════════════
    │  第四层: 独立基础设施模块
    │  ════════════════════════════════════════════
    ├── core/                  # ⚙️ 核心基础设施 (框架级, 不含业务)
    │   ├── __init__.py
    │   ├── config.py          #   全局配置 (Pydantic Settings)
    │   ├── logging.py         #   日志系统 (loguru + request_id)
    │   ├── database.py        #   数据库引擎/Session/生命周期
    │   ├── exceptions.py      #   统一异常 + 全局处理器
    │   ├── storage.py         #   文件存储 (Local/MinIO)
    │   └── events.py          #   🆕 内部事件总线 (模块解耦)
    │
    ├── common/                # 🧱 跨模块共享组件
    │   ├── __init__.py
    │   ├── base.py            #   Model Mixin (时间戳/软删除/ID生成)
    │   ├── enums.py           #   通用枚举 (Status/Priority/SortOrder)
    │   ├── pagination.py      #   统一分页 (PaginationParams + PaginatedResponse)
    │   └── response.py        #   统一响应 (ApiResponse 包装器)
    │
    ├── auth/                  # 🔐 认证与授权模块
    │   ├── __init__.py
    │   ├── security.py        #   JWT 生成/验证 + 密码哈希
    │   ├── permissions.py     #   🆕 RBAC 权限 (角色/权限/装饰器)
    │   ├── oauth.py           #   🆕 OAuth2 社交登录 (GitHub等)
    │   └── middleware.py      #   🆕 认证中间件 (自动 Token 校验)
    │
    ├── audit/                 # 📋 审计与合规模块
    │   ├── __init__.py
    │   ├── logger.py          #   🆕 操作审计日志 (who/what/when)
    │   ├── sanitizer.py       #   🆕 数据脱敏 (PII/敏感字段)
    │   └── rate_limiter.py    #   🆕 API 限流 (per-user/per-IP)
    │
    ├── llm/                   # 🧠 LLM 统一接入层
    │   ├── __init__.py
    │   ├── router.py          #   多 LLM 路由器 (原 llm_router.py)
    │   ├── providers.py       #   🆕 Provider 适配器 (OpenAI/DeepSeek/..)
    │   ├── guardrails.py      #   🆕 Prompt 安全防护 (注入检测/输出过滤)
    │   └── tracker.py         #   🆕 Token/成本追踪
    │
    ├── memory/                # 💾 共享记忆系统
    │   ├── __init__.py
    │   ├── manager.py         #   记忆管理器 (原 memory.py)
    │   ├── working.py         #   🆕 工作记忆 (Redis)
    │   ├── episodic.py        #   🆕 情景记忆 (对话摘要)
    │   ├── semantic.py        #   🆕 语义记忆 (向量检索)
    │   └── todo.py            #   🆕 共享 TODO 队列
    │
    ├── rag/                   # 📚 RAG 检索增强生成
    │   ├── __init__.py
    │   ├── pipeline.py        #   RAG 主流水线 (end-to-end)
    │   ├── chunker.py         #   🆕 文档分块策略
    │   ├── embedder.py        #   🆕 向量化 (embedding)
    │   ├── retriever.py       #   🆕 混合检索 (向量+关键词)
    │   ├── reranker.py        #   🆕 结果重排序
    │   └── parser.py          #   🆕 文档解析 (PDF/DOCX/MD)
    │
    ├── mcp/                   # 🔌 MCP 协议集成
    │   ├── __init__.py
    │   ├── manager.py         #   MCP Server 管理 (原 mcp_manager.py)
    │   ├── adapter.py         #   🆕 MCP → LangChain Tool 适配
    │   └── registry.py        #   🆕 MCP Server 注册中心
    │
    ├── skills/                # 🧩 Skills 技能系统
    │   ├── __init__.py
    │   ├── registry.py        #   技能注册 (原 skills.py)
    │   ├── loader.py          #   🆕 动态加载器
    │   └── sandbox.py         #   🆕 执行沙箱
    │
    ├── learning/              # 🌐 外部学习引擎
    │   ├── __init__.py
    │   ├── engine.py          #   学习引擎 (原 learning.py)
    │   ├── fetchers.py        #   🆕 数据源适配器 (GitHub/HN/ArXiv)
    │   ├── analyzer.py        #   🆕 相关性分析
    │   └── scheduler.py       #   🆕 定时调度
    │
    ├── workflow/              # 🔄 工作流引擎
    │   ├── __init__.py
    │   ├── engine.py          #   🆕 工作流执行器
    │   ├── definitions.py     #   🆕 工作流模板定义
    │   └── triggers.py        #   🆕 触发器 (定时/事件/手动)
    │
    │  ════════════════════════════════════════════
    │  第五层: 数据层 (Data)
    │  ════════════════════════════════════════════
    ├── models/                # 🗃️ SQLModel 数据库模型
    │   ├── __init__.py
    │   ├── user.py            #   🆕 用户模型
    │   ├── chat.py            #   对话/消息模型
    │   ├── knowledge.py       #   知识库/文档模型
    │   ├── agent.py           #   🆕 Agent 配置模型
    │   ├── audit.py           #   🆕 审计日志模型
    │   └── learning.py        #   🆕 技术发现模型
    │
    ├── schemas/               # 📐 Pydantic 请求/响应 Schema
    │   ├── __init__.py
    │   ├── auth.py            #   🆕 认证 Schema
    │   ├── chat.py            #   对话 Schema
    │   ├── knowledge.py       #   🆕 知识库 Schema
    │   ├── agent.py           #   🆕 Agent Schema
    │   ├── admin.py           #   🆕 管理端 Schema
    │   └── ws.py              #   WebSocket Schema
    │
    └── utils/                 # 🔧 工具函数
        ├── __init__.py
        ├── id_gen.py          #   🆕 ID 生成 (UUID/ULID)
        ├── time.py            #   🆕 时间处理 (UTC 统一)
        └── pagination.py      #   🆕 分页工具
```

### 模块依赖图

```
api/ ──→ services/ ──→ agents/ ──→ llm/
  │         │             │         ↑
  │         │             ├──→ memory/
  │         │             ├──→ rag/
  │         │             ├──→ mcp/
  │         │             ├──→ skills/
  │         │             └──→ learning/
  │         │
  │         ├──→ auth/
  │         └──→ audit/
  │
  ├──→ common/ (多数模块依赖)
  │      ├── base        — Model Mixin
  │      ├── enums       — 通用枚举
  │      ├── pagination  — 分页
  │      └── response    — API 响应
  │
  └──→ core/ (所有模块都依赖)
         ├── config
         ├── logging
         ├── database
         ├── exceptions
         ├── storage
         └── events
```

### 三层定位区分

| 层 | 职责 | 放什么 | 不放什么 |
|----|------|--------|----------|
| `core/` | 框架基础设施 | config, db engine, logging setup, 异常体系 | 业务类型、共享枚举 |
| `common/` | 跨模块共享 | Model Mixin, 通用枚举, 分页, 响应包装 | 框架配置、纯函数 |
| `utils/` | 纯工具函数 | 字符串处理、时间格式化、无状态计算 | 任何含状态或依赖的东西 |

### 模块边界规则

| 层级 | 可以调用 | 不可以调用 |
|------|----------|-----------|
| `api/routes/` | `services/`, `auth/`, `schemas/`, `common/` | `agents/`, `models/`, `llm/` |
| `services/` | `agents/`, `auth/`, `audit/`, `models/`, `schemas/`, `common/` | `api/` |
| `agents/` | `llm/`, `memory/`, `rag/`, `mcp/`, `skills/`, `core/`, `common/` | `api/`, `services/` |
| `auth/` | `models/`, `core/`, `common/` | `agents/`, `services/` |
| `audit/` | `models/`, `core/`, `common/` | `agents/`, `services/` |
| `llm/` | `core/`, `common/` | 其他所有业务模块 |
| `memory/` | `core/`, `common/` | 其他所有业务模块 |
| `common/` | `core/` (仅) | 其他所有模块 |
| `core/` | 无外部依赖 | — |

---

## ⚛️ 前端 (frontend/src/) — AI-First 架构

**核心理念:** Chat 不是页面，是永驻右侧面板，驱动整个应用的交互。

```
frontend/
├── .env                       # 环境变量
├── vite.config.ts             # Vite 配置
├── tsconfig*.json             # TypeScript 配置
└── src/
    ├── App.tsx                # 根组件 (主题 + 路由)
    ├── main.tsx               # 入口文件
    ├── index.css              # 全局样式
    ├── vite-env.d.ts          # 类型声明
    │
    ├── components/            # 组件 — 按功能域分目录
    │   ├── common/            #   通用 (Layout, PageContainer, StatCard..)
    │   ├── chat/              #   Chat 领域 (ChatPanel, ActionButton)
    │   ├── agents/            #   Agent 领域 (AgentCard)
    │   ├── knowledge/         #   知识库领域
    │   └── learning/          #   技术动态领域
    │
    ├── pages/                 # 页面 (thin, 组合组件)
    │   ├── DashboardPage.tsx  #   概览首页
    │   ├── KnowledgePage.tsx  #   知识库管理
    │   ├── AgentsPage.tsx     #   Agent 监控
    │   ├── LearningPage.tsx   #   技术动态
    │   └── SettingsPage.tsx   #   系统设置
    │
    ├── stores/                # Zustand 状态管理
    ├── services/              # API 请求封装
    ├── hooks/                 # 自定义 Hooks
    ├── types/                 # TypeScript 类型
    ├── styles/                # 共通样式系统
    └── utils/                 # 工具函数
```

---

## 📖 文档 (docs/)

```
docs/
├── README.md                  # 文档导航
├── architecture.md            # 系统架构总览
├── design/                    # 设计文档
│   └── ai-first-frontend.md
├── evaluation/                # 🆕 评估体系
│   ├── RAG_EVALUATION_FRAMEWORK.md    # RAG 三层评测框架
│   ├── AGENT_EVALUATION_FRAMEWORK.md  # Agent 四层评测框架
│   ├── EVALUATION_SYSTEM_AUDIT.md     # 评估体系审计报告
│   ├── METRICS_CHEATSHEET.md          # RAG 指标速查
│   ├── AGENT_METRICS_CHEATSHEET.md    # Agent 指标速查
│   ├── L3_QUALITY_BOARD.md            # L3 看板 (自动生成)
│   └── L4_INTEGRITY_REPORT.md         # L4 报告 (自动生成)
├── requirements/              # 需求文档 (REQ-NNN-*.md)
│   ├── REQ-001 ~ REQ-007
│   └── ...
└── changelog/                 # 变更追踪
    ├── CHANGELOG.md
    ├── decisions/             # 架构决策 (ADR-NNN-*.md)
    └── devlog/                # 开发日志 (DEV-NNN-*.md)
```

---

## 规则

### ❌ 禁止行为
1. 不得在上述结构之外创建新目录
2. 不得在 `src/` 根目录直接创建组件文件
3. 不得在路由文件中直接写业务逻辑 (必须通过 `services/` 层)
4. 不得在 `api/` 层直接操作 `models/` (必须通过 `services/`)
5. 不得在 `agents/` 中直接创建 LLM 实例 (必须通过 `llm/` 路由)
6. 不得跳过 `auth/` 自行实现认证逻辑
7. 不得跳过 Schema 层直接使用 raw dict

### ✅ 新增文件的规则
- **新 API 端点**: 在 `api/routes/` 已有文件中添加
- **新业务逻辑**: 在 `services/` 中添加
- **新 Agent**: 在 `agents/` 中创建, 继承 `BaseAgent`
- **新组件**: 在 `components/` 对应子目录创建
- **如果确实需要新目录**: 必须先更新本文档并得到确认
