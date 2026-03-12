# 🧠 记忆压缩与 Token 预算计算设计 (Memory Compression & Token Budgeting)

> 目标：在保障智能体长期认知连续性的同时，严格控制上下文 Token 的膨胀，防止由于上下文遗忘（Lost in the Middle）、超长响应延迟与 OOM 导致的可用性下降。本设计适用于 ARM-P1 及后续阶段的记忆引擎。

---

## 📅 版本历史

| 版本 | 日期 | 状态 | 说明 |
|------|------|------|------|
| v1.0 | 2026-03-12 | Draft | 初始设想与架构规划 |

---

## 一、核心挑战与痛点

1. **Token 限制爆炸**：随着对话轮次增加以及自动读取的 Role/Personal Memory 的累积，注入 Prompt 的 Token 数量会成指数级攀升。
2. **"Lost in the Middle" 效应**：当注入了庞大的知识图谱 (Neo4j) 上下文与向量块时，LLM 对位于中段的核心上下文更容易出现遗忘。
3. **成本与速度开销**：上下文越长，单次推理及首字响应（TTFT）时间越长，调用成本剧增。

---

## 二、Token 预算基座 (Token Calculation Base)

所有模块的输入和输出都需要具备“可度量”的属性。

### 2.1 引入 `tiktoken` 计算标准
在 `backend/app/core/token_service.py` 内部统一接管 Token 计费与探测：

```python
# 概念示例 (Token 计量层)
import tiktoken

class TokenService:
    @staticmethod
    def count_tokens(text: str, model: str = "gpt-4o") -> int:
        enc = tiktoken.encoding_for_model(model)
        return len(enc.encode(text))
    
    @staticmethod
    def truncate_to_budget(text: str, budget: int, model: str = "gpt-4o") -> str:
        enc = tiktoken.encoding_for_model(model)
        tokens = enc.encode(text)
        if len(tokens) <= budget:
            return text
        return enc.decode(tokens[:budget])
```

### 2.2 定义硬性阶段预算 (Budgets)

以总预算为 32K token 为例，按阶段严格分配空间：

| 载荷区域 | 建议占比 | 示例上限 (32K) | 削减/压缩策略 (若超限) |
|---|---|---|---|
| **System Rules & Security** | 10% | 3,200 | 静态压缩，非必要不删减 |
| **Role & Personal Memory** | 15% | 4,800 | TTL 遗忘（保留最高权重，剔除低频次记忆）|
| **RAG Knowledge Context** | 45% | 14,400 | Contextual Compression / 重排 (Re-ranking) |
| **Swarm Chat History** | 20% | 6,400 | 短期会话滚动折叠 (Sliding Window / Summarization) |
| **Output / Buffer** | 10% | 3,200 | 设置 `max_tokens` 参数兜底 |

---

## 三、记忆的压缩策略设计 (Compression Strategies)

### 3.1 对话级别的短期记忆流压缩 (Chat History Compaction)

当单轮“Chat History”超过预算阈值（如 6,400 tokens）时，由 `Agent` 自主触发，或在 Orchestrator 旁路自动触发压缩节点。

* **滑动窗口清理 (Sliding Window)**：仅保留最近 `N` 轮的完整 Message 日志，老日志仅留取 `AIMessage` 和核心 `User` 提问。
* **分级提炼压缩 (Cascading Summary)**：
  - 调用廉价 / 高速模型（如 Haiku / Flash）对历史进行蒸馏：`"请把这 20 轮对话压缩为包含 3 个核心决策点和 1 句目标总结的短摘要"`。
  - 用摘要对象（`SummaryMessage`）替换原始的长对话链数组，注入原系统栈中。

### 3.2 长期记忆的自动遗忘机制 (Decay Mechanism for Tier-1/Tier-2)

记忆池不能只进不出。Neo4j 与 ChromaDB 中的个人数据需配有“温度”衰减系数机制。

