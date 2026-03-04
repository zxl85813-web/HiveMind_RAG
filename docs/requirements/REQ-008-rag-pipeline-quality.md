# REQ-008: RAG Pipeline 可配置化 & 数据质量体系

> 📅 创建时间: 2026-02-22
> 📝 来源: 用户需求讨论
> 🏷️ 优先级: P1 — 核心功能

---

## 1. 需求背景

当前 RAG 知识库系统存在以下短板：

1. **Pipeline 是硬编码的** — 所有文档走同一个处理流程（解析 → 800 字分块 → 向量化），无法按文档类型定制
2. **缺少标签/分类体系** — 文档导入没有打标签，无法按标签匹配处理策略
3. **没有数据质量审核** — 任何文件上传后直接入库，没有审核环节
4. **缺少 RAG 质量评估** — 没有衡量幻觉率、召回率等指标的标准化体系

---

## 2. 需求拆解

### 2.1 Pipeline 配置系统

#### 2.1.1 Ingestion Pipeline（摄取流水线）可配置

**目标**: 不同类型的文档走不同的处理工作流。

**概念模型**:
```
PipelineConfig:
  name: "法律合同处理流"
  trigger_tags: ["legal", "contract"]
  steps:
    - step: "OCR增强"           # 合同经常是扫描件
      enabled: true
      config: { engine: "paddle_ocr", lang: "zh" }
    - step: "敏感信息脱敏"       # 合同有商业机密
      enabled: true
      config: { patterns: ["phone", "id_card", "amount"] }
    - step: "语义分块"
      enabled: true
      config: { strategy: "recursive", chunk_size: 500, overlap: 50 }
    - step: "向量化"
      enabled: true
      config: { model: "embedding-3", batch_size: 32 }
    - step: "质量检查"
      enabled: true
      config: { min_chunk_length: 20, max_duplicate_ratio: 0.3 }
```

**核心功能**:
- [ ] Pipeline 配置存储（数据库 or YAML 文件）
- [ ] Step 注册中心（类似 ParserRegistry，注册所有可用步骤）
- [ ] Pipeline 编排引擎（按配置顺序执行步骤）
- [ ] Pipeline Debug/日志（记录每个 Step 的处理结果）
- [ ] 预设模板（内置 3~5 个常见 Pipeline：通用文档、技术文档、法律文档、数据表格）

#### 2.1.2 Retrieval Pipeline（检索流水线）可配置

**目标**: 不同知识库可以有不同的检索策略。

**概念模型**:
```
RetrievalConfig:
  name: "技术文档检索"
  steps:
    - step: "查询改写"        # Query Rewriting / HyDE
      config: { method: "hyde", model: "deepseek-v2.5" }
    - step: "混合检索"        # Vector + BM25
      config: { vector_weight: 0.7, bm25_weight: 0.3, top_k: 20 }
    - step: "重排序"          # Cross-Encoder Reranker
      config: { model: "bge-reranker-v2", top_n: 5 }
    - step: "引用溯源"        # Source Attribution
      config: { include_page_number: true, highlight: true }
```

**核心功能**:
- [ ] 每个知识库可独立绑定 Retrieval Pipeline 配置
- [ ] 检索策略 A/B 测试支持
- [ ] 检索过程追踪日志（trace_log 已有雏形）

---

### 2.2 标签/分类体系 (Tagging & Classification)

#### 2.2.1 标签管理

**概念模型**:
```sql
-- 标签表
Tag:
  id, name, color, category, description, created_at

-- 标签分类
TagCategory:
  id: str
  name: str     -- e.g. "文档类型", "业务领域", "安全等级"

-- 文档-标签关联
DocumentTag:
  document_id, tag_id
```

**预置标签分类**:
| 类别 | 示例标签 |
|------|---------|
| 文档类型 | `需求文档`, `设计文档`, `测试用例`, `API文档`, `用户手册` |
| 业务领域 | `金融`, `医疗`, `法律`, `技术`, `运营` |
| 安全等级 | `公开`, `内部`, `保密`, `机密` |
| 处理状态 | `待审核`, `已审核`, `已驳回`, `需人工标注` |

#### 2.2.2 标签与 Pipeline 匹配

