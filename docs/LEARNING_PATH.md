# 🎓 Agent RAG 边做边学路径

> 本文档不是又一份 "概念扫盲"。
> 它是一张**以本项目代码为课本**的学习地图——每一个概念都对应一个你可以立刻打开、运行、修改的文件。
> "读文档" 是听课，"改代码" 才是真正的学。

---

## 如何使用这份路径

```
不要全部读完再动手。
选一个模块 → 读概念（2 分钟）→ 找到对应代码（5 分钟）→ 改一行试试效果（10 分钟）→ 理解为什么。
```

难度分级：🟢 入门 | 🟡 中级 | 🔴 进阶

---

## 第一关：RAG 是什么？为什么需要它？

### 概念（2 分钟）

**RAG = Retrieval-Augmented Generation（检索增强生成）**

LLM 的知识是"考前记在脑子里的"（训练截止日）。RAG 给它一个"开卷考试"的机会：
先去文档库里查相关片段，再把片段拼到 Prompt 里让 LLM 回答。

```
用户提问
  │
  ▼
[检索器] → 从知识库找最相关的 3~5 段文本
  │
  ▼
[LLM]   ← 收到：System Prompt + 检索结果 + 用户问题
  │
  ▼
答案（有据可查，降低幻觉）
```

**没有 RAG 会怎样？** LLM 会"一本正经地胡说八道"，尤其对私有企业知识、最新信息。

### 本项目中的 RAG 在哪里？

| 组件 | 文件 | 作用 |
|:---|:---|:---|
| 检索管道 | [backend/app/services/retrieval/pipeline.py](../backend/app/services/retrieval/pipeline.py) | 串联 8 个检索步骤 |
| 向量检索 | [backend/app/services/retrieval/steps.py](../backend/app/services/retrieval/steps.py) | 从 ChromaDB 取相似片段 |
| Prompt 注入 | [backend/app/prompts/templates/agent_task.j2](../backend/app/prompts/templates/agent_task.j2) | 把检索结果嵌入最终 Prompt |

### 🟢 动手练习

打开 [backend/app/services/retrieval/pipeline.py](../backend/app/services/retrieval/pipeline.py)，
找到 `_resolve_steps()` 方法，看看 `ab_no_graph` 变体和 `default` 变体有什么区别。
思考：把图检索去掉会影响什么场景的回答质量？

---

## 第二关：检索管道的 8 个步骤

### 概念（3 分钟）

朴素 RAG 只有"向量检索"一步。生产级 RAG 需要更多：

```
用户原始问题
   │
   ▼
① QueryPreProcessingStep   — 改写、扩展、HyDE（生成假设答案再检索）
   │
   ▼
② GraphRetrievalStep       — 从 Neo4j 知识图谱取实体关系
   │
   ▼
③ HybridRetrievalStep      — 向量检索 + BM25 关键词检索二合一
   │
   ▼
④ ACLFilterStep            — 权限过滤（你没权限的文档删掉）
   │
   ▼
⑤ RerankStep               — 用重排模型重新打分，留 Top-K
   │
   ▼
⑥ ParentChunkExpansionStep — 把短 chunk 替换为父级大块（上下文更完整）
   │
   ▼
⑦ ContextualCompressionStep — LLM 压缩：只保留和问题直接相关的句子
   │
   ▼
⑧ InjectionFilterStep      — 安全过滤：删除含提示词注入风险的片段
   │
   ▼
最终 context → 注入 Prompt
```

### 关键设计：父子分块（Parent-Child Chunking）

> 这是本项目最重要的 RAG 原创设计之一，来自 [DEV_NOTES.md](../DEV_NOTES.md)

- **Child chunk**（短，~200 字）：用于 Embedding，精准匹配关键词
- **Parent chunk**（长，~1000 字）：存在 SQL DB，给 LLM 足够上下文
- 检索时用 Child 定位，返回时扩展到 Parent

**为什么这样设计？**
向量模型对短文本效果更好（避免长文本中信号被稀释），但 LLM 需要长上下文来推理。这个设计两全其美。

