# 🔬 HiveMind 评估体系深度审计报告

> **审计角色**: LLM 评估体系架构师  
> **审计日期**: 2026-04-13  
> **审计范围**: 全链路评估代码 + 数据模型 + 运行时集成  
> **结论**: 框架骨架完整，但存在 7 个结构性缺陷需要改造

---

## 一、现状总评

### 1.1 已有的好东西（不要丢掉）

| 组件 | 评价 | 成熟度 |
|-----|------|-------|
| `EvaluationService.run_evaluation` | 6 维度 LLM-as-Judge 完整闭环 | ⭐⭐⭐ |
| `MultiGraderEval` | 多裁判独立评分 + 硬规则兜底 | ⭐⭐⭐⭐ |
| `RagAssertionGrader` | CITE-001/002 硬规则断言 | ⭐⭐⭐⭐ |
| `ABTracker` | A/B 实验遥测采集 | ⭐⭐⭐ |
| `L4 Process Integrity Gate` | 推理链结构审计 | ⭐⭐⭐ |
| `SelfLearningService` | 失败案例自动反思 + Todo 生成 | ⭐⭐⭐ |
| `SwarmTrace/SwarmSpan` | 可观测性数据模型 | ⭐⭐⭐⭐ |

### 1.2 总体诊断

```
当前状态: "骨架完整，肌肉松弛"

✅ 评估维度设计合理（6 维度 + 多裁判 + 硬规则）
✅ 数据模型覆盖面广（Trace/Span/Report/BadCase）
✅ 自进化闭环已打通（L3 失败 → L4 反思 → Todo）

❌ 但评估的"精度"和"可信度"存在严重问题
❌ 评估结果无法真正指导优化决策
❌ 检索侧和生成侧没有解耦评测
```

---

## 二、7 个结构性缺陷诊断

### 缺陷 1: 🔴 单次 LLM 调用承担 6 维度评分 — "万能裁判"反模式

**位置**: `EvaluationService.run_evaluation` 第 150-165 行

**现状代码**:
```python
judge_prompt = (
    "Analyze the RAG result with 6 metrics:\n"
    f"Q: {res['question']}\n"
    f"GT: {res['ground_truth']}\n"
    f"AI: {res['answer']}\n"
    f"Context: {res['contexts'][:3]}\n\n"
    "Rate 0.0-1.0 for:\n"
    "f: Faithfulness ...\n"
    "r: Relevance ...\n"
    "p: Context Precision ...\n"
    "rec: Context Recall ...\n"
    "acc: Answer Correctness ...\n"
    "sim: Semantic Similarity ...\n\n"
    'Return JSON only: {"f": 0.0, "r": 0.0, ...}'
)
```

**问题**:
- 一个 Prompt 同时要求 6 个维度评分，LLM 认知负荷过重
- 各维度评分会互相"污染"（锚定效应：一个维度打高分会拉高其他维度）
- 没有要求先推理再评分（直接输出数字，缺乏 Chain-of-Thought）
- `Context: {res['contexts'][:3]}` — 只取前 3 个上下文的字符串表示，信息严重丢失

**严重程度**: 🔴 高 — 直接导致评分不可信

**改造方案**:
```
方案 A（推荐）: 拆分为独立评估器
  - FaithfulnessGrader: 逐句验证 claim 是否有上下文支撑
  - RelevanceGrader: 逆向生成问题 + 相似度计算
  - ContextGrader: 评估上下文信噪比
  - CorrectnessGrader: 与 Ground Truth 事实对比
  每个 Grader 独立 Prompt，强制 CoT 推理

方案 B（折中）: 保持单次调用但强制 CoT
  - 要求先输出每个维度的分析理由
  - 再输出最终评分
  - 增加 "reasoning" 字段到输出 JSON
```

---

### 缺陷 2: 🔴 检索侧和生成侧完全耦合 — 无法定位问题根因

**位置**: `EvaluationService.run_evaluation` 第 110-140 行

**现状**:
```python
# 评测时同时执行检索 + 生成，然后一起评分
pipeline = RetrievalPipeline()
docs = await pipeline.run(item.question, collection_names=[kb.vector_collection])
contexts = [doc.page_content for doc in docs]
# ... 然后生成 answer ...
# ... 然后一起评分 ...
```