**规则引擎**:
```python
# 匹配规则示例
rules = [
    {
        "condition": {"tags_contain": ["legal", "contract"]},
        "pipeline": "legal_pipeline"
    },
    {
        "condition": {"file_type_in": ["xlsx", "csv"]},
        "pipeline": "table_pipeline"
    },
    {
        "condition": {"tags_contain": ["confidential"]},
        "pipeline": "secure_pipeline"  # 额外加密和脱敏步骤
    }
]
```

#### 2.2.3 自动标签 (Auto-Tagging)

- [ ] 基于文件名/扩展名的规则标签
- [ ] 基于文件内容的 AI 标签（LLM 读取前 N 页摘要后打标签）
- [ ] 基于知识库元数据的继承标签（知识库本身有标签，导入文档继承）

---

### 2.3 数据质量审核体系 (Data Quality Review)

#### 2.3.1 审核工作流

```
上传文档
    ↓
[自动预处理] → 解析 + 分块 + AI 质量评分
    ↓
[自动审核] → 规则引擎检查 (见下方规则)
    ↓
    ├── 自动通过 → 直接入库 (score ≥ 阈值)
    ├── 人工审核 → 进入审核队列 (阈值范围内)
    └── 自动驳回 → 标记失败 (score ≤ 下限)
    ↓
[人工审核台] → 审核员 Review & 标注
    ↓
    ├── 通过 → 入库
    ├── 修改 → 修改后重新入库
    └── 驳回 → 标记失败，通知上传者
```

#### 2.3.2 自动审核规则

| 规则 | 检查内容 | 阈值 |
|------|---------|------|
| 最小内容长度 | 解析后文本不能太短 | ≥ 100 字符 |
| 重复率检测 | 分块之间的重复度 | ≤ 30% |  
| 乱码检测 | 非 UTF-8 字符占比 | ≤ 5% |
| 空白率检测 | 空白/无意义内容占比 | ≤ 20% |
| 格式完整性 | PDF 页数 > 0, DOCX 段落 > 0 | 必须通过 |
| 内容哈希去重 | 检查是否已存在相同内容的文档 | 内容 hash 唯一 |
| 敏感信息检测 | 是否包含手机号/身份证/银行卡号 | 可配置策略 |

#### 2.3.3 人工审核台 (Review Dashboard)

**前端页面**:
- 审核列表（按状态筛选：待审核 / 已通过 / 已驳回）
- 文档预览（左侧原文，右侧分块结果对比）
- 标签编辑（人工修正 AI 打的标签）
- 批注功能（审核员可以对问题分块添加批注）
- 批量操作（批量通过 / 驳回）

**后端 API**:
- [ ] `GET /knowledge/review/queue` — 审核队列
- [ ] `POST /knowledge/review/{doc_id}/approve` — 通过审核
- [ ] `POST /knowledge/review/{doc_id}/reject` — 驳回
- [ ] `POST /knowledge/review/{doc_id}/annotate` — 添加批注
- [ ] `GET /knowledge/review/stats` — 审核统计

#### 2.3.4 数据库 Schema 扩展

```python
class DocumentReview(SQLModel, table=True):
    """数据质量审核记录"""
    id: str
    document_id: str       # FK -> documents.id
    reviewer_id: str | None  # FK -> users.id (人工审核时)
    review_type: str       # "auto" | "manual"
    status: str            # "pending" | "approved" | "rejected" | "needs_revision"
    
    # 自动审核评分
    quality_score: float = 0.0       # 0~1 综合评分
    content_length_ok: bool = True
    duplicate_ratio: float = 0.0
    garble_ratio: float = 0.0
    blank_ratio: float = 0.0
    
    # 人工审核内容
    reviewer_comment: str = ""
    
    created_at: datetime
    updated_at: datetime
```

---

### 2.4 RAG 质量评估体系 (Evaluation Framework)

#### 2.4.1 评估指标体系

采用业界标准 **RAGAS** (Retrieval Augmented Generation Assessment) 框架：

| 指标 | 英文 | 含义 | 计算方式 |
|------|------|------|---------|
| **忠实度** | Faithfulness | 回答是否忠于检索到的上下文（抗幻觉） | LLM 判断回答中每句话是否有上下文支撑 |
| **答案相关性** | Answer Relevancy | 回答是否与问题相关 | 生成反向问题，计算与原问题的相似度 |
| **上下文精确率** | Context Precision | 检索到的文档是否真正相关 | 相关文档 / 总检索文档 |
| **上下文召回率** | Context Recall | 是否检索到了所有相关文档 | 检索到的相关文档 / 应该检索到的文档 |
| **幻觉率** | Hallucination Rate | 回答中没有上下文支撑的比例 | 1 - Faithfulness |
| **噪声鲁棒性** | Noise Robustness | 混入无关文档时的表现 | 加入干扰文档后的指标变化 |

