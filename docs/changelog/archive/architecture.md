# 🏗️ HiveMind RAG — Architecture Design

## 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                         │
│  AI-Native Design (Vite + Zustand + React Query)             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │ AI 组件库 │ │ 分层记忆 │ │ 遥测埋点 │ │ 推测性预加载   │  │
│  │ (AntD X) │ │ (IDB/BM25)│ │ (Trace)  │ │ (意图驱动)     │  │
│  └──────────┘ └──────────┘ └──────────┘ └───────────────┘  │
├───────────────────┬──────────────────┬──────────────────────┤
│ 多轨流(SSE)断点续传│    WebSocket     │      REST API        │
├───────────────────┴──────────────────┴──────────────────────┤
│                     FastAPI Gateway                          │
├─────────────────────────────────────────────────────────────┤
│                  Agent Swarm (LangGraph)                      │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Supervisor Agent                                      │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │  │
│  │  │ RAG      │ │ SQL      │ │ Web      │ │ Reflect  │ │  │
│  │  │ Agent    │ │ Agent    │ │ Agent    │ │ Agent    │ │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ │  │
│  └───────┼─────────────┼────────────┼────────────┼───────┘  │
│  ┌───────▼─────────────▼────────────▼────────────▼───────┐  │
│  │          MCP Tools + Skills + Shared Memory            │  │
│  └───────────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              LLM Router (Multi-Model)                  │  │
│  └───────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│  PostgreSQL │ Redis │ Vector DB │ MinIO │ V3 Trace Store    │
└─────────────────────────────────────────────────────────────┘
```

## 核心设计理念

### 1. Agent 蜂巢 (Swarm)
Agent 不是单一的，而是一个协作的集群。Supervisor Agent 负责理解用户意图、
拆解任务、路由到专业 Agent，并汇总最终结果。

### 2. 对内反省 (Internal Reflection)
Agent 集群拥有共享记忆和 TODO List。每次回答后进行自评估，
检测错误并自纠正。信心不足时主动提醒用户介入。

### 3. 对外学习 (External Learning)
订阅引擎持续监控互联网，追踪与当前技术栈相关的新技术、
高星开源项目和最佳实践，定期向用户推送发现。

### 4. 混合通信与弹性层 (SSE + WebSocket)
- 双向实时：通过 WebSocket 下发通知流。
- 多轨协议：基于 SSE (`fetch-event-source` 断点续传技术) 返回文本、工具调用、运行状态等多轨数据流。
- 架构降级：在遇到被限流或出错时，借助监控状态机自动退让或平滑降级（Graceful Degradation）。

### 5. 体验预判与分层缓存 (Prediction & Memory)
前端引入意图驱动预加载机制：大模型在返回内容时附带推测意图，进而提前并行拉取数据和代码块，屏蔽等待时间。在对话记忆上，采用 Zustnad + IndexedDB + 本地端侧检索 (Local BM25) 构成的三层缓存架构，消解页面刷新时的历史重载。

### 6. 统一工具接口 (MCP + Skills)
通过 MCP 标准化外部工具接入，通过 Skills 系统实现模块化能力管理。
两者统一为 LangChain Tool 接口，供 Agent 使用。

## 技术架构中的 HMER 支撑

系统的每一层架构设计都内置了 **HMER (Hypothesis-Measure-Experiment-Reflect)** 验证能力的支撑：

1.  **Hypothesis (假设)**：通过 `docs/design/DES-NNN.md` 显式记录架构设计的假设及其预期影响（如：引入推测性加载预期降低 30% TTFT）。
2.  **Measure (度量) —— 遥测体系**：
    *   **Backend**: 基于 `OpenTelemetry` 的分布式追踪，记录 Agent 节点的执行耗时。
    *   **Frontend**: `MonitorService` 实时采集用户交互延迟与流式响应首字时间 (TTFT)。
3.  **Experiment (实验) —— 弹性路由**：
    *   **A/B Testing**: 利用 `LLM Router` 的权重分配实现不同 Prompt 策略或模型的灰度对比。
    *   **Feature Flags**: 代码层级的逻辑开关，支持在不重启服务的情况下动态调整检索策略（如切换向量搜索与图谱搜索）。
4.  **Reflect (反思) —— 实验看板**：
    *   **Architecture Lab**: 在前端专门开辟 `/architecture-lab` 页面，实时可视化 A/B 组的性能差异。
    *   **Back Test**: 支持通过历史 Trace 数据对新算法进行离线回归测试。

## 前端画布与图可视化架构（2026-03）

### 技术分层

- `AntV X6`：结构化流程编排画布（Pipeline Builder 目标主栈）
- `AntV G6`：Agent 协作关系图与知识图谱可视化（Graph 目标主栈）
- `React Flow` / `react-force-graph-2d`：现有存量能力，作为迁移过渡层

### 已落地的 Simple 组件（可复用模板）

- `frontend/src/components/canvas/X6SimpleCanvas.tsx`
- `frontend/src/components/canvas/G6SimpleGraph.tsx`
- `frontend/src/pages/CanvasLabPage.tsx` (`/canvas-lab`)

### 迁移原则

1. 新需求优先复用 `components/canvas/` 里的 AntV 初始化模式。
2. 存量页面按“先页面替换、后交互增强”的方式逐步迁移，避免一次性重构风险。
3. AI 生成前端代码时，涉及流程编排优先选择 X6，涉及关系图优先选择 G6。