### 关键设计：HyDE（假设性文档嵌入）

用户的问题往往是"问句"，知识库里存的是"答句"。两者向量方向不同，
导致"问句向量"和"答句向量"语义不够对齐。

HyDE 的做法：**先让 LLM 生成一个假设性答案，再用这个假设答案去检索。**
这样检索的是"答句找答句"，准确率大幅提升。

### 🟡 动手练习

1. 在 [steps.py](../backend/app/services/retrieval/steps.py) 中找到 `ParentChunkExpansionStep`，
   理解它如何通过 `parent_chunk_id` 回查 SQL DB
2. 尝试在 `pipeline.py` 中新增一个变体 `ab_no_rerank`，去掉重排步骤，
   思考：它会让速度提升但质量下降吗？在什么场景下反而更好？

---

## 第三关：Agent 是什么？和 RAG 的区别

### 概念（3 分钟）

**RAG** = 查文档 → 生成答案（单步，确定性强）

**Agent** = 自主规划 → 选择工具 → 执行 → 观察结果 → 迭代直到完成（多步，自主性强）

```
RAG：   问题 → [检索] → [生成] → 答案

Agent： 问题
          │
          ▼
        [规划：这个问题需要什么工具？]
          │
          ├─ 需要查资料 → 调用 RAG 工具
          ├─ 需要查数据库 → 调用 SQL 工具
          └─ 需要最新信息 → 调用 Web 搜索工具
                │
                ▼
              [观察结果，是否足够回答？]
                │
                ├─ 足够 → 生成答案
                └─ 不足 → 继续下一轮工具调用
```

**本质区别**：RAG 是工具，Agent 是使用工具的决策者。
本项目的 RAG 检索管道，是 Agent 可以调用的一个工具。

### 本项目的 Agent 蜂群架构

```
用户输入
   │
   ▼
[Supervisor Agent] ← "蜂后"：意图识别 + 任务路由
   │
   ├─→ [RAG Agent]        ← 工蜂：专门查知识库
   ├─→ [Code Agent]       ← 工蜂：专门写/解释代码
   ├─→ [Web Agent]        ← 工蜂：专门联网搜索
   └─→ [Reflection Agent] ← 品控蜂：审核输出质量
```

代码入口：[backend/app/agents/swarm.py](../backend/app/agents/swarm.py)

### 🟢 动手练习

打开 [swarm.py](../backend/app/agents/swarm.py)，搜索 `class SwarmState`，
看看这个 TypedDict 里有哪些字段。
这些字段就是整个 Agent 执行过程中的"共享记忆"——每个 Agent 节点都能读写它。

---

## 第四关：LangGraph 是什么？为什么用它编排 Agent？

### 概念（3 分钟）

LangGraph 是 LangChain 出品的**状态机/有向图框架**，专为多步 Agent 工作流设计。

**为什么不用普通的函数调用链？**

| 普通函数链 | LangGraph StateGraph |
|:---|:---|
| 线性，A→B→C | 可以分支、循环、条件跳转 |
| 无法持久化中间状态 | 状态自动序列化，支持断点续传 |
| 难以实现"自我纠错" | Reflection 节点可以让流程回头 |
| 调试困难 | 每个节点输入输出可完整 trace |

**核心 API 模式（本项目实际用法）：**

```python
# 1. 定义共享状态
class SwarmState(TypedDict):
    messages: list
    current_agent: str
    prompt_variant: str   # ← 我们上次加的 A/B 实验字段
    ...

# 2. 定义节点（每个 Agent 是一个节点）
def supervisor_node(state: SwarmState) -> SwarmState:
    ...

# 3. 构建图
graph = StateGraph(SwarmState)
graph.add_node("supervisor", supervisor_node)
graph.add_node("rag", rag_agent_node)
graph.add_conditional_edges("supervisor", route_to_worker)  # 分支路由

# 4. 编译并运行
app = graph.compile()
result = await app.ainvoke(initial_state)
```

### 🟡 动手练习