**问题**:
- 检索失败和生成失败混在一起，无法区分
- 没有 L1 Retriever 独立评测（Precision@K, Recall@K, MRR 全部缺失）
- 没有 L2 Generator 独立评测（注入标准上下文测试生成能力）
- 诊断矩阵无法落地：你不知道是"检索没找到"还是"找到了但生成错了"

**严重程度**: 🔴 高 — 评测结果无法指导优化方向

**改造方案**:
```
新增两个独立评测方法:

1. evaluate_retriever(question, gold_doc_ids) → Precision@K, Recall@K, MRR
   - 只跑检索，不跑生成
   - 对比检索结果与黄金文档 ID

2. evaluate_generator(question, gold_context, ground_truth) → Faithfulness, Correctness
   - 注入标准上下文，不跑检索
   - 纯测 LLM 的总结和表达能力
```

---

### 缺陷 3: 🟡 MultiGraderEval 与 EvaluationService 是两套独立体系

**位置**: 
- `evaluation/__init__.py` — 6 维度评分（用于离线评测）
- `evaluation/multi_grader.py` — 6 维度评分（用于在线 Reflection）

**问题**:
- 两套评估器的维度定义不同、Prompt 不同、评分标准不同
- `EvaluationService` 评 RAG 质量：faithfulness, relevance, precision, recall, correctness, similarity
- `MultiGraderEval` 评 Agent 质量：accuracy, safety, conciseness, format, consistency, citation
- 同一个系统有两套"质量标准"，结果不可比较
- `MultiGraderEval` 的硬规则断言（`RagAssertionGrader`）没有集成到 `EvaluationService`

**严重程度**: 🟡 中 — 造成评估标准碎片化

**改造方案**:
```
统一为分层评估架构:

BaseGrader (抽象基类)
├── RAGGrader (RAG 专项)
│   ├── FaithfulnessGrader
│   ├── RelevanceGrader
│   └── ContextGrader
├── AgentGrader (Agent 专项)
│   ├── TaskCompletionGrader
│   ├── ToolUsageGrader
│   └── SafetyGrader
└── AssertionLayer (硬规则，所有 Grader 共享)
    ├── CITE-001
    ├── CITE-002
    ├── TOOL-001
    └── SAFE-001

EvaluationService 和 Reflection 节点都调用同一套 Grader
```

---

### 缺陷 4: 🟡 评分没有置信度和一致性校验

**位置**: 所有评分逻辑

**问题**:
- LLM 裁判的评分没有置信度指标
- 没有多次采样取均值（单次评分噪声大）
- 没有顺序交换（Position Bias 未缓解）
- 没有评分一致性检查（同一个 Case 评两次，分数可能差 0.3+）

**现状**: 每个维度只调用一次 LLM，直接取返回值作为最终分数

**严重程度**: 🟡 中 — 评分波动大，不可复现

**改造方案**:
```python
class RobustGrader:
    async def grade(self, ...) -> GradeResult:
        # 1. 多次采样
        scores = []
        for _ in range(N_SAMPLES):  # N=3
            score = await self._single_grade(...)
            scores.append(score)
        
        # 2. 一致性检查
        std_dev = statistics.stdev(scores)
        if std_dev > 0.2:  # 波动过大，标记为低置信度
            confidence = "low"
        else:
            confidence = "high"
        
        # 3. 返回均值 + 置信度
        return GradeResult(
            score=statistics.mean(scores),
            confidence=confidence,
            std_dev=std_dev,
            raw_scores=scores
        )
```

---

### 缺陷 5: 🟡 EvaluationItem 缺少检索侧黄金标注

**位置**: `models/evaluation.py`

**现状**:
```python
class EvaluationItem(SQLModel, table=True):
    question: str
    ground_truth: str           # 只有答案的 Ground Truth
    reference_context: str      # 只存了生成时用的 chunk 片段
```

**问题**:
- 没有 `gold_doc_ids` 字段 — 无法做 Retriever 独立评测
- 没有 `gold_context` 字段 — 无法做 Generator 注入式评测
- `reference_context` 只截取了 500 字符，信息不完整
- 没有难度标签、类型标签 — 无法按维度分析弱项

