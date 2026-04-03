# REQ-015 — P1 Architecture Resilience (Enrichment & Persistence)

> **Objective**: Improve the semantic depth of ingested data and ensure swarm reliability through persistent agent checkpointing and budget-aware tool design.

---

## 1. Context & Rationale

After the P0 hardening of the execution sandbox and token budget system, the system now requires higher "Intelligence Density" and "Operational Reliability":
1. **Ingestion Quality**: Currently, ingested documents are indexed with raw text/embeddings, lacking semantic metadata like timelines or versioning, which limits complex RAG queries.
2. **Persistence Gap**: Swarm sessions are currently stored in memory. A server restart or crash results in "Cognitive Reset," which is unacceptable for long-running multi-agent tasks.
3. **Tool Optimization**: Skills currently return large volumes of data without token awareness, leading to context window stress even with the new budgeting system.

## 2. Requirements

### 2.1 P1-1: Ingestion 管线 EnrichmentStep (M7.4.1)
- **Node**: Introduce `EnrichmentStep` in the `IngestionOrchestrator` graph.
- **Extraction**:
    - **Temporal Entities**: Extract relative and absolute dates to build a "Knowledge Timeline."
    - **Version Chain**: Identify if a document is an update to an existing record.
    - **Semantic Tags**: Auto-generate at least 3 high-relevance tags per chunk.
    - **Pulse Summary**: Generate a 100-character "Pulse Summary" for quick graph traversal.

### 2.2 P1-2: Agent 状态持久化 (Persistence)
- **Storage**: Move from `MemorySaver` to a persistent `PostgresSaver` or `RedisSaver`.
- **Functionality**:
    - Support `resume` from a `thread_id` even after backend restart.
    - Export/Import swarm states for auditing and debugging.

### 2.3 P1-3: 工具响应 Token 预估 (Budget-Aware Tools)
- **Constraint**: Every core Skill tool must implement basic token estimation for its response.
- **Modes**: Support a `concise=True` flag for tools to return summarized results if the agent is nearing its budget.

## 3. Success Criteria

1. **Neo4j**: New nodes in the knowledge graph must contain `pulse_summary` and `tags` properties.
2. **Recovery**: Killing the backend process during a Swarm run, restarting, and sending a `resume` signal must continue the task from the last successful node.
3. **Budgeting**: A tool call return that would exceed 10K tokens must be auto-summarized if `concise` mode is active.

---

> **Status**: Draft / P1 Phase  
> **Milestone**: M7.4 (Intelligence Density)