在 [swarm.py](../backend/app/agents/swarm.py) 中搜索 `add_conditional_edges`，
找到 Supervisor 的路由逻辑。
试着理解：如何新增一个 "Data Analysis Agent" 节点，并让 Supervisor 能路由给它？

---

## 第五关：Prompt 工程

### 概念（3 分钟）

Prompt 工程是"让 LLM 按你期望的方式输出"的艺术。本项目有一套 4 层结构：

```
Layer 1: base/system.yaml      ← 全局安全规则、输出格式规范（所有 Agent 共用）
   +
Layer 2: agents/{role}.yaml    ← 该 Agent 专属的角色定位（RAG Agent vs Code Agent）
   +
Layer 3: templates/agent_task.j2  ← Jinja2 模板，运行时动态填充
   +
Layer 4: Runtime Context       ← 实际检索结果、对话历史、工具列表（运行时注入）
   ‖
   ▼
最终 Prompt（传给 LLM）
```

### 关键设计：Head-Tail Anchor（首尾锚定）

一个长 Prompt 中，**LLM 对中间内容的关注度最低**（Lost-in-the-Middle 现象）。
解决方案：把最重要的约束放在**开头（Head）和结尾（Tail）**重复强调。

```
[HEAD]  ← 身份定义、核心安全规则（LLM 首先读到）
  │
  ├─ Role Description
  ├─ Task Definition
  ├─ RAG Context（检索结果注入这里）
  └─ Memory
  │
[TAIL]  ← "Final Guardrails" 尾锚（LLM 即将生成时最后读到）
```

查看实现：[backend/app/prompts/templates/agent_task.j2](../backend/app/prompts/templates/agent_task.j2)
（搜索 `Final Guardrails`）

### 🟡 动手练习

1. 打开 [agent_task.j2](../backend/app/prompts/templates/agent_task.j2)，
   找到 `{{ rag_context }}` 的位置，理解检索结果是如何被嵌入 Prompt 的
2. 修改 `head_tail_v1` 变体的尾锚文字，加一条新的规则，
   然后在 Chat API 中传入 `prompt_variant: "head_tail_v1"` 测试效果

---

## 第六关：LLM 路由与多模型策略

### 概念（2 分钟）

不同任务对模型能力的需求不同：

| 任务类型 | 速度要求 | 质量要求 | 推荐 Tier |
|:---|:---|:---|:---|
| 快速问候、意图分类 | 极高 | 低 | `FAST` |
| 普通 RAG 问答 | 中 | 高 | `BALANCED` |
| 代码推理、多跳推断 | 低 | 极高 | `REASONING` |

本项目通过 `LLMRouter` 根据任务选择合适 Tier 的模型，
避免"大炮打蚊子"（浪费算力）或"小马拉大车"（质量不足）。

代码入口：[backend/app/llm/router.py](../backend/app/llm/router.py)（如存在）

### 🔴 进阶思考

什么时候应该让 **Supervisor** 使用 FAST 模型，什么时候必须用 REASONING 模型？
提示：考虑"路由本身的错误代价"——如果路由决策错了，后续所有工作全白费。

---

## 第七关：MCP 与 Skills——工具层的设计

### 概念（3 分钟）

**MCP（Model Context Protocol）**：Anthropic 提出的开放标准，定义了 AI 模型如何调用外部工具（文件系统、数据库、IDE）。类似 USB 接口——任何工具只要实现了 MCP 协议，Agent 就能直接插拔使用。

**Skills**：本项目在 MCP 之上封装的"业务能力模块"，每个 Skill 对应一类专门任务（PDF 解析、Excel 分析、Web 搜索等）。

```
[Agent]
   │ 调用
   ▼
[Skills 层]    ← 业务逻辑封装（skills/ 目录下每个文件夹是一个 Skill）
   │ 底层接入
   ▼
[MCP 层]       ← 标准工具协议（mcp-servers/ 目录）
   │
   ▼
[实际工具]     ← 文件系统 / 数据库 / 第三方 API
```

