---
name: rag_search
description: "知识库检索与问答 — 从向量数据库中检索相关文档并生成带引用的回答。当用户询问需要从知识库获取信息的问题时使用此 Skill，包括：(1) 语义搜索与相似度检索 (2) 多知识库交叉查询 (3) 带来源引用的答案生成 (4) 文档上下文扩展与精排 (5) 基于元数据的过滤检索。触发关键词：知识库搜索、文档查找、RAG、检索增强、引用来源。"
---

# RAG Search Skill

## Overview

基于向量相似度的知识库检索与答案生成系统。核心原则：**检索质量决定回答质量**。

## Quick Reference

| 任务 | 方法 |
|------|------|
| 基础语义搜索 | `search_knowledge_base` — 单库向量检索 |
| 多库联合检索 | `multi_search` — 跨多个知识库并行检索 |
| 上下文扩展 | `get_document_context` — 获取检索结果前后文 |
| 混合检索 | `hybrid_search` — 向量 + 关键词双路召回 |
| 重排序 | `rerank_results` — 对召回结果精排 |

---

## 检索策略

### 1. 查询预处理

**始终对用户查询进行预处理再检索。** 直接用原始查询检索往往召回质量差。

```python
# ❌ 错误 — 直接用原始查询
results = await search(query="这个功能怎么用？")

# ✅ 正确 — 查询重写 + 补充上下文
rewritten = await rewrite_query(
    original="这个功能怎么用？",
    context=conversation_history,  # 利用对话上下文消歧
)
# rewritten → "HiveMind 平台知识库文档上传功能的使用方法和步骤"
results = await search(query=rewritten)
```

**查询重写策略：**
- **消歧义**：利用对话上下文补全代词和模糊引用
- **关键词扩展**：为专业术语添加同义词（如 "向量数据库" → "vector store, embedding database"）
- **查询分解**：复杂问题拆成多个子查询分别检索，再合并结果
- **HyDE（假设性文档嵌入）**：先让 LLM 生成一个假设性答案，用它作为检索查询

### 2. 检索参数调优

```python
search_params = {
    "top_k": 10,              # 召回数量（建议 10-20，过多增加噪声）
    "score_threshold": 0.7,    # 相似度阈值（低于此分数的结果丢弃）
    "metadata_filter": {       # 元数据过滤（缩小搜索范围）
        "source_type": "official_doc",
        "language": "zh",
    },
}
```

**参数经验值：**

| 场景 | top_k | threshold | 说明 |
|------|-------|-----------|------|
| 精确问答 | 5-8 | 0.8 | 高精度、低召回 |
| 知识探索 | 15-20 | 0.6 | 高召回、容忍噪声 |
| 摘要生成 | 10-15 | 0.7 | 平衡精度与覆盖 |
| 事实核查 | 5 | 0.85 | 只要最相关的 |

### 3. 混合检索（推荐）

单纯的向量检索在关键词精确匹配场景下效果差。混合检索结合向量语义和关键词匹配的优势。

```python
# 双路召回
vector_results = await vector_search(query, top_k=10)
keyword_results = await keyword_search(query, top_k=10)

# 融合排序（RRF = Reciprocal Rank Fusion）
merged = reciprocal_rank_fusion(
    [vector_results, keyword_results],
    k=60,  # RRF 常量，通常取 60
)

# 精排（可选，用 Cross-Encoder 或 LLM 打分）
final = await rerank(merged[:20], query, top_k=5)
```

### 4. 多知识库检索

当用户问题可能涉及多个知识库时，并行检索并合并结果。

```python
# 并行检索多个知识库
kb_ids = await identify_relevant_kbs(query, available_kbs)
tasks = [search_kb(kb_id, query, top_k=5) for kb_id in kb_ids]
all_results = await asyncio.gather(*tasks)

# 合并 + 去重（基于文档 ID）
merged = deduplicate(flatten(all_results))

# 按相关性重排
final = sorted(merged, key=lambda r: r.score, reverse=True)[:10]
```

---

## 上下文组装

### Chunk 上下文扩展

检索返回的 chunk 可能断句不完整，需要扩展前后文。

```python
# 获取 chunk 周围的上下文
expanded = await get_document_context(
    chunk_id=result.chunk_id,
    window=2,  # 前后各扩展 2 个 chunk
)
```

### Context Window 管理

**关键原则：不要把所有检索结果都塞进 context。**

```python
# 计算 token 预算
total_budget = model_max_tokens - output_reserve - system_prompt_tokens
context_budget = int(total_budget * 0.6)  # 60% 给检索上下文

# 按相关性从高到低填充，直到预算用完
context_chunks = []
used_tokens = 0
for result in ranked_results:
    chunk_tokens = count_tokens(result.content)
    if used_tokens + chunk_tokens > context_budget:
        break
    context_chunks.append(result)
    used_tokens += chunk_tokens
```

---

## 答案生成规范

### 引用格式

**所有基于知识库的回答必须包含来源引用。**

```markdown
## 回答

根据知识库中的信息，HiveMind 平台支持以下文件格式 [1][2]：
- PDF 文档（含 OCR 扫描件）
- Word 文档（.docx）
- Markdown 文件

### 来源
[1] 《产品使用手册》第 3.2 节 — 文件上传说明 (相关度: 0.92)
[2] 《FAQ 常见问题》— 支持的文件格式 (相关度: 0.87)
```

### 无结果处理

当知识库中未找到相关信息时：

```markdown
❌ 错误：编造答案或使用通用知识回答
✅ 正确：

"在当前知识库中未找到与您问题直接相关的信息。

**建议：**
1. 尝试使用不同的关键词重新提问
2. 检查是否需要上传相关文档到知识库
3. 如需实时信息，可切换到网络搜索模式"
```

### 置信度评估

为每个回答生成置信度标签：

| 置信度 | 条件 | 展示 |
|--------|------|------|
| 🟢 高 | top-1 相关度 ≥ 0.85，多个来源互证 | 直接回答 |
| 🟡 中 | top-1 相关度 0.7-0.85，部分来源支撑 | 回答 + 标注"仅供参考" |
| 🔴 低 | top-1 相关度 < 0.7，来源单一或矛盾 | 明确告知信息不充分 |

---

## 常见陷阱

- **不要跳过查询重写** — 原始查询直接检索的召回质量通常较差
- **不要忽略 score threshold** — 低分结果引入噪声，会误导 LLM
- **不要在无结果时编造答案** — 必须明确告知用户知识库中无相关信息
- **不要一次检索过多 chunk** — top_k > 20 时性能下降且噪声增加
- **不要忽略元数据过滤** — 当用户明确提到文档类型或来源时，用元数据缩小范围

---

## Tools

- `search_knowledge_base`: 单库语义检索
- `multi_search`: 多知识库并行检索
- `hybrid_search`: 向量 + 关键词混合检索
- `get_document_context`: 扩展 chunk 上下文
- `rerank_results`: 检索结果精排
- `cite_sources`: 格式化来源引用
