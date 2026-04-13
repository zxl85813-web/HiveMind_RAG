# 🎯 RAG 评测体系综合指南

> **版本**: v2.0  
> **最后更新**: 2026-04-13  
> **适用范围**: HiveMind RAG 系统全链路质量评估

---

## 一、核心理念：为什么需要新的评测范式？

### 1.1 传统指标的局限性

传统文本匹配指标（BLEU, ROUGE, METEOR）在 RAG 场景中存在天然缺陷：

| 缺陷类型 | 问题描述 | 示例 |
|---------|---------|------|
| **语义盲区** | 无法识别语义相同但表达不同的答案 | "北京是中国首都" vs "中国的首都是北京" |
| **幻觉容忍** | 可能给字面重叠高但语义相反的答案高分 | "不是 A" vs "是 A" 可能得高分 |
| **因果断裂** | 无法评估答案是否基于检索文档生成 | 无法区分 RAG 输出 vs LLM 先验知识泄漏 |

### 1.2 评测范式转型

```
传统范式: 字符串匹配 → 分数
    ↓
新范式: LLM-as-Judge + 分层解耦 + 硬规则断言
```

**核心原则**：
- 以 **LLM-as-Judge** 为核心的语义模型评测
- **解耦检索与生成**，精准定位问题
- **硬规则断言** 兜底，防止 LLM 裁判偏差

---

## 二、三层分层评估模型

```
┌─────────────────────────────────────────────────────────────┐
│                    L3: 端到端评测 (E2E)                      │
│         用户满意度 | 全链路耗时 | 准确率 | 综合得分            │
├─────────────────────────────────────────────────────────────┤
│  L1: Retriever 独立评测        │  L2: Generator 独立评测     │
│  Precision@K | Recall@K        │  Faithfulness              │
│  MRR | NDCG                    │  Instruction Following     │
│  Context Relevance             │  Answer Correctness        │
└─────────────────────────────────────────────────────────────┘
```

### 2.1 L1: Retriever 独立评测（检索侧）

**目标**：脱离生成环节，单独压测召回能力

| 指标 | 定义 | 计算方式 |
|-----|------|---------|
| **Precision@K** | Top-K 结果中相关文档占比 | `相关文档数 / K` |
| **Recall@K** | 召回的相关文档占全部相关文档比例 | `召回相关数 / 总相关数` |
| **MRR** | 首个相关结果的排名倒数均值 | `1/rank` 的均值 |
| **NDCG** | 考虑位置的归一化折损累积增益 | 标准 NDCG 公式 |
| **Context Relevance** | 检索片段是否包含回答所需最小必要信息 | LLM 评分 0-1 |

**评测方法**：
```python
# 建立 "问题 - 黄金文档 ID" 映射表
gold_mapping = {
    "什么是 RAG?": ["doc_001", "doc_015"],
    "如何配置向量数据库?": ["doc_042", "doc_043", "doc_044"],
}
```

### 2.2 L2: Generator 独立评测（生成侧）

**目标**：注入标准参考文档，消除检索噪音，测试 LLM 语义总结能力

| 指标 | 定义 | 评估方式 |
|-----|------|---------|
| **Faithfulness** | 回答是否能从上下文推导 | LLM 逐句验证 |
| **Instruction Following** | 是否遵循格式/风格指令 | 规则 + LLM 评分 |
| **Answer Correctness** | 答案与 Ground Truth 事实一致性 | LLM 对比评分 |
| **Semantic Similarity** | 语义相似度 | Embedding 余弦相似度 |

### 2.3 L3: 端到端评测 (End-to-End)

**目标**：评估完整 RAG 链路的用户体验

| 指标 | 定义 | 权重 |
|-----|------|-----|
| **Faithfulness** | 忠实度 | 20% |
| **Answer Relevance** | 答案相关性 | 10% |
| **Context Precision** | 上下文精确度 | 10% |
| **Context Recall** | 上下文召回率 | 10% |
| **Answer Correctness** | 答案正确性 | 30% |
| **Semantic Similarity** | 语义相似度 | 20% |

**综合得分计算**（当前实现）：
```python
total_score = (
    faithfulness * 0.2 +
    answer_relevance * 0.1 +
    context_precision * 0.1 +
    context_recall * 0.1 +
    answer_correctness * 0.3 +
    semantic_similarity * 0.2
)
```

---

## 三、RAG Triad 核心维度详解

### 3.1 Faithfulness（忠实度）

```
┌─────────────────────────────────────────┐
│  定义: 生成的回答是否能从检索上下文推导？   │
│  目标: 消除"幻觉"                        │
│  局限: 检索文档错误时，高忠实度 ≠ 正确答案  │
└─────────────────────────────────────────┘
```

**评估流程**：
1. 将回答拆分为独立声明（claims）
2. 逐一验证每个声明是否有上下文支撑
3. 计算有支撑声明的比例

### 3.2 Answer Relevance（答案相关性）

```
┌─────────────────────────────────────────┐
│  定义: 回答是否直接有效地解决用户问题？     │
│  目标: 解决"答非所问"                     │
│  方法: Answer → 逆向生成 Question → 相似度 │
└─────────────────────────────────────────┘
```