查看可用 Skills：[skills/](../skills/) 目录
查看 MCP 配置：[backend/mcp_servers.json](../backend/mcp_servers.json)

### 元技能（Meta-Skill）——会"造工具"的工具

`skills/mcp-builder/` 和 `skills/skill-creator/` 是**元技能**：
它们的能力是"生成新的 Skill 样板代码"，让系统在运行时扩展自己的能力。
这是本项目最有野心的设计之一——Agent 的自我进化。

### 🟡 动手练习

打开 [skills/web_search/](../skills/web_search/) 目录，看一个完整 Skill 的结构。
思考：如果要新增一个"代码 Review Skill"，你需要准备哪些文件？

---

## 第八关：Reflection（反思机制）

### 概念（2 分钟）

Reflection = Agent 生成答案后，**另一个 Agent 来审核它**，如果质量不达标就打回重做。

```
Worker Agent 生成答案
   │
   ▼
[Reflection Agent 审核]
   │
   ├─ 通过 → 返回用户
   └─ 不通过 → 打回 Worker，附上改进建议 → Worker 重新生成
                  │
                  └─ 最多重试 N 次（防止无限循环）
```

**为什么不直接让 Worker 生成更好的答案？**
自我审核存在"盲点"——生成者往往意识不到自己的错误。
引入独立的审核视角，模拟了人类"四眼原则"（Two-person integrity）。

查看文档：[docs/AGENT_GOVERNANCE.md](./AGENT_GOVERNANCE.md)（搜索 `Reflection`）

### 🔴 进阶思考

Reflection 会增加延迟（多一轮 LLM 调用）。
如何设计"值得 Reflection 的条件"，让它只在必要时触发？
提示：信心分数（Confidence Score）是一个方向。

---

## 学习成果检验

完成以下任务，说明你已真正内化了关键概念：

### 🟢 初级（理解层）
- [ ] 能用自己的话解释 RAG 和纯 LLM 的区别
- [ ] 能说出本项目检索管道的至少 5 个步骤和它们的必要性
- [ ] 能找到 Supervisor Agent 的路由逻辑代码

### 🟡 中级（应用层）
- [ ] 能新增一个检索管道变体（如 `ab_no_rerank`）并写单测
- [ ] 能修改 `agent_task.j2` 增加新的 Prompt 规则并在 API 中验证
- [ ] 能看懂 `SwarmState` 里的字段，并解释为什么需要共享状态

### 🔴 进阶（设计层）
- [ ] 能设计并实现一个新的 Agent 节点（如 DataAnalysis Agent）并接入 LangGraph
- [ ] 能为一个 Skill 编写完整的 MCP 接口和单测
- [ ] 能评估一次 A/B 实验结果（prompt_variant 的效果差异）并写出分析报告

---

## 深入阅读（按需）

| 想了解 | 阅读 |
|:---|:---|
| 系统整体架构 | [docs/architecture.md](./architecture.md) |
| Agent 治理机制 | [docs/AGENT_GOVERNANCE.md](./AGENT_GOVERNANCE.md) |
| 开发决策背景 | [DEV_NOTES.md](../DEV_NOTES.md) |
| 数据治理 | [docs/DATA_GOVERNANCE.md](./DATA_GOVERNANCE.md) |
| 项目路线图 | [docs/ROADMAP.md](./ROADMAP.md) |

**推荐外部资源（配合本项目理解效果更佳）：**
- LangGraph 官方文档：`langchain-ai.github.io/langgraph/`
- RAG 综述：《Retrieval-Augmented Generation for Large Language Models: A Survey》（2023）
- Prompt 工程指南：`platform.openai.com/docs/guides/prompt-engineering`
- MCP 协议规范：`modelcontextprotocol.io`
- Lost-in-the-Middle 论文：《Lost in the Middle: How Language Models Use Long Contexts》（2023）

---

> **建议**：把这份文档打开放在旁边，打开一个相关代码文件，然后开始改代码。
> 不要只是读——做一个"探索性"的修改，看看报什么错，再把它改回来。
> 这就是最快的学习方式。
