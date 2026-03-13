# 🧭 核心抽象设计：分词/切分、分类与路由算法 (Core Abstractions: Chunking, Classification & Routing)

> **目标**：在整个系统中，分词切分 (Tokenization & Chunking)、分类推断 (Classification) 和动态路由 (Routing) 高频地贯穿于数据摄取 (Ingestion)、知识检索 (RAG)、记忆压缩 (Memory Compression) 以及多智能体协作 (Swarm Orchestration) 中。本设计旨在将这些分散的算法下沉为基础组件 (Core Infrastructure)，实现跨模块的开箱即用、统一配置与评估。

---

## 📅 版本历史

| 版本 | 日期 | 状态 | 说明 |
|------|------|------|------|
| v1.0 | 2026-03-12 | Draft | 初版核心算法统一设计抽象 |

---

## 一、为什么需要统一抽象？(Motivation)

在目前的系统中，存在大量的**重复且未标定**的实现模式：
1. **分块 (Chunking)**：`batch/ingestion/chunking.py` 内部实现了分块，但在长对话记忆生成历史摘要时，又需要重新切割上下文。
2. **分类 (Classification)**：检索流程 `QueryPreProcessingStep` 里硬编码了 prompt 提取意图（fact/action/summary）；如果在其他地方需要分类文档、标签或 SQL 复杂度，也要重写极其类似的 LLM prompt 解析逻辑。
3. **路由 (Routing)**：Swarm Orchestrator 内部维护了 Agent 的智能路由；RAGGateway 内部也有根据用户意图选择检索策略的路由需求。

如果各路各自为战，将导致**不可控的幻觉率**、**不同步的计费计算**与**无法中心化调优的设计**。

---

## 二、基础引擎：统一的分词与切分体系 (Tokenization & Chunking)

**定位**：为整个系统的文本长短感知提供标准尺子和统一裁剪工具。

### 2.1 统计与计费基座 (`TokenService`)
封装所有依赖预训练分词器 (如 `tiktoken`, `sentencepiece`) 的操作。

- **`count_tokens(text: str, model: str) -> int`**：计算准确 Token 数，用于计费、滑动窗口和防 OOM 截断。
- **`truncate_to_budget(text: str, max_tokens: int, strategy: str) -> str`**：安全的边界截断，防止字符截断导致 UTF-8 乱码或破损。

### 2.2 文本切分器接口标准化 (`BaseSplitter`)
不再局限于入库，任何文本压缩、对话压缩都可以使用它。

```python
class BaseSplitter(ABC):
    @abstractmethod
    def split_text(self, text: str) -> list[str]: pass

class SemanticSplitter(BaseSplitter):
    """基于特定标点符号或语义（LLM）的句子分割，保证上下文句意完整。"""

class ParentChildSplitter(BaseSplitter):
    """大段落与小句子的双级切割，用于高精度 Vector 检索的回溯展示。"""

class TokenSplitter(BaseSplitter):
    """纯粹的按 Token 上限无情切分 (常用于超出软上限但需要暴力送给大模型的临时历史摘要场景)。"""
```

---

## 三、通用推断引擎：分类算法 (Classification Engine)

**定位**：将系统中所有基于 `规则` 与 `大模型语义推断` 的判断整合为单一的泛化调用。

提供 `ClassifierService`。无论在系统哪一层，只需定义目标的 `Enum` 类型，就能获取分类结果。

### 3.1 意图分类引擎 (Intent Classifier)
基于预先注入或动态注册的特征，识别一段文本的内容属性：

```python
from enum import Enum

class QueryIntent(Enum):
    FACT = "事实问答"
    SUMMARY = "总结概括"
    COMPARISON = "对比分析"
    ACTION = "动作指令"
    EXPLORATION = "开放探索"

# 通用分类器调用形态
intent, confidence = await classifier_service.classify(
    text=user_msg, 
    target_enum=QueryIntent,
    fallback=QueryIntent.FACT
)
```

