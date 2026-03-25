# 🛡️ M7 架构治理与高可用 (Architecture Governance) — 团队开发指引与学习卡片

> 本文已并入统一手册：
> [guides/collaboration_and_delivery_playbook.md](./guides/collaboration_and_delivery_playbook.md)
> 当前文件保留为阶段性记录，新增里程碑模板请更新统一手册。

> **写给小伙伴们的话:**
> 随着 HiveMind 的演进，我们不再只是追求“大模型能回答问题”，而是要把它变为一个**具有极高生产可用性 (99.99%) 和资产防腐能力的强健生态**。
> 本期的核心任务围绕“服务治理”和“代码资产库 (Code Vault)”展开。在开始敲代码之前，请务必花一些时间阅读本指引，理解背后的**设计哲学**，并熟悉相关技术栈。这不仅能避免开发走弯路，更能提升大家的架构设计思维。

---

## 🎯 任务一：Agent-Native LLM 智能路由 & 熔断器 (Backend)

**📝 任务说明：**
当前我们所有的 Agent 默认都在疯狂燃烧昂贵的商业模型（如 GPT-4o 或 Claude-3.5-Sonnet），而且一旦官方 API 宕机或被限流 (Rate Limit)，整个平台就会僵死。
我们需要开发一个类似 **ClawRouter** 的智能调度中间件：
1. **智能分流 (`llm_router.py`)**：根据输入的 Token 长度、任务复杂度，动态决定是将请求发给廉价/快速的 `Eco` 模型（如 GLM-4-flash / Llama-3-8B），还是发给昂贵的 `Premium` 模型。
2. **无缝熔断降级 (Circuit Breaker)**：在发起模型网络请求时套一层熔断器，失败或超时 3 次后自动打开熔断开关，后续请求静默回退（Fallback）到备用的本地/免费模型，保证对话不断档。

**🧠 必须掌握的知识点 & 学习搜索词：**
- **LLM Routing / Semantic Routing**：理解如何通过启发式算法或简单分类器来判断一次请求的复杂度。
  - *参考竞品*：[ClawRouter (GitHub)](https://github.com/BlockRunAI/ClawRouter)（了解其 15 维度打分机制理念）、[RouteLLM](https://github.com/lm-sys/RouteLLM)。
- **Circuit Breaker Pattern (断路器模式)**：微服务高可用经典概念。理解断路器的三种状态（Closed、Open、Half-Open）。
  - *Python 库推荐*：`pybreaker` 或 `failsafe`。了解如何在 `asyncio` 异步上下文中优雅地包裹外部请求。
- **LangChain / LangGraph 底层调度**：理解我们如何在现有的 `SwarmOrchestrator` 中劫持或介入 LLM Client 的实例化。

---

## 🎯 任务二：读写分离与 CQRS 架构切分 (Backend / Data)

**📝 任务说明：**
目前系统无论是轻量的“与用户聊天”，还是极度消耗 CPU 和 IO 的“解析 500 页 PDF 入库”，都在同一个 FastAPI 事件循环里跑。这意味着一旦有人上传了大量文件，所有正在聊天的用户都会卡顿！
我们需要贯彻 **CQRS (命令查询职责分离)** 思想，将 `Ingestion Pipeline`（写操作/计算密集）彻底从 Web API 剥离，交给后台独立的计算节点（Worker）执行。

**🧠 必须掌握的知识点 & 学习搜索词：**
- **CQRS (Command Query Responsibility Segregation)**：读写分离架构模式的概念，理解为什么它在复杂数据密集型系统中如此重要。
- **Celery + Redis / ARQ**：Python 生态下最成熟的分布式任务队列。
  - *学习目标*：如何配置 Celery App，如何将 FastAPI 中的异步函数包装成 `@celery.task` 扔到后台执行，如何查询 Task 状态。
  - *或者*：如果考虑全异步性能，可以研究 Python 的轻量级 `ARQ` 队列。
- **FastAPI BackgroundTasks vs Message Queues**：理解为什么原生的 `BackgroundTasks` 不足以应对大集群，为什么要引入外部队列（Redis）。

---

## 🎯 任务三：前端交互韧性加固 (Frontend)

**📝 任务说明：**
大模型经常返回奇奇怪怪的 Markdown 内容，或者系统偶发异常。以前一旦报错，整个 React 组件树就会随之崩溃，引发大面积“白屏”。
同时，包含几千个节点的 `ForceGraph` 知识图谱与高频的 `SSE` 聊天数据流绑定在了一起，导致聊天打字时整个图谱都在无意义地重渲染，引发严重卡顿。
我们需要通过结构分离与错误捕获，保障前端比城墙还坚固。

**🧠 必须掌握的知识点 & 学习搜索词：**
- **React Error Boundaries (错误边界)**：
  - *要点*：学习如何在遇到局部组件崩溃时展示“优雅的兜底 UI（如一个可爱的维护图标）”而不是白屏。研究第三方库 `react-error-boundary`。
- **React State Segmentation (状态树切分) & Zustand**：
  - *要点*：理解 React 的重新渲染（Re-render）机制。学习如何使用 Zustand 从顶层切分状态，避免子树的大规模无意义渲染。
  - *学习词*：`Zustand selectors`, `React.memo`, `useMemo`。
- **Debounce / Throttle (防抖与节流) 在流式 UI 中的应用**：
  - *要点*：接收长文本 SSE 流时，如何将高频的字级别刷新（每秒几百次）合并成合理的帧率更新（如 30fps），大幅度降低 DOM 树压力。

---

## 🎯 任务四：Code Vault 全景代码资产库 (Fullstack / Neo4j)

**📝 任务说明：**
这是我们针对“造轮子”现象下的重手：开发一套代码结构库。在 AI Agent 生成代码或研发同学写代码前，系统自动识别并强制推荐项目中已有的高质量 SQL 脚本或通用工具集。
最激动人心的是“**正向飞轮**”：如果你的代码被 AI 检索命中并用于成功回答了别人的问题（被点赞），你就会收到积分打赏！

**🧠 必须掌握的知识点 & 学习搜索词：**
- **AST (Abstract Syntax Tree, 抽象语法树)**：
  - *要点*：不要用正则去提取代码里的类和函数！学习使用 Python 的 `ast` 模块。如果涉及前端 TS 代码，可以了解下 `tree-sitter` 或 Babel AST。我们将编写专门的 `ASTParserSkill`。
- **Knowledge Graphs (知识图谱) 与 Neo4j Cypher**：
  - *要点*：理解如何用图数据库表达代码依赖树。例如：`MATCH (d:Developer)-[:WROTE]->(c:CodeAsset)-[:CALLS]->(u:Utils)`。
- **Semantic Hashing (语义哈希) 或 MinHash**：
  - *要点*：理解如何分辨两段长得很像的代码是否是同一个代码的微调版（发现重复造轮子）。
- **LangChain Tool Calling**：如何把这个新库接入为 Agent 的扩展能力。

---

> 🤝 **沟通建议**:
> 在深入着手这些领域前，**一定要先写好简易的技术方案草图 (RFC)**，尤其是接口名和组件流转方式。不要钻进具体的代码泥沼里忘记了我们宏观的“高可用与韧性”目标。祝咱们的生态越来越强大！🚀