* **时间衰减积分 (Time-based Weight Decay)**：
    * 每次查询/命中记忆库中的数据标签时，提高对应的命中词云节点（`Tag`或`Entity`）的热度值（`hit_count++`）。
    * 定时任务（例如 `Daily Job`）将所有的记忆热度按照系数惩罚（如每天 `decay_rate = 0.95`）。
* **冷数据驱逐 (Cold Storage)**：
    * 提取到 Role/Personal Prompt 里的内容只允许拉取 `Score > Threshold` 的热知识，长尾且无用 (Score 归 0) 的个人摘要被剔除出自动注入池，直到用户明确再搜索。

### 3.3 知识库切片重排与抽取式压缩 (Knowledge Extraction)

这是用于压缩 `RAG Knowledge Context` 数据量最有效的方式。当从 Chroma/Graph 招回的内容过载时：

* **Reranker 去尾**：依据 Cross-Encoder 返回的置信度评分，如置信度断崖式下跌，强制截断长尾切片。
* **基于 LLM 的信息抽取器 (Extract & Inject)**：
    在丢给主模型进行生成前，先过一轮 `ExtractorLayer`：
    `"给定用户的 query，请仅从下面 10 段冗长的长文中摘录 150 字最相关的事实片段，如果没有相关数据请回复空。"`
    以此将 15,000 token 缩小至 1,000 token 的纯金块。

### 3.4 分层分类与渐进披露查询 (Layered Categorization & Progressive Disclosure)

记忆体系不仅需要总量控制，更需要结构化的分类，以支持“渐进披露”的设计核心理念。系统在面临宽泛的问题时，不应一股脑将极细颗粒度的信息吐出，而应经过路由分发或依赖引导来逐层深入：

* **核心索引层 (Core Index - Tier 1)**：存储知识库与个人的 `Summary`（总结）、`Topics` 和全局分类标签。当查询意图不明朗或视野极宽时，默认仅检索这一层，并回应一个概述性的“大纲记忆”。
* **实体关系图谱层 (Graph Context - Tier 2)**：当用户针对某个具体“人、事、物”展开追问，触发对应的实体路由，抽出相关的关联关系而非原文，为问题提供逻辑解答辅助。
* **事实载体层 (Vector/Raw Chunks - Tier 3)**：只有当系统或用户确认需要查看特定“代码块”、“原始合同条目”时，才进行极细颗粒度的向量召回，做到**按需加载 (On-Demand Loading)**。
* **多跳路由机制**：赋予 Agent 探索性查询的机制（如工具 `fetch_deep_memory`），先展现 Tier 1/2 的结果，如果 LLM 判断信息不够，再发出一轮深加工请求捞取 Tier 3 数据，以此拦截非必要的 Token 开销。

---

## 四、技术实施路径 (TODO)

### 阶段 1 (P1): 基础 Token 服务与拦截
- [ ] 开发 `app.core.token_service.py` 工具链，集成 `tiktoken`。
- [ ] 改造 `chat_service.py` 或编排网关：限制输入 Prompt 不得超过硬件上限，进行粗暴截断 `chat_history_window_size`。

### 阶段 2 (P2): 对话流式摘要
- [ ] 增加 `ContextCompactionStep`，用于感知并自动折叠超过特定 Token 的聊天链为 System Message 摘要块。
- [ ] 挂载基于 Redis/KV 的 Semantic Caching 时，联动记录 Tokens 消费账本（挂载于全局 Tracing 中）。

### 阶段 3 (P3): 高级记忆衰减
- [ ] 依托 `MemoryService` (ARM-P1-2)，定期扫描用户的 `PersonalMemory`，使用 AI 读取后按照“最近关注偏好”洗一次牌。
- [ ] `Vector DB` / `Graph` RAG 端点接入基于 LLM 的提取器（Extractor）。

---

## 五、结论边界
Token 与 Memory 的计算应当独立于权限核查（ARM-P0）。压缩发生在 “权限筛选完成后的数据组装侧”。丢失一些长缓存和历史虽然会影响记忆效果，但在工程上保障系统永远不因 Payload 超载而崩溃。
