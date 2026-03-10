# 🍯 数据治理 — 知识的酿造过程

> 花粉本身没有价值。
> 蜜蜂将它采集、转化、脱水、封存——经过这一系列工序，它才变成蜂蜜。
> HiveMind 对文档做的，与此如出一辙。

---

## 知识的生命周期

一份文档从上传到可被精准检索，需要经历完整的"酿造"流程：

```
原始文档（花粉）
    │
    ▼
📥 上传 & 入队
    │  JobManager (LangGraph DAG) 调度
    ▼
🔍 解析 Skills
    │  PDF → 文本+图片  /  Excel → 表格  /  图片 → OCR
    ▼
🧠 上下文增强（Contextual Retrieval）
    │  Agent 为每个分块注入文档级背景摘要
    │  "这段文字出自XX文档第X章，讨论的是……"
    ▼
    ├──→ 🕸️ 实体/关系抽取 → Neo4j 知识图谱
    │
    └──→ 🔢 向量化 → pgvector
              │
              └──→ 📋 自动打标签 / 生成摘要 → 抽象索引

            （蜂蜜封存完毕）
```

---

## 三层记忆结构 — 蜂巢的存储格

知识不是平铺在一个向量数据库里的。HiveMind 构建了三层结构，对应不同粒度的检索需求：

| 层级 | 名称 | 引擎 | 作用 | 类比 |
|:---|:---|:---|:---|:---|
| **Tier 1** | 抽象索引 | 内存标签/实体集合 | 快速碰撞，锁定检索方向 | 蜂巢标签格——告诉你蜜在哪个区 |
| **Tier 2** | 知识图谱 | Neo4j | 关联扩展，发现隐式关系 | 蜂巢的连通管道——追溯关联 |
| **Tier 3** | 向量精排 | pgvector + BM25 + Cross-Encoder | 混合召回 → 精排 → Top-N | 精确取出这一格蜜 |

### 三层渐进式检索流程

```
用户提问
    │
    ▼ Tier 1：标签/实体碰撞（毫秒级）
    │  → 命中？快速缩小候选范围
    │
    ▼ Tier 2：图谱关联扩展
    │  → 从命中节点出发，扩展 1-2 跳关联知识
    │
    ▼ Tier 3：向量 + BM25 混合召回
       → Cross-Encoder 精排
       → 注入 Top-N 上下文给 LLM
```

---

## Contextual Retrieval — 为什么每个分块都要有"背景"

传统 RAG 的分块是盲目的。一段话被切出来，它不知道自己是哪份文档的哪个部分，语义上下文丢失。

HiveMind 在入库时，**Agent 会为每个分块生成一段上下文前缀**：

```
[原始分块]
"该合同第三条规定，甲方应在交付后30天内完成验收……"

[增强后]
"本段摘自《2024年XX项目服务合同》第三章「验收条款」。
 该合同签署于2024年1月，甲乙双方为A公司和B公司。
 该合同第三条规定，甲方应在交付后30天内完成验收……"
```

这使得每个分块即使脱离原始文档，也能被精准理解和检索。

---

## 知识图谱 — 关系是知识的骨架

向量找的是"相似"，图谱找的是"关联"。二者互补。

当 Agent 处理一份文档，它会同步执行实体/关系抽取：

```
文档 → Agent 抽取 → (实体A) --[关系]--> (实体B) → 写入 Neo4j
```

例如，处理一份技术文档：
- 实体：`FastAPI`、`pgvector`、`LangGraph`
- 关系：`FastAPI` **依赖** `uvicorn`，`pgvector` **存储** `向量嵌入`

当用户问"LangGraph 相关的数据库是什么？"，图谱检索可以通过关系路径找到 `pgvector`，即使这两个词从未在同一句话中出现过。

---

## JobManager — 异步批处理引擎

文档处理是异步的，不阻塞用户操作。`JobManager` 基于 LangGraph 实现 DAG 任务调度：

- **并发处理**：多文档可同时进入 Pipeline
- **断点续传**：任务中断后从最后成功的节点恢复
- **进度推送**：处理状态通过 WebSocket 实时推送到前端
- **多模态支持**：PDF / Excel / 图片通过不同 Skill 插件处理，热插拔

---

## 代码位置索引

| 组件 | 路径 |
|:---|:---|
| Ingestion Pipeline | `backend/app/batch/` |
| 解析 Skills | `backend/app/skills/` |
| 检索 Pipeline | `backend/app/services/retrieval/` |
| 知识库管理服务 | `backend/app/services/knowledge/` |
| 记忆层服务 | `backend/app/services/memory/` |
| 图谱抽取 | `backend/app/skills/` (graph skill) |

---

## 相关文档

- [← 返回 README](../README.md)
- [🔐 权限-角色-记忆治理](ACCESS_ROLE_MEMORY_GOVERNANCE.md)
- [🧭 Agent 治理：指挥系统](AGENT_GOVERNANCE.md)
- [🏭 开发治理：生产规范体系](DEV_GOVERNANCE.md)