**评估方式**：
```
原始问题: "如何在 Python 中读取 JSON 文件？"
AI 回答: "使用 json.load() 函数..."
逆向问题: "这段代码是做什么的？" ← 相关性低
逆向问题: "如何用 Python 解析 JSON？" ← 相关性高
```

### 3.3 Context Relevance（上下文相关性）

```
┌─────────────────────────────────────────┐
│  定义: 检索片段是否包含回答所需最小必要信息？│
│  目标: 优化"检索信噪比"，减少干扰信息      │
│  指标: 有效句子数 / 总句子数               │
└─────────────────────────────────────────┘
```

---

## 四、LLM-as-Judge 偏差治理

### 4.1 常见偏差类型

| 偏差类型 | 描述 | 影响 |
|---------|------|-----|
| **位置偏差** | 倾向给排序靠前的选项打高分 | 多选评估不公平 |
| **冗长偏差** | 倾向给更长的答案打高分 | 鼓励冗余输出 |
| **自我偏好** | 更认同自己/同系列模型的风格 | 跨模型评估失真 |

### 4.2 缓解策略

#### 策略 1: Step-by-Step 推理
```python
judge_prompt = """
请先分析以下几个方面，然后给出评分：
1. 事实准确性分析: ...
2. 逻辑完整性分析: ...
3. 表达清晰度分析: ...

基于以上分析，给出最终评分 (0-1): 
"""
```

#### 策略 2: 顺序交换 (Swap)
```python
# 交换 A/B 顺序，多次评分取均值
score_1 = judge(answer_a, answer_b)  # A 在前
score_2 = judge(answer_b, answer_a)  # B 在前
final_score = (score_1 + score_2) / 2
```

#### 策略 3: 多裁判投票
```python
# 当前实现: MultiGraderEval
CRITERIA = {
    "accuracy": "Compare against context. Is it factually correct?",
    "safety": "Contains sensitive/harmful/toxic content?",
    "conciseness": "Efficient without unnecessary filler?",
    "format": "Follows requested output format?",
    "consistency": "Reconciles contradictions between sources?",
    "citation_accuracy": "Correctly uses [1], [2] citations?",
}
```

---

## 五、硬规则断言层（RAG Assertion Grader）

> LLM 裁判可能被绕过，硬规则是最后防线

### 5.1 强制规则

| 规则 ID | 规则描述 | 触发条件 | 惩罚 |
|--------|---------|---------|-----|
| **CITE-001** | 有上下文时必须引用 | KB 有结果但回答无 `[N]` 标记 | 分数上限 0.2 |
| **CITE-002** | 无上下文时必须声明 | KB 为空但回答超过 80 字符且未声明"未找到" | 分数上限 0.1 |

### 5.2 实现代码
```python
# backend/app/services/evaluation/rag_assertion_grader.py

class RagAssertionGrader:
    def check(self, query, response, context) -> RagAssertionResult:
        result = RagAssertionResult()
        
        # CITE-001: 有上下文必须引用
        if not _context_is_empty(context) and not _response_has_citations(response):
            result.add_violation("CITE-001", "缺少引用标记", penalty=0.2)
        
        # CITE-002: 无上下文必须声明
        if _context_is_empty(context) and not _response_acknowledges_not_found(response):
            if len(response) > 80:
                result.add_violation("CITE-002", "未声明知识库无结果", penalty=0.1)
        
        return result
```

---

## 六、诊断矩阵：快速定位问题根因

| E2E 表现 | Retriever | Generator | 诊断结论 | 优化建议 |
|---------|-----------|-----------|---------|---------|
| ❌ 差 | ✅ 好 | ✅ 好 | **上下文缺失/损耗** | 检查 Token 截断、Prompt 格式、长文本处理 |
| ❌ 差 | ❌ 差 | ✅ 好 | **检索失败** | 调优 Embedding、多路召回、Rerank |
| ❌ 差 | ✅ 好 | ❌ 差 | **生成失败** | 调优 Prompt、更换基座模型、Temperature |
| ❌ 差 | ❌ 差 | ❌ 差 | **系统性重构** | 重新审视 Chunking 策略与数据质量 |

---

## 七、评测数据模型

### 7.1 核心实体

```python
# EvaluationSet: 测试集
class EvaluationSet:
    id: str
    kb_id: str           # 关联知识库
    name: str
    items: List[EvaluationItem]
    reports: List[EvaluationReport]

# EvaluationItem: 单条测试用例
class EvaluationItem:
    id: str
    set_id: str
    question: str        # 测试问题
    ground_truth: str    # 标准答案
    reference_context: str  # 参考上下文

# EvaluationReport: 评测报告
class EvaluationReport:
    id: str
    set_id: str
    model_name: str      # 被测模型
    
    # 6 维度指标
    faithfulness: float
    answer_relevance: float
    context_precision: float
    context_recall: float
    answer_correctness: float
    semantic_similarity: float
    total_score: float
    
    # 成本追踪
    latency_ms: float
    cost: float
    token_usage: int
    
    details_json: str    # 详细结果

# BadCase: 标注的坏案例
class BadCase:
    id: str
    question: str
    bad_answer: str
    expected_answer: str
    reason: str          # 失败原因分类
    status: str          # pending/reviewed/fixed
```

