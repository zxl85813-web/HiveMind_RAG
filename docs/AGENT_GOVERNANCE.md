# 🧭 Agent 治理 — 蜂群的指挥系统

> 蜂群不需要一个中央控制器来告诉每只蜜蜂做什么。
> 但它需要一套隐性的信号系统——谁去采蜜，谁留守，谁负责品控。
> HiveMind 的 Agent 治理，正是这套信号系统的显式化实现。

---

## 架构概览

HiveMind 的 Agent 层由三类角色构成：

| 角色 | 对应 Agent | 职责 |
|:---|:---|:---|
| **蜂后（意图识别）** | `Supervisor Agent` | 解读用户意图，路由到正确的 Worker |
| **工蜂（专项执行）** | `RAG / Code / Web Agent` | 执行具体任务：检索、生成代码、联网搜索 |
| **品控蜂（质量审核）** | `Reflection Agent` | 评审 Worker 输出质量，决定通过或打回重做 |

---

## Supervisor — 意图路由与任务分发

`Supervisor` 是每次对话的入口节点。它的职责不是回答问题，而是**理解问题的性质**，然后将任务交给最合适的 Worker。

### 路由逻辑

```
用户输入
  │
  ├─ Fast Path 关键字检测（直接回答，无需 RAG，避免幻觉）
  │
  └─ LLM 路由决策
       ├─ "需要查知识库" → RAG Agent
       ├─ "需要写/解释代码" → Code Agent
       └─ "需要联网" → Web Agent
```

**Fast Path** 是一个重要的设计决策：对于明确无需检索的问题（如"你是谁"、"今天几号"），Supervisor 直接拦截并回答，避免无谓的检索开销和潜在的幻觉注入。

### 推测式检索（Speculative Retrieval）

Supervisor 在路由决策的**同时**异步发起 RAG 检索（`asyncio.gather`）。如果路由决策结果确实是 RAG，则直接使用已预取的结果，显著降低端到端延迟。

---

## Reflection — 自省纠错机制

Worker Agent 完成草稿后，不会直接输出给用户，而是先经过 `Reflection Agent` 的质量评审：

```
Worker Agent 输出草稿
        │
  Reflection Agent 评审
        │
  ┌─────┴─────┐
  │           │
APPROVE     REVISE (附修改意见)
  │           │
输出终稿    打回 Worker 重做（循环上限 N 次）
```

Reflection 的评审维度包括：
- **事实性**：答案是否与检索到的上下文一致
- **完整性**：是否遗漏了关键信息
- **格式**：输出结构是否符合要求

---

## LangGraph StateGraph — Agent 的骨架

所有 Agent 行为建立在 **LangGraph StateGraph** 之上，这带来几个关键能力：

- **状态持久化**：对话状态可落库，支持跨请求续接
- **断点续传**：长任务中断后可从检查点恢复
- **可观测性**：每个节点的输入/输出均可追踪，Trace 面板实时展示

### Agent DAG 可视化

前端 Agents 页面提供实时的 DAG 可视化，展示当前对话中各 Agent 节点的执行状态、耗时和数据流向。每个节点使用颜色标注状态：

| 颜色 | 含义 |
|:---|:---|
| 🔵 蓝色 | 等待中 |
| 🟡 黄色 | 执行中 |
| 🟢 绿色 | 已完成 |
| 🔴 红色 | 失败 |

---

## 代码位置索引

| 组件 | 路径 |
|:---|:---|
| Supervisor 节点 | `backend/app/agents/agentic_search.py` |
| Agent Prompt 模板 | `backend/app/prompts/agents/supervisor.yaml` |
| LLM Gateway | `backend/app/core/llm.py` |
| Agent 工具集 | `backend/app/agents/tools.py` |
| Prompt 渲染引擎 | `backend/app/prompts/engine.py` |
| DAG 可视化前端 | `frontend/src/pages/Agents/` |

---

## 相关文档

- [← 返回 README](../README.md)
- [🍯 数据治理：知识酿造流程](DATA_GOVERNANCE.md)
- [🏭 开发治理：生产规范体系](DEV_GOVERNANCE.md)
