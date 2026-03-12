# 📚 核心算法的开源参考与技术选型指南 (Open Source References & Tech Selections)

为了支撑我们在 `core_routing_classification_design.md` 中提出的 **分词器/切块**、**智能分类**和**动态路由**的设计目标，我们不应该从零开始造轮子。业界已经有一些现象级开源项目完美契合我们当前的需求。

以下是对当前市面上最前沿的库与方法的调研报告，供我们在 Phase 5 重构时直接引入或剥离借鉴。

---

## 🚦 1. 动态智能路由 (Semantic Routing)

传统的路由通过提示词（Prompting）大模型，让模型输出 JSON 来决定去向。这种方式**速度慢、成本高、幻觉多**。现代框架倾向于将路由转换为“向量空间比较”。

### 强烈推荐：`aurelio-labs/semantic-router` (Semantic Router)
- **GitHub**: [aurelio-labs/semantic-router](https://github.com/aurelio-labs/semantic-router)
- **核心理念**：通过将不同代理 (Agent) 的意图转化为“语料块”并映射为快速聚合的 Embedding 向量。路由时不调用生成 API，而是使用超低延迟的 Encoder（如 FastEmbed / Cohere）对比余弦相似度，匹配上了就直接路由，百毫秒内解决战斗。
- **与我们的结合点**：
  > 可以在 Swarm Orchestrator (`app.agents.swarm`) 中，引入 `RouteLayer` 作为 Supervisor 的首选判别引擎，而不再依赖 LLM 推理。只有当 Semantic Router 信心不足时，才 Fallback（降级） 回大模型判断。

### 替代方案：`vllm-project/semantic-router`
- 更偏向底层的深度架构路由器，集成在 vLLM 生态内，提供系统的 "Mixture-of-Models" (MoM)，适合当你真的部署了十几个开源集群时的流量硬路由。对我们当前单体架构来讲，Aurelio 大概更合适，但也值得保持关注。

---

## ✂️ 2. 上下文记忆压缩与分词 (Token Budgeting & Compression)

如何对付膨胀的上下文 (Lost-in-the-middle) 以及庞大的 token 开销？除了我们在代码层面自己写的滑动窗口外，以下开源库是工业级的标准。

### 强烈推荐：`microsoft/LLMLingua` (LLM 提示词压缩器)
- **GitHub**: [microsoft/LLMLingua](https://github.com/microsoft/LLMLingua)
- **核心理念**：利用一个小参数量模型（例如 LLaMA-2-7B 或更小的专有模型）对庞大的 Prompt 进行计算，根据困惑度 (Perplexity) **剔除那些不影响整体语义的助词、废话和冗余修饰词**，甚至可以做到将 10,000 Token 压缩为 1,000 Token，而大模型的回答质量基本不变。最新的 `LLMLingua-2` 基于 GPT-4 蒸馏提速 3~6 倍。
- **与我们的结合点**：
  > 我们的 Tier 3 (原始 Vector Chunks) 在召回多篇文档时会消耗海量 Tokens。在装配 Prompt 时送入 LLMLingua 层压缩一轮，可以完美达成 `memory_compression_design.md` 中的“长尾截断/抽取式压缩”。

### 基础基座：`tiktoken`
- 由 OpenAI 提供。所有长度检查（滑动窗口拦截）应该一律收拢在底层用 tiktoken ( `enc.encode()` ) 计算。

---

## 🗂️ 3. 结构化分类与抽取引擎 (Classification & Extraction)

如何稳定地让 LLM 抽取分类结果 (如 Fact vs. Summary)、提取领域标签 (Tags)，而不产生幻觉崩溃？

### 强烈推荐：`jxnl/instructor`
- **GitHub**: [jxnl/instructor](https://github.com/jxnl/instructor)
- **核心理念**：基于 Python 原生的 `Pydantic` 模型对 OpenAI 等支持 API 接口的模型进行极大强化的工具。相比 LangChain 庞杂的输出解析链，Instructor 只做一件事：**强迫 LLM 的输出完美吻合你定义的 Pydantic 类**。
- **与我们的结合点**：
  > 我们的 `QueryPreProcessingStep` 和未来的 Tier 1 Memory（Abstract Index 构建）强依赖分类与标签提取。
  > 引入 Instructor 可以将下面这段不可靠的代码：
  > `json.loads(await llm.chat_complete(...))` 
  > 彻底替换为安全、带自动重试与纠错功能的类型安全写法。

### 语义分块推荐方案：`Semantic Chunker` 
- 在 LangChain (`langchain_experimental.text_splitter.SemanticChunker`) 和 LlamaIndex (`SemanticSplitterNodeParser`) 中均有现成实现。
- **核心理念**：它摒弃了盲目按字符长度切分（如 `RecursiveCharacterTextSplitter`），改为计算相邻句子的 Embedding 相似率分水岭，当句子间聊的话题变了（相似度剧降），就在那里切一刀。
- **与我们的结合点**：
  > 这就是我们 `Sub-Document/Parent-Child Splitter` 所需的基础设施，在入库时极大程度提升未来检索的精准度。

---

## 💡 落地实施建议路线

针对这四个神器，建议的集成顺序为：

1. **`tiktoken` & `jxnl/instructor` (高回报，低折腾)**
   - **操作**：新建 `TokenService` 使用 `tiktoken`；重构所有分类与提炼代码使用 `instructor` 裹挟 Pydantic。这能瞬间把运行时错误率降至极低。
2. **`aurelio-labs/semantic-router` (架构大优)**
   - **操作**：抽离硬编码的判断意图代码。让 Agent Swarm 使用向量比对实现超高速分发路由。
3. **`microsoft/LLMLingua` (攻坚挑战)**
   - **操作**：虽然效益极大，但需要在我们后端的运行环境中引入并常驻跑一个小 Transformer 模型（或通过远程调 API 解决）。可以在 RAG 上下文常常爆掉时正式将其引入 `chat_service.py` 环节。

这些开源库已经受过生产环境的考验，拥抱这些组件完全符合我们构建高可靠 Enterprise RAG 的长远目标。
