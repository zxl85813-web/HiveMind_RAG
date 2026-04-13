# 📊 RAG 评测指标速查表

> 快速参考卡片，用于日常评测和问题诊断

---

## 一、指标一览表

### 核心 6 维度（当前实现）

| 指标 | 中文名 | 评估对象 | 健康阈值 | 权重 |
|-----|-------|---------|---------|-----|
| `faithfulness` | 忠实度 | Generator | ≥ 0.85 | 20% |
| `answer_relevance` | 答案相关性 | Generator | ≥ 0.80 | 10% |
| `context_precision` | 上下文精确度 | Retriever | ≥ 0.75 | 10% |
| `context_recall` | 上下文召回率 | Retriever | ≥ 0.80 | 10% |
| `answer_correctness` | 答案正确性 | E2E | ≥ 0.85 | 30% |
| `semantic_similarity` | 语义相似度 | E2E | ≥ 0.80 | 20% |

### 检索专项指标（L1 层）

| 指标 | 公式 | 说明 |
|-----|------|-----|
| `Precision@K` | `相关文档数 / K` | Top-K 结果的精确度 |
| `Recall@K` | `召回相关数 / 总相关数` | 召回覆盖率 |
| `MRR` | `mean(1/rank)` | 首个相关结果排名 |
| `NDCG@K` | 标准公式 | 位置加权的相关性 |

---

## 二、快速诊断流程图

```
                    ┌─────────────────┐
                    │  E2E 得分 < 0.7  │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              ▼                              ▼
    ┌─────────────────┐            ┌─────────────────┐
    │ context_recall  │            │  faithfulness   │
    │     < 0.7       │            │     < 0.7       │
    └────────┬────────┘            └────────┬────────┘
             │                              │
             ▼                              ▼
    ┌─────────────────┐            ┌─────────────────┐
    │  检索问题        │            │  生成问题        │
    │  - Embedding    │            │  - Prompt       │
    │  - Chunking     │            │  - Temperature  │
    │  - Rerank       │            │  - 基座模型      │
    └─────────────────┘            └─────────────────┘
```

---

## 三、常见问题速查

### 问题 1: 忠实度低 (Faithfulness < 0.7)

**症状**: 回答包含上下文中没有的信息

**可能原因**:
- [ ] Temperature 过高
- [ ] Prompt 未强调"仅基于上下文回答"
- [ ] 上下文注入位置不当

**快速修复**:
```python
# 降低 Temperature
temperature = 0.1

# 强化 Prompt
prompt = """
仅基于以下上下文回答问题。如果上下文中没有相关信息，请明确说明"根据提供的资料无法回答"。
不要使用你的先验知识。

上下文: {context}
问题: {question}
"""
```

### 问题 2: 上下文召回低 (Context Recall < 0.7)

**症状**: 检索结果缺少关键信息

**可能原因**:
- [ ] Embedding 模型与领域不匹配
- [ ] Chunk 大小不合适
- [ ] 缺少多路召回

**快速修复**:
```python
# 增加召回数量
top_k = 10  # 从 5 增加到 10

# 启用混合检索
retrieval_mode = "hybrid"  # 向量 + 关键词

# 调整 Chunk 大小
chunk_size = 512  # 尝试不同大小
chunk_overlap = 50
```

### 问题 3: 答案相关性低 (Answer Relevance < 0.7)

**症状**: 回答正确但答非所问

**可能原因**:
- [ ] 问题理解偏差
- [ ] 回答过于发散
- [ ] 缺少问题重述

**快速修复**:
```python
prompt = """
问题: {question}

请直接回答上述问题，不要偏离主题。
回答应该简洁、针对性强。
"""
```

### 问题 4: 引用缺失 (CITE-001 违规)

**症状**: 有上下文但回答没有 [1], [2] 引用标记

**快速修复**:
```python
prompt = """
基于以下资料回答问题，每个陈述必须标注来源编号如 [1], [2]。

资料:
[1] {doc_1}
[2] {doc_2}

问题: {question}
"""
```

---

## 四、阈值参考表

### 生产环境建议阈值

| 场景 | 最低阈值 | 目标阈值 | 说明 |
|-----|---------|---------|-----|
| **客服问答** | 0.75 | 0.85 | 容错度较高 |
| **法律/医疗** | 0.90 | 0.95 | 零容忍幻觉 |
| **技术文档** | 0.80 | 0.90 | 准确性优先 |
| **创意写作** | 0.60 | 0.75 | 允许发散 |

### CI/CD 门禁建议

```yaml
quality_gates:
  blocking:  # 必须通过
    - faithfulness >= 0.80
    - answer_correctness >= 0.75
  warning:   # 警告但不阻塞
    - context_recall >= 0.70
    - semantic_similarity >= 0.75
```

---

## 五、评测命令速查

```bash
# 生成测试集
python -m scripts.eval generate --kb-id kb_001 --count 50

# 运行评测
python -m scripts.eval run --set-id eval_001 --model gpt-4o

# 查看报告
python -m scripts.eval report --report-id rpt_001

# 对比模型
python -m scripts.eval compare --set-id eval_001 --models "gpt-4o,claude-3"

# 导出 BadCase
python -m scripts.eval export-badcases --threshold 0.6
```

---

## 六、监控告警规则

```python
# 建议的 Prometheus 告警规则
ALERT_RULES = {
    "rag_faithfulness_low": {
        "condition": "avg(faithfulness) < 0.75 for 5m",
        "severity": "critical",
        "action": "检查 Prompt 和 Temperature"
    },
    "rag_recall_degradation": {
        "condition": "delta(context_recall) < -0.1 over 1h",
        "severity": "warning",
        "action": "检查 Embedding 服务和索引状态"
    },
    "rag_latency_spike": {
        "condition": "p95(latency_ms) > 5000",
        "severity": "warning",
        "action": "检查向量数据库性能"
    }
}
```

---

## 七、BadCase 分类标签

| 标签 | 说明 | 优先级 |
|-----|------|-------|
| `hallucination` | 幻觉/编造信息 | P0 |
| `outdated` | 信息过时 | P1 |
| `incomplete` | 回答不完整 | P1 |
| `irrelevant` | 答非所问 | P1 |
| `format_error` | 格式错误 | P2 |
| `tone_issue` | 语气不当 | P2 |
| `citation_missing` | 缺少引用 | P2 |

---

_快速参考 v1.0 | 2026-04-13_
