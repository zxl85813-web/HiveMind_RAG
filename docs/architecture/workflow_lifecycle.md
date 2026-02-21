# Workflow Lifecycle & Architecture

本文档详细描述了 HiveMind 后端的核心工作流机制，包括路由、决策、容错、状态管理及日志系统。

## 1. 核心层级架构 (Hierarchy)

系统采用了 **分形 (Fractal)** 架构设计，即“大流程套小流程”，每一层都有独立的状态机和容错机制，互不干扰。

| 层级 | 组件 | 职责 | 状态机管理 | 容错机制 |
|------|------|------|------------|----------|
| **L1 (宏观)** | **BatchJob** | 管理批量任务、全局并发控制 | `JobManager` (LangGraph) | 任务级重试、依赖解锁、状态重放 |
| **L2 (中观)** | **Pipeline** | (Optional) 定义固定流程 (DAG) | `PipelineExecutor` | Stage 级重试、依赖回滚 |
| **L3 (微观)** | **Swarm** | 动态决策、工具调用、多 Agent 协作 | `SwarmOrchestrator` (LangGraph) | 反思循环 (Reflection)、自我修正 |
| **L4 (原子)** | **Agent** | 执行具体指令 (LLM 调用) | `PromptEngine` | Prompt 优化、模型切换 |

---

## 2. 路由与决策 (Routing & Decision)

### 2.1 宏观路由：Pipeline DAG
*   **定义方式**: 静态代码定义 (`PipelineDefinition`)。
*   **对决策**: 基于 **数据依赖 (Data Dependency)**。
    *   例如：只有当 `Artifact A` (提取结果) 和 `Artifact B` (分类结果) 都存在时，才路由到 `RiskCheck` 节点。
*   **代码位置**: `app/batch/pipeline.py` -> `get_execution_order()`

### 2.2 微观路由：Supervisor Agent
*   **定义方式**: 动态 Prompt (`prompts/agents/supervisor.yaml`)。
*   **判决策**: 基于 **语义意图 (Semantic Intent)**。
    *   Supervisor 接收用户输入 + 上下文。
    *   输出结构化决策 JSON：`{ "next_agent": "code_agent", "reasoning": "需计算风险值" }`。
*   **状态机**: LangGraph 的 `ConditionalEdge`。

---

## 3. 错误处理与重试 (Error Handling)

### 3.1 软错误 (Soft Errors) - 质量不达标
*   **处理者**: Swarm 内部的 **Reflection Node**。
*   **机制**: 
    1. Agent 生成结果。
    2. 结果并不直接返回，而是先流向 Reflection Node。
    3. Reflection Agent (LLM) 评估质量。
    4. 如果 `verdict="REVISE"`，带着修改意见退回给原 Agent。
*   **表现**: 用户无感知，只会等待时间稍长，但得到的结果更准确。

### 3.2 硬错误 (Hard Errors) - 崩溃/异常
*   **处理者**: `PipelineExecutor` 和 `BatchController`。
*   **机制**:
    1. 捕获 Python Exception (如 API Timeout, JSON Parse Error)。
    2. 记录错误日志。
    3. **Exponential Backoff**: 等待 $2^n$ 秒后重试。
    4. 若超过 `max_retries`，标记该 Stage 为 `FAILED`，并生成一个类型为 `ERROR` 的 Artifact，中断后续依赖该节点的任务。

---

## 4. 自主学习 (Autonomous Learning)

### 4.1 短期学习 (In-Context Learning)
*   **实现**: 对话历史 (Memory)。
*   **原理**: 在同一个 Swarm Session 中，Supervisor 记得 Agent 之前的错误尝试，不会重蹈覆辙。

### 4.2 长期学习 (Evolutionary Learning) - *Planned*
*   **实现**: `LearningService` + 向量数据库。
*   **流程**:
    1. 任务结束后，系统分析 `Artifact` 中的 `reflection_history`。
    2. 提取“教训” (Key Lessons)，例如：“这个API对日期格式很敏感，必须用 YYYY-MM-DD”。
    3. 存入 Global Knowledge Base。
    4. 下次任何 Agent 启动时，`PromptEngine` 自动检索并注入相关教训到 System Prompt。

---

## 5. 状态机与日志 (State & Logging)

### 5.1 状态可视化
后端维护一棵实时的 **状态树 (State Tree)**，前端通过轮询 `/batch/jobs/{id}` 获取。

```json
{
  "job_id": "job-abc",
  "tasks": [
    {
      "id": "task-1",
      "status": "processing",
      "pipeline_state": {
        "current_stage": "risk_check",
        "completed_stages": ["extract", "classify"],
        "artifacts_produced": 2
      },
      "swarm_state": {
        "current_agent": "rag_agent",
        "reflection_count": 1,
        "last_log": "正在检索法律条款..."
      }
    }
  ]
}
```

### 5.2 Artifact 日志 (Audit Trail)
不同于传统的文本日志，我们将 **中间产物 (Artifacts)** 视为最重要的业务日志。
*   每一个 Artifact 包含：`source_stage`, `confidence`, `data`, `created_at`。
*   这构成了完整的 **证据链**。用户可以追溯：“为什么最后报告说风险高？哦，是因为 `classify` 阶段把它标记为 P2P 借贷合同，置信度 95%。”

---

## 6. 开发指南

*   **添加新流程**: 在 `app/batch/pipelines/` 下定义新的 `PipelineDefinition`。
*   **添加新 Agent**: 
    1. 在 `app/agents/` 注册 Agent 类。
    2. 在 `app/prompts/agents/` 添加 YAML 定义。
*   **调试**: 使用 `logs/app.log` 查看系统日志，使用 API 查看 Artifact 日志。
