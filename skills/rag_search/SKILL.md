---
name: rag_search
description: "知识库检索与引用。用于：文档问答、语义搜索、跨库查询、带来源引用的回答。当用户提及搜索、查找、根据文档、知识库时触发。"
---

# RAG Search Skill

## ⚡ 快速参考 (Quick Reference)

三步必须执行：**Analyze → Retrieve → Cite**

| 步骤 | 命令 / 工具 | 强制 |
|------|-------------|------|
| 1. 查询增强 | `python skills/rag_search/scripts/rag_ops.py analyze --query "<问题>"` | ✅ |
| 2. 知识检索 | 调用 `search_knowledge_base`（用 expanded_queries 中每条查询） | ✅ |
| 3. 引用格式化 | `python skills/rag_search/scripts/rag_ops.py cite --results "<JSON>"` | ✅ |

> **零容忍规则**：检索结果为空 → 必须回答"在当前知识库中未找到相关信息"，禁止凭通用知识作答。

---

## 📋 完整规程 (Full Protocol)

### 第一步：查询分析与增强 (Analyze)
严禁直接使用用户原始查询。脚本自动完成代词消歧、HyDE 增强、子问题拆分：
```bash
python skills/rag_search/scripts/rag_ops.py analyze --query "<用户问题>"
```
- 使用返回的 `expanded_queries` 逐条检索，覆盖语义盲区。
- 若包含 `sub_queries`（复杂问题），对每个子问题独立检索后汇总。

### 第二步：智能检索与筛选 (Retrieve)
1. 调用 `search_knowledge_base`（`hybrid_search=true` 当查询含特定术语或 ID）。
2. 仅保留 `score > 0.7` 的结果。
3. 多库场景：对每个 KB 分别检索，合并后按分数重排。

### 第三步：答案生成与引用 (Cite)
1. 回答开头注明"基于知识库信息..."。
2. 句末用 `[1][2]` 标注来源索引。
3. 运行引用格式化脚本生成标准来源列表：
   ```bash
   python skills/rag_search/scripts/rag_ops.py cite --results "<检索 JSON>"
   ```

---

## 🔒 强制准则 (Critical Rules)

| 规则 | 说明 |
|------|------|
| 不跳过分析脚本 | 代词消歧和 HyDE 增强由脚本完成，跳过导致召回断崖式下降 |
| 禁止无来源作答 | 检索空 → 声明未找到，建议用户上传文档 |
| 引用一致性 | 正文 `[N]` 索引必须与底部来源列表一一对应 |
| 元数据过滤 | 用户指定文档类型时，必须在 `metadata_filter` 中设置 |

## 🗂️ 资源
- `scripts/rag_ops.py`：查询分析 / HyDE 增强 / 引用格式化核心工具
- `backend/app/services/retrieval/`：后端检索 Pipeline（包含 RRF 重排、QueryPreProcessingStep）
