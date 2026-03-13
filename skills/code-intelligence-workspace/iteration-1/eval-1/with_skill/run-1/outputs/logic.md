### 逻辑解构：Memory Distillation 并发处理

在 `memory_service.py` 中，并发任务通过 `asyncio.Semaphore(2)` 进行流量控制，并配合 `Redis Lock` 确保同一用户不会同时触发两个压缩任务。

#### 任务流可视化：

```mermaid
sequenceDiagram
    participant App as API Layer
    participant Svc as MemoryService
    participant Sem as Semaphore (Limit:2)
    participant DB as VectorStore

    App->>Svc: Trigger Distillation
    Svc->>Sem: Acquire Slot
    alt Slot Available
        Sem-->>Svc: Granted
        Svc->>DB: Compress & Re-index
        DB-->>Svc: Success
        Svc->>Sem: Release Slot
    else Busy
        Svc-->>App: Task Queued/Rate Limited
    end
```

**关键路径**：
- **资源限制**：通过信号量防止内存溢出。
- **原子性**：利用数据库事务保证压缩前后的数据一致。
