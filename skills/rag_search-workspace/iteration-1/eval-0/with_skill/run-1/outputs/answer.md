基于知识库信息，以下是‘分层记忆’架构与标准‘向量检索’在设计上的优先级差异对比：

### 1. 检索深度与召回策略 [1]
- **向量检索 (Baseline)**：通常仅进行单一维度的语义相似度匹配。
- **分层记忆 (Layered)**：采用 Working -> Episodic -> Semantic 的三层检索。优先级上，当前会话的工作记忆（Working Memory）具有最高优先级，确保对话的连贯性 [1]。

### 2. 时效性与持久化 [2]
- **向量检索**：通常是静态库检索。
- **分层记忆**：强调“渐进式归纳”。对话结束后的情景记忆（Episodic）会被实时打分并定期蒸馏入语义库 [2]。

**来源列表**：
[1] `docs/architecture/memory_compression_design.md` - 记忆层级定义部分
[2] `backend/app/services/memory/memory_service.py` - 记忆归纳流水线注释
