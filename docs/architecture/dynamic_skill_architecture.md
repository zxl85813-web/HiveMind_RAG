# Architecture: Dynamic Skill Orchestration with Production Safeguards&nbsp;

本文档展示了融合 **LangGraph (动态编排)**、**Skill-Based Worker (动态执行)** 以及 **Production Safeguards (生产级保障)** 的完整架构。

## 1. 宏观架构图 (High-Level Architecture)

```mermaid
graph TB
    %% --- 入口与缓冲 ---
    User((User)) -->|POST /batch| API[API Gateway]
    API -->|1. Enqueue Job| Redis[[Redis Queue\nAsync Buffer]]
    
    %% --- 编排层 (Orchestrator) ---
    subgraph "Control Plane (LangGraph Orchestrator)"
        direction TB
        JobManager[Job Manager\n(LangGraph State Machine)]
        Redis -->|2. Consume| JobManager
        
        DB[(Postgres\nCheckpointer)]
        JobManager <-->|3. Load/Save State| DB
        
        Human[Human Reviewer]
        JobManager -.->|4. Request Approval\n(If Low Confidence)| Human
        Human -.->|5. Resume/Edit| JobManager
    end

    %% --- 动态资源库 ---
    subgraph "Skill Registry (Stateless Knowledge)"
        direction TB
        S_Resume[Skill: Resume Analysis]
        S_DAO[Skill: DAO Cleaning]
        S_General[Skill: General Processing]
    end

    %% --- 执行层 (Execution Plane) ---
    subgraph "Worker Pool (Universal Agents)"
        direction TB
        Worker[Universal Worker Agent\n(LLM Instance)]
        Cache[Semantic Cache\n(Redis/VectorDB)]
        
        JobManager -->|6. Dispatch Task| Worker
        Worker <-->|7. Check Cache| Cache
    end

    %% --- 安全与执行环境 ---
    subgraph "Secure Sandbox & MCP Hub"
        direction TB
        MCP_File[MCP: FileSystem]
        MCP_DB[MCP: Database]
        
        Sandbox[E2B / Firecracker\nIsolated MicroVM]
        MCP_Code[MCP: Python Interpreter]
        
        Worker -->|8. Read/Write| MCP_File
        Worker -->|9. Query| MCP_DB
        Worker -->|10. Execute Code| Sandbox
        
        Sandbox -.->|Run Unsafe Code| MCP_Code
    end

    %% --- 观测与反馈 ---
    Worker -->|11. Trace & Log| TraceHub[V3 Trace Hub\nRedis + PostgreSQL]
    JobManager -->|12. Final Report| Report[Artifact Store]
```

## 2. 详细交互时序图 (Detailed Interaction Flow with Safeguards)

此图展示了一个包含 **人工审核 (HITL)** 和 **安全沙箱** 的完整任务流转。

```mermaid
sequenceDiagram
    participant User
    participant Q as Redis Queue
    participant Orch as LangGraph (Orchestrator)
    participant DB as Postgres (State)
    participant Worker as Universal Worker
    participant Box as Secure Sandbox
    participant Human as Human Admin

    User->>API: Upload Excel (Resume + DAO)
    API->>Q: Push Job ID: 101
    
    %% --- 异步消费与初始化 ---
    Orch->>Q: Pop Job 101
    Orch->>DB: Create Job State (START)
    
    %% --- 预处理与分发 ---
    Orch->>Worker: Task: Preprocess & Plan
    Worker->>Orch: Result: Plan = [Task A: Resume, Task B: DAO]
    Orch->>DB: Save Checkpoint (PLANNED)
    
    %% --- 并行执行: Task A (Resume) ---
    rect rgb(240, 248, 255)
        Orch->>Worker: Dispatch Task A (Skill: Resume)
        activate Worker
        Worker->>Worker: Load Skill & Tools
        Worker->>Worker: Analyze Candidates
        
        %% 触发人工审核 (HITL)
        alt Low Confidence (< 0.6)
            Worker-->>Orch: Suspend (Reason: Low Confidence)
            deactivate Worker
            Orch->>DB: Save State (SUSPENDED)
            Orch->>Human: Notify "Review Needed for Task A"
            
            Human->>Orch: Approve / Edit Inputs
            Orch->>DB: Update State & Resume
            Orch->>Worker: Resume Task A
            activate Worker
        end
        
        Worker-->>Orch: Result A (Verified)
        deactivate Worker
    end

    %% --- 并行执行: Task B (DAO) ---
    rect rgb(255, 240, 245)
        Orch->>Worker: Dispatch Task B (Skill: DAO)
        activate Worker
        Worker->>Box: Execute Python Cleaning Script
        Box-->>Worker: Return Cleaned Data
        Worker-->>Orch: Result B
        deactivate Worker
    end

    %% --- 聚合与完成 ---
    Orch->>Orch: Aggregate Results (A + B)
    Orch->>DB: Save State (COMPLETED)
    Orch-->>User: Notification: Job Done
```

## 3. 核心设计升级点

### 3.1 生产级保障 (Safeguards)
*   **Async Buffer (Redis Queue)**: 只有 `Orchestrator` 准备好后才会从队列取任务。防止瞬间流量打垮 LLM 或数据库。
*   **Job Checkpointer (Postgres)**: 
    *   **断点续传**: 如果服务器在 `Task A` 执行时重启，重启后 `Orchestrator` 会从 DB 读取状态，发现 `Task A` 未完成，自动重新调度，而不会重跑预处理。
    *   **状态回滚**: 如果人工发现跑错了，可以回滚到上一个 Checkpoint 修改参数。

### 3.2 人机回环 (HITL)
*   **中断机制**: Worker 发现异常（如置信度低、敏感词触发）时，主动挂起任务。
*   **人工介入**: 管理员介入修改中间变量（State），然后命令 `Orchestrator` 继续运行。这保证了高风险场景的安全性。

### 3.3 安全沙箱 (Sandboxing)
*   **隔离执行**: 任何 Python 代码执行都不在 Worker 容器内，而是在 **E2B** 或 **Firecracker MicroVM** 中。
*   **资源限制**: 沙箱有严格的 CPU/内存限制和网络白名单。即使 LLM 生成了 `while True:` 恶意代码，也只会卡死沙箱，主进程不受影响。

### 3.4 语义缓存 (Semantic Caching)
*   **节省成本**: Worker 在执行昂贵的 LLM 推理前，先查 `Semantic Cache`。
*   **秒级响应**: 如果同样的 Excel 昨天有人传过，今天直接返回结果，耗时 0 秒，成本 0 元。