### 3.2 标签与实体分类引擎 (Tag/Entity Extraction)
允许输入候选标签集合 (Tags Vector Space)，利用 LLM 的 `logprobs` 信心分数进行 Top-K 映射：
- 用于文档入库时的自动标签推断 (Auto-Tagging)。
- 用于 SQL 复杂度评估（L1/L2/L3）与提取卡片。
- 用于记忆提取层 (Tier-1 Abstract) 里的标签标注。

### 3.3 分类策略的分段降级 (Cascade Classification)
1. **优先正则/关键字匹配**：极低成本、极高速度。
2. **轻量级 Embedding 匹配**：预先对各类意图做好描述向量，提取用户输入的向量，计算最高余弦相似度。
3. **大模型 Prompt 显式抽取**：成本最高，如果前面都不命中，则用 LLM 强制指定 `ResponseFormat(JSON)` 解析出分类树。

---

## 四、决策的归宿：通用路由算法 (Routing Algorithms)

**定位**：有了准确的 **分类结果** 和 **Token 容量监控**，进行最终的执行派发 (Dispatch)。

### 4.1 语义路由器 (Semantic Router)
不同于传统的基于正则表达式的 URL 路由，大模型应用完全基于“意图语义向量”或“多参数评估”进行导向。

```python
class RoutingDecision(BaseModel):
    target_node: str         # 去哪个 Agent / 哪个步骤
    confidence: float        # 信心指数
    reasoning: str | None    # 决策理由 (如果是 CoT 路由)
```

### 4.2 经典的路由模式支持
1. **基于知识库标签的路由 (KB / Graph Router)**
    用户输入 → 实体提取 → 命中「HR 领域」→ 路由查询到 `hr_kb_vector` 与 `hr_neo4j` 图谱。这种路由基于静态特征。
2. **多智能体选择器 (Swarm Supervisor Router)**
    用户输入 → 判断为「想修改代码并建个 PR」→ 降级查询 `RagAgent` 是否能拿代码库结构 → 主控权移交 `CodeAgent`。这种被称为动态责任链路由。
3. **Token 容量感知降级路由 (Token-Aware Fallback Router)**
    监控到目前剩余可用 Token (上限 128k - 占用 120k = 8k)。触发降级路由：不再将问题抛给会产生大量中间结果的 `GraphRetrievalStep`，直接要求走 `Vector` + `Semantic Caching` 并强迫截断历史返回摘要。

---

## 五、横向融合：在系统各处的统一落脚点

将这三大共通算法封装于底层库（如 `app.core.algorithms`），并在外层服务注入：

* **RAG 入库 (`Ingestion`)**: 使用 Tokenizer 分割，使用 Classifier 打标签。
* **RAG 检索 (`Retrieval`)**: 使用 Router 定位目标图谱或向量子库，使用 Classifier 断定重写意图（是否需要 HyDE）。
* **记忆系统 (`Memory`)**: 使用 Tokenizer 获取滑动窗口体积，使用 Classifier 为记忆定“温度”和关键 Entity，过载时使用 Summarization Router 折叠数据。
* **联邦协调 (`Swarm`)**: Supervisor 完全由 Router + Classifier 构建起中央脑，管理后续 Agent。

---

## 六、下一步实现路径 (Implementation TODO)

1. [x] **建立 Core 目录**：将现有的分散路由逻辑 (e.g., `orchestrator.py` 中的意图解析, `steps.py` 中的 json 解析) 重构成高度泛化的组件（`TokenService`, `SemanticRouter`, `CascadeClassifier`）。
2. [ ] **依赖注入化 (DI)**：将通用的服务以依赖的形式让各个层的组件按需调用。
3. [ ] **制定指标与评估 (Eval)**：因为它们成为独立的核心能力，我们现在可以通过 M2.1E (RAGAS / Eval) 建立“意图识别准确率”、“路由命中率”的标准数据集，杜绝牵一发而动全身。
