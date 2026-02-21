# Multi-Tier Hybrid Memory Architecture (RAG)

## 背景 (Background)
传统的扁平化 RAG（将所有文本切块扔进向量数据库，提问时直接做 K-NN 检索）存在严重的上下文污染、Token 浪费和检索准确度问题（“大海捞针”）。为了打造媲美顶级 Agent 的记忆引擎，HiveMind 引入了 **多层渐进式记忆架构 (Multi-Tier Memory Architecture)**。

我们的目标是模拟人类回忆的过程：**先快速回忆起地标/索引 (Radar)，再关联场景网络 (Graph)，最后才去翻阅具体的字典 (Detailed Vector)**。

---

## 架构概览 (Architecture Overview)

系统将记忆分为三个层次 (Tiers)，递进式地为 Agent 提供上下文：

### Tier 1: 摘要/索引层 (Abstract Layer) - 高速雷达
*   **定位**: 充当 Agent 的“热记忆路由” (Hot Memory Routing) 和雷达。
*   **存储引擎**: **纯内存 (In-Memory)** -> `InMemoryAbstractIndex` (未来可演进为 Redis)。
*   **内容形态**: 极其精简的 JSON 元数据（`doc_id`, `title`, `tags`, `type`, `date`）。
*   **速度**: < 1 毫秒 ($O(1)$ 通过 Set 交集计算)。
*   **作用**: Agent 思考问题前，第一眼先扫过这里。例如：瞬间定位到“今天”、“关于 PostgreSQL”、“Bug”的所有线索。不返回大段文本，只返回高度浓缩的结论。

### Tier 2: 概述/关系层 (Overview Layer) - 全局视角 (规划中)
*   **定位**: 记忆的网络和骨架。
*   **存储引擎**: **Neo4j** 图数据库。
*   **内容形态**: 实体 (Entities) 和关系 (Edges)，例如：`(Bug) -[发生在]-> (Auth 模块)`。
*   **作用**: 当 Agent 通过 Tier 1 拿到几个线索（ID）后，可以在 Tier 2 爬取与这些线索相关联的其他代码模块和历史事件，获得全局视角，避免“盲人摸象”。

### Tier 3: 详情层 (Details Layer) - 深度潜水
*   **定位**: 承载具体的原生知识和长文本。
*   **存储引擎**: **Elasticsearch** (Hybrid Search: 向量 + BM25) 或 ChromaDB。
*   **内容形态**: 切片的 Chunk 文本、完整的代码块、原始日志 (`page_content`, `embedding`)。
*   **作用**: 当 Agent 明确知道要看什么（通过前面两层拿到了确切的范围或 ID）时，对目标进行硬性过滤检索，提取原始代码用于生成最终回答。

---

## 写入流 (Ingestion Pipeline)

当新消息或文档进入系统 (例如 `MemoryService.add_memory`) 时火控分离：
1.  **慢速轨道**: 完整文本进行 Embedding，写入 Vector DB (Tier 3)。
2.  **极速轨道**: 启动异步任务 (`asyncio.create_task`)，调用一个小参数量大模型（LLM Fast Extraction），提取出 `title` 和 `tags`，立刻塞进内存倒排索引 (`InMemoryAbstractIndex`) 中。

## 读取流 (Retrieval Pipeline: ChatService)

在日常对话的 `chat_stream` 中：
1.  **Radar 阶段**: LLM 瞬间从 User Query 提取 Keywords (如 ["数据库", "报错"])。
2.  **Hit (命中)**: 内存查询 `abstract_index.route_query(tags=["数据库"])`，返回雷达信号。
3.  **Deep Search 阶段**: 无论雷达是否击中，去 Vector DB 抽调最底层的几条 Context 兜底。
4.  **最终组装**: Context 包含了 `--- HOT MEMORY (Abstracts) ---` 和 `--- DEEP CONTEXT ---`，一起送给 LLM 生成完美回答。

---

## 代码分布
*   **核心索引**: `backend/app/services/memory/tier/abstract_index.py`
*   **写入入口**: `backend/app/services/memory/memory_service.py` -> `_extract_and_index_abstract`
*   **读取拦截**: `backend/app/services/chat_service.py` -> `chat_stream`
*   **Agent Tool**: `backend/app/skills/generation/tools.py` -> `search_abstract_memory`
