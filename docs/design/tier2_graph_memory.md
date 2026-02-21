# Tier-2: Overview Layer (Graph Memory)

## 1. 背景 (Background)
在 “多层渐进式记忆架构” 中，Tier-1 (Abstract Index) 解决了“极速定位线索”的问题，Tier-3 (Vector DB) 解决了“精确查阅细节”的问题。然而，当线索数量庞大或者线索之间存在隐式关联时，传统的搜索机制就失效了。
例如：Agent 知道出了一个 `DatabaseConnectionError`，但它不知道这个错误通常是哪个 `Service` 调用的。
**Tier-2 (Overview Layer)** 的引入，旨在利用图数据库 (Neo4j) **“由点连成线，由线交织成网”**，给 Agent 提供全局的网络结构作为上下文。

---

## 2. 核心职责 (Core Responsibilities)
1. **实体与关系抽取 (Graph Extraction)**: 当一段文本（对话、日志、设计文档）入库时，后台异步调用 LLM 将其中的核心要素抽取为 `Nodes (Entities)` 和 `Edges (Relations)`。
2. **图谱沉淀 (Graph Storage)**: 利用的 `Neo4jStore` (位于 `app/core/graph_store.py`)，将结构化的知识写入 Neo4j 数据库。相同实体应当合并 (MERGE)，关系应当积累。
3. **关系跳跃检索 (Graph Retrieval - Neighborhood)**: 当 `ChatService` 启动检索，并且通过 Tier-1 Radar 命中了一些关键字 (Tags/Entities) 时，Tier-2 会向 Neo4j 查询这些实体的“一阶/二阶邻居”，从而把隐式上下文“顺藤摸瓜”地拉取出来交还给 Agent。

---

## 3. 系统设计规范 (System Design Guidelines)

### 3.1 实体抽取大模型 Schema (LLM Schema)
为了保证结构化，大模型 (`LLMService.chat_complete` json_mode) 抽取出的返回格式必须为：
```json
{
  "nodes": [
    {"id": "User_Alice", "label": "Person", "name": "Alice"},
    {"id": "DB_Postgres", "label": "Technology", "name": "Postgres"}
  ],
  "edges": [
    {"source": "User_Alice", "target": "DB_Postgres", "type": "USES", "description": "querying data"}
  ]
}
```

### 3.2 提取器接口 (GraphIndex)
我们需要在 `app/services/memory/tier/graph_index.py` 中建立一个 `GraphIndex` 类，包含：
* `extract_and_store(doc_id: str, content: str) -> None`: 异步调用 LLM 提取 JSON，并通过 `get_graph_store().import_subgraph(nodes, edges)` 写入图库。
* `get_neighborhood(entity_names: List[str], depth: int = 1) -> List[str]`: 输入实体列表，执行 Cypher 查询找出这组实体的关联网，然后翻译成自然语言描述返回。如：`"(Alice) -> [USES] -> (Postgres)"`。

### 3.3 容错设计 (Fault Tolerance)
因为 Neo4j 属于重型组件，在开发/测试环境中可能未安装。
* **隔离策略**: `Neo4jStore` 本身带有 `NEO4J_AVAILABLE` 判断。如果 `driver` 为 `None`，`extract_and_store` 和 `get_neighborhood` 应当“静默退出（或返回空）”，绝对不能阻塞主业务 (`ChatService`)。
* **LLM 容错**: 抽取大模型偶尔返回的 JSON 不合法时，需要 `try-except` 包裹，并在报错时 `logger.warning` 即可。

---

## 4. 读写流集成 (Integration Pipeline)

### 写入流 (Write) -> `MemoryService`
在 `MemoryService.add_memory` 中：
1. 依然触发 `_extract_and_index_abstract` (Tier 1)。
2. 新增一个 `asyncio.create_task`：`graph_index.extract_and_store(doc_id, content)` (Tier 2)。

### 读取流 (Read) -> `chat_service.py`
在 `chat_service.py` 里的 `chat_stream` 阶段 1 (Radar) 之后：
如果我们从 Radar 拿到了 Tags（这些 tag 其实也是一种 Entity），我们会将它们送入 Tier-2：
`neighbor_info = graph_index.get_neighborhood(tags)`
如果返回了内容，将这些图谱关系添加到上下文中 `--- GLOBAL CONTEXT (Graph) ---` 中。
