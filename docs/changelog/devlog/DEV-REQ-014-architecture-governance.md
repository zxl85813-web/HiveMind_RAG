# DEV-REQ-014: 系统架构韧性治理与大模型智能路由 (Architecture Governance & LLM Routing)

| 字段 | 值 |
|------|------|
| **关联需求** | REQ-012 (Code Vault), Phase 5 (服务治理), Phase 6 (前端韧性) |
| **开始时间** | 2026-03-08 15:00 |
| **状态** | 🚧 进行中 |

## 背景
为系统引入 **ClawRouter** 理念的 Agent-Native 大模型智能路由、熔断机制，实现 CQRS 架构分离并全面强化前端的交互与渲染韧性。涵盖从网络、数据库分离到 React 状态树的抗抖动加固。

## 任务分解

| # | 子任务 | 文件/模块 | 状态 | 耗时 |
|---|--------|------|------|------|
| 1 | **定义 LLM Router 引擎机制** | `backend/app/agents/llm_router.py` | ⬜ | - |
| 2 | **集成熔断与 Fallback** | `backend/app/agents/llm_router.py` | ⬜ | - |
| 3 | **适配 Agent 调度层 (Swarm)** | `backend/app/agents/swarm.py` | ⬜ | - |
| 4 | **应用读写分离与 CQRS 设计** | `backend/app/services/indexing.py` | ⬜ | - |
| 5 | **独立部署后台 Worker 队列** | `backend/app/worker.py` | ⬜ | - |
| 6 | **开发 CodeVault AST 提取器** | `backend/app/plugins/code_parser.py` | ⬜ | - |
| 7 | **实现 AI 正向星标飞轮打赏** | `backend/app/services/chat_service.py` | ⬜ | - |
| 8 | **前端：通用 Error Boundaries** | `frontend/src/components/common/ErrorBoundary.tsx` | ⬜ | - |
| 9 | **前端：ForceGraph 防抖动优化** | `frontend/src/pages/KnowledgeDetail.tsx` | ⬜ | - |
| 10| **前端：ChatPanel 状态树切分** | `frontend/src/components/chat/ChatPanel.tsx` | ⬜ | - |
| 11| **全链路集成与压测联调** | - | ⬜ | - |

## 开发日志

### Step 1: 定义 LLM Router 引擎机制
**时间**: 待定
**操作**: 将基于 15 个维度（Token 用量、任务复杂度、当前模型延迟）计算模型得分，并支持 `Eco` / `Premium` Profile 分流。
**决策**: 参考 ClawRouter 模式降低 92% 空转成本。
**问题**: 暂无

### Step 2: 集成大模型熔断器 (Circuit Breaker)
**时间**: 待定
**操作**: 当高可用商业模型（如 Anthropic/OpenAI）连续超时或被 Rate Limit 时，自动降级切换至端侧模型（如 GLM-4-flash/Qwen）。
**决策**: 追求 99.99% 的对话存活率，避免 API 宕机导致产品僵死。
**问题**: 暂无

### Step 3: 前端韧性防抖加固
**时间**: 待定
**操作**: 抽离重度的图谱渲染与高频的 SSE 对话数据流，采用 Zustand 和 Error Boundary 从根源隔绝渲染。
**决策**: 保障用户体验流畅，绝不允许白屏现象。
**问题**: 暂无

## 总结
**完成时间**: -
**实际耗时**: -
**经验教训**: -