**严重程度**: 🟡 中 — 数据模型限制了评测能力

**改造方案**:
```python
class EvaluationItem(SQLModel, table=True):
    question: str
    ground_truth: str
    
    # 新增: 检索侧黄金标注
    gold_doc_ids: list[str]       # 应该检索到的文档 ID
    gold_context: str             # 完整的参考上下文
    
    # 新增: 元数据标签
    difficulty: str               # easy / medium / hard
    category: str                 # factual / reasoning / comparison / multi-hop
    requires_tools: list[str]     # 需要的工具列表（Agent 评测用）
```

---

### 缺陷 6: 🟡 L3 看板脚本硬编码 + 脆弱

**位置**: `backend/scripts/l3_dashboard_sync.py`

**问题**:
- 只有 3 个测试用例，覆盖面极窄
- 路径硬编码 `c:\Users\linkage\Desktop\aiproject\...`
- 评分 Prompt 过于简单（4 维度简单平均）
- 与 `EvaluationService` 的 6 维度体系不一致
- 异常处理粗糙：JSON 解析失败直接 score=0

**严重程度**: 🟡 中 — L3 看板数据不可信

**改造方案**:
```
1. 测试用例从硬编码改为从数据库/配置文件加载
2. 评分逻辑复用 EvaluationService 的 Grader 体系
3. 路径使用相对路径或环境变量
4. 增加测试用例到 20+ 覆盖各维度
```

---

### 缺陷 7: 🟢 A/B 测试框架采集了数据但没有决策闭环

**位置**: `evaluation/ab_tracker.py` + `swarm.py`

**现状**:
```python
# swarm.py 中随机分配变体
variant = "react" if random.random() < 0.5 else "monolithic"

# ab_tracker.py 只做数据采集和统计
def get_summary(self) -> dict:
    # 返回统计摘要，但没有人消费这个结果
```

**问题**:
- 数据采集了但没有自动决策机制
- 没有统计显著性检验（样本量够不够？差异是否显著？）
- `quality_score` 字段大部分是 -1.0（未填充）
- 没有与评估体系打通（A/B 结果不影响评估报告）

**严重程度**: 🟢 低 — 功能存在但未闭环

---

## 三、改造优先级路线图

```
┌─────────────────────────────────────────────────────────────┐
│                    改造优先级矩阵                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  影响大 ┃  P0: 缺陷1 拆分评估器    P1: 缺陷2 解耦检索/生成  │
│        ┃  (评分可信度)            (问题定位能力)             │
│  ──────╋────────────────────────────────────────────────── │
│  影响小 ┃  P2: 缺陷3 统一Grader   P3: 缺陷4 置信度校验     │
│        ┃  P2: 缺陷5 数据模型扩展  P3: 缺陷6 L3脚本重构     │
│        ┃                         P4: 缺陷7 A/B闭环         │
│        ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │
│           实现简单 ←──────────────────────→ 实现复杂         │
└─────────────────────────────────────────────────────────────┘
```

### Phase 0: 立即修复（1-2 天）

**目标**: 让现有评分变得可信

1. 给 `EvaluationService` 的 judge prompt 加上 CoT 推理要求
2. 把 `RagAssertionGrader` 集成到 `EvaluationService`（目前只在 MultiGrader 里用）
3. 修复 L3 脚本的硬编码路径

### Phase 1: 核心改造（1 周）

**目标**: 拆分评估器 + 解耦检索/生成

1. 实现独立的 `FaithfulnessGrader`（逐句 claim 验证）
2. 实现独立的 `CorrectnessGrader`（与 GT 事实对比）
3. 新增 `evaluate_retriever()` 方法
4. 新增 `evaluate_generator()` 方法
5. 扩展 `EvaluationItem` 数据模型

### Phase 2: 体系统一（2 周）

**目标**: 统一评估标准 + 提升可信度

1. 抽象 `BaseGrader` 基类
2. 统一 `EvaluationService` 和 `MultiGraderEval`
3. 增加多次采样 + 置信度
4. L3 脚本重构为可配置的评测框架

### Phase 3: 闭环优化（持续）

**目标**: 评估驱动优化

1. A/B 测试统计显著性检验
2. 评估结果自动触发优化建议
3. 评测用例库持续扩充