#### 2.4.2 评估工作流

```
[创建测试集]
    ↓
[评估任务]
    - 选择知识库
    - 选择测试集 (Question + Ground Truth Answer + Ground Truth Contexts)
    - 选择评估指标
    ↓
[自动执行]
    - 对每个问题执行 RAG Pipeline
    - 收集 Retrieved Contexts + Generated Answer
    - 用 LLM 评估各指标
    ↓
[评估报告]
    - 各指标均分 / 分布图
    - 最差 Case 排行榜 (方便定位问题)
    - 与上一次评估的对比 (Delta)
```

#### 2.4.3 测试集管理

```python
class EvalTestSet(SQLModel, table=True):
    """RAG 评估测试集"""
    id: str
    name: str           # e.g. "法律知识库-V1测试集"
    kb_id: str           # 关联知识库
    description: str = ""
    created_at: datetime

class EvalTestCase(SQLModel, table=True):
    """单条测试用例"""
    id: str
    test_set_id: str          # FK -> eval_test_sets.id
    question: str              # 测试问题
    ground_truth_answer: str   # 标准答案
    ground_truth_contexts: str # 应该命中的文档片段 (JSON)
    difficulty: str = "normal" # easy | normal | hard
    tags: str = ""             # 测试标签 (JSON array)

class EvalRun(SQLModel, table=True):
    """一次评估运行"""
    id: str
    test_set_id: str
    pipeline_config: str       # 使用的 Pipeline 配置 (JSON)
    
    # 聚合指标
    avg_faithfulness: float = 0.0
    avg_answer_relevancy: float = 0.0
    avg_context_precision: float = 0.0
    avg_context_recall: float = 0.0
    hallucination_rate: float = 0.0
    
    total_cases: int = 0
    passed_cases: int = 0
    
    status: str = "running"    # running | completed | failed
    created_at: datetime
    completed_at: datetime | None = None

class EvalCaseResult(SQLModel, table=True):
    """单条用例的评估结果"""
    id: str
    run_id: str
    test_case_id: str
    
    # RAG 输出
    retrieved_contexts: str    # 检索到的上下文 (JSON)
    generated_answer: str      # LLM 生成的回答
    
    # 各项评分
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_precision: float = 0.0
    context_recall: float = 0.0
    
    # 问题标注
    has_hallucination: bool = False
    reviewer_comment: str = ""
```

#### 2.4.4 前端评估仪表盘

- **测试集管理** — CRUD 测试集和测试用例
- **评估运行** — 触发评估、查看进度
- **评估报告** — 雷达图(各指标)、趋势图(历次评估对比)、问题 Case 详情
- **知识库健康度** — 每个知识库的综合评分 + 达标状态

---

## 3. 实现优先级

| 阶段 | 内容 | 预计工作量 |
|------|------|-----------|
| **Phase 1** | 标签体系 + 基础 Pipeline 配置 | 中 |
| **Phase 2** | 自动审核规则 + 审核工作流 | 中 |
| **Phase 3** | 人工审核台前端 | 中 |
| **Phase 4** | RAG 评估测试集管理 | 中 |
| **Phase 5** | RAGAS 评估引擎集成 | 高 |
| **Phase 6** | 评估仪表盘前端 | 中 |

---

## 4. 依赖项

| 依赖 | 用途 | 状态 |
|------|------|------|
| `ragas` (Python) | RAG 评估框架 | ⬜ 未安装 |
| `deepeval` (Python) | 备选评估框架 | ⬜ 未安装 |
| `langchain-text-splitters` | 语义分块 | ⬜ 未安装 |
| `echarts` / `recharts` (前端) | 评估报告可视化 | ⬜ 未安装 |

---

## 5. 参考标准

- [RAGAS Framework](https://docs.ragas.io/) — RAG 评估事实标准
- [DeepEval](https://docs.confident-ai.com/) — LLM 评估框架
- [LangSmith Evaluations](https://docs.smith.langchain.com/) — LangChain 评估工具
- [TruLens](https://www.trulens.org/) — RAG 可观测性
