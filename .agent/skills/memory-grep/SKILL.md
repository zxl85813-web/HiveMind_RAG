---
name: memory-grep
description: 传统检索引擎集成：利用 SmartGrep (BM25 + Fuzzy) 召回向量匹配难以处理的精确事实。当用户询问特定错误 ID、唯一代号、或特定的代码 API 细节时触发。
---

# 🧠 Memory-Grep Skill

## 核心理念

> 当向量搜索失效时，回归传统关键词的力量。

**向量检索的弱点**（需要使用此 Skill 的场景）：
- **唯一代号**：如 `REQ-001`、`BUG-004` 等，向量容易召回语义相近但不相关的文档。
- **特定术语**：如 `ClawRouter`、`PWA-Offline` 等，向量由于 embedding 的稀释，召回权重低。
- **错误堆栈**：如特定的 `Traceback` 信息，向量无法通过局部匹配精确定位。
- **配置文件路径**：如 `/etc/nginx/conf.d/` 等。

---

## 🛠️ 工作原理：传统检索主线

此 Skill 主要依赖后端 `SmartGrepService` 和 `MemoryService` 的 `auto` 模式：

1.  **BM25 (Best Match 25)**：权重化关键词检索，对出现频率低但重要的词（如专有名词）赋予高分。
2.  **Fuzzy Trigram**：容错检索。即使你查询时有拼写错误（如把 `PostgreSQL` 写成 `Postgre`），也能召回。
3.  **零成本同义词**：内置 14 个技术分类，搜“数据库”自动关联“db/mysql/postgres”，无需消耗 Token 调用 LLM。

---

## 🧭 执行指南

### 1. 识别场景
如果你（Agent）在上下文中看到 `--- DEEP MEMORY (Tier-3 Vector) ---` 召回的内容与用户的核心实体完全不符，你应意识到**语义漂移**。

### 2. 利用检索证据
在 `get_context` 召回的上下文中，请重点观察：
`--- LOG EVIDENCE (SmartGrep) ---` 区块。
- `[bm25]` 标记：表示**词根绝对匹配**（硬核事实）。
- `[fuzzy]` 标记：表示**高度相似匹配**（可能含拼写纠正）。

### 3. 输出策略
在最终回答中，如果信息来自 `SmartGrep`，请优先信任其精确性。例如：
- ❌ “系统提到了一些关于数据库优化的内容。”
- ✅ “根据 SmartGrep 的日志证据，在 `2026-03-18.md` 中记录了针对 `PostgreSQL` 的 `Index creation` 决策。”

---

## 🔗 协同关系
- **输入**：`MemoryService.get_context(query)` 自动触发。
- **决策层**：`memory_governance_service` 评估密度。
- **互补**：作为 `Deep Vector` (Tier-3) 的高性能并行分支。