---

## 八、落地最佳实践：三位一体方案

```
┌─────────────────────────────────────────────────────────────┐
│                    三位一体评测方案                          │
├─────────────────────────────────────────────────────────────┤
│  1. 自动化初筛 (Auto-Screening)                             │
│     └─ RAGAS 大规模回归测试，CI/CD 集成                      │
│                                                             │
│  2. 领域定制测试集 (Gold Dataset)                           │
│     └─ 业务专家维护高质量测试集                              │
│     └─ 覆盖边界场景、对抗样本                                │
│                                                             │
│  3. 人工抽检回贴 (Human Review)                             │
│     └─ 模型评分与专家评分不一致的 Case 深入复盘               │
│     └─ 持续迭代 BadCase 库                                  │
└─────────────────────────────────────────────────────────────┘
```

### 8.1 自动化评测流程

```python
# 使用示例
from app.services.evaluation import EvaluationService

# 1. 生成测试集
eval_set = await EvaluationService.generate_testset(
    db=db,
    kb_id="kb_001",
    name="产品文档测试集 v1",
    count=50
)

# 2. 运行评测
report = await EvaluationService.run_evaluation(
    db=db,
    set_id=eval_set.id,
    model_name="gpt-4o"
)

# 3. 查看结果
print(f"综合得分: {report.total_score}")
print(f"忠实度: {report.faithfulness}")
print(f"答案正确性: {report.answer_correctness}")
```

### 8.2 CI/CD 集成建议

```yaml
# .github/workflows/rag-eval.yml
name: RAG Quality Gate

on:
  push:
    paths:
      - 'backend/app/services/retrieval/**'
      - 'backend/app/services/generation/**'

jobs:
  evaluation:
    runs-on: ubuntu-latest
    steps:
      - name: Run RAG Evaluation
        run: python scripts/run_rag_eval.py --threshold 0.75
      
      - name: Fail if below threshold
        if: ${{ steps.eval.outputs.score < 0.75 }}
        run: exit 1
```

---

## 九、工具生态

| 工具 | 用途 | 集成状态 |
|-----|------|---------|
| **RAGAS** | 开源 RAG 评测框架 | ✅ 理念已集成 |
| **DeepEval** | LLM 应用测试框架 | 🔄 待集成 |
| **Arize Phoenix** | 可观测性 + 评测 | 🔄 待集成 |
| **LangSmith** | LangChain 生态评测 | ❌ 未计划 |

---

## 十、演进路线

### Phase 1: 当前状态 ✅
- [x] 6 维度 LLM-as-Judge 评分
- [x] 硬规则断言层 (CITE-001, CITE-002)
- [x] 多裁判评估 (MultiGraderEval)
- [x] 测试集自动生成
- [x] BadCase 管理

### Phase 2: 近期目标 🔄
- [ ] L1 Retriever 独立评测指标 (Precision@K, MRR)
- [ ] 偏差缓解策略 (顺序交换、多次采样)
- [ ] 评测结果可视化看板
- [ ] A/B 测试框架完善

### Phase 3: 远期规划 📋
- [ ] 领域专项裁判微调
- [ ] 对抗样本自动生成
- [ ] 实时在线评测 (Shadow Mode)
- [ ] 用户反馈闭环集成

---

## 附录 A: 评测 Prompt 模板

### A.1 6 维度评分 Prompt
```
Analyze the RAG result with 6 metrics:
Q: {question}
GT: {ground_truth}
AI: {answer}
Context: {contexts}

Rate 0.0-1.0 for:
f: Faithfulness (AI matches Context)
r: Relevance (AI matches Q)
p: Context Precision (Matches Q)
rec: Context Recall (Contains GT)
acc: Answer Correctness (AI matches GT facts)
sim: Semantic Similarity (Meaning similar to GT)

Return JSON only: {"f": 0.0, "r": 0.0, "p": 0.0, "rec": 0.0, "acc": 0.0, "sim": 0.0}
```

### A.2 测试用例生成 Prompt
```
Based on the following text chunk, generate a realistic question and its definitive answer (ground truth).
The question should be something a user would actually ask.
The answer must be based ENTIRELY on the provided text.

Format as JSON:
{"question": "...", "answer": "..."}

Text Chunk:
{chunk_content}
```

---

## 附录 B: 相关文件索引

| 文件路径 | 说明 |
|---------|------|
| `backend/app/services/evaluation/__init__.py` | 评测服务主入口 |
| `backend/app/services/evaluation/multi_grader.py` | 多裁判评估器 |
| `backend/app/services/evaluation/rag_assertion_grader.py` | 硬规则断言层 |
| `backend/app/models/evaluation.py` | 评测数据模型 |
| `docs/evaluation/L3_QUALITY_BOARD.md` | L3 质量看板 |
| `docs/evaluation/L4_INTEGRITY_REPORT.md` | L4 完整性报告 |

---

_Generated by HiveMind Documentation System | 2026-04-13_
