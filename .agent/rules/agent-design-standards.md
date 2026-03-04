# 🤖 Agent 蜂巢与智能开发规范 (Agent Design Standards)

> 关联文档: [`project-structure.md`](project-structure.md), [`backend-design-standards.md`](backend-design-standards.md)

本规范定义了在 HiveMind RAG 系统中，如何正确开发、注册和管理人工智能节点 (Agent)、长短期记忆 (Memory) 以及知识检索流 (RAG Pipeline)。所有涉及大模型 (LLM) 和图计算的代码均需遵循此规范。

---

## 1. 架构定位：智能层不是业务系统

### 1.1 隔离原则
Agent 并不是被前端 HTTP 直接调用的对象，它是 `Manager` 后台的“思考引擎”。
*   **严禁** 在 `app/agents/` 或 `app/services/retrieval/` 内部处理 HTTP Request/Response。
*   **严禁** Agent 直接进行未经安全校验的 `Session.commit()`。
*   Agent 获取业务数据必须走 `services/` 层，或者直接读取数据库，但**修改**重要业务状态，只能通过 Tools (工具) 携带可被审计的签名进行。

---

## 2. Agent 节点开发守则 (Node Guidelines)

系统采用 LangGraph 构建了 **SwarmOrchestrator**，这是一个带有 Supervisor（主管）的多节点状态图。

### 2.1 增加一个新的 Agent
如果你想增加一个专门处理文档总结的 `SummaryAgent`：
1.  **绝笔** 随意新建顶层类，必须在 `agents/swarm.py` 的注册中心实例化 `AgentDefinition`。
2.  必须赋予清晰的 `description`，因为这个描述是 Supervisor 决定是否把任务路由给它的依据。
3.  按需绑定 `skills` 或 MCP 工具。

### 2.2 状态流传 (SwarmState) 与记忆
*   **读写黑板**：所有 Agent 在同一个上下文中工作，通过 `SwarmState` (类似 Blackboard) 交流。
*   **记忆分层**：
    *   *工作记忆 (Working Memory)*：随单次会话滑动保持，存于 `SwarmState['messages']`。
    *   *片段/语义记忆 (Episodic/Semantic Memory)*：严禁直接在 Agent 里调 Redis，必须通过 `app.agents.memory.SharedMemoryManager` 暴露的方法存储和提取。

---

## 3. Prompt 管理规范：引擎化

禁止在 Python 代码里硬编码超长的大段文字 Prompt。
系统内置了灵活的 **PromptEngine** (`app/prompts/engine.py`)。

*   **隔离存放**：Prompt 模板必须存放在 `app/prompts/` 目录下的 YAML 或等效配置文件中。
*   **四级组装**：调用时应通过 `PromptEngine.build(...)` 根据系统级 (Base) -> 角色级 (Role) -> 任务级 (Task) -> 上下文 (Context) 动态拼装。
*   所有的 Prompt 必须用英文编写主引导，并用清晰的 Markdown 结构或 XML 标签规范输出。

---

## 4. LLM 路由策略 (Model Routing)

HiveMind 拥有多个模型可用（如 GPT-4o, Claude 3.5 Sonnet, 极速版通义等），我们采用分层调用！
不要在代码中定死 `ChatOpenAI(model="gpt-4")`。

必须使用 `LLMRouter` 并指明使用哪种 Tier：
*   `ModelTier.FAST`：用于简单的意图识别、路由判定、文本格式化。
*   `ModelTier.BALANCED`：用于主战 Agent 的对话和常规问题。
*   `ModelTier.REASONING`：用于复杂的代码生成、复杂图谱推理。

---

## 5. RAG 与检索管线安全底线 (Retrieval & Security)

HiveMind RAG 对于知识的安全与精确度有着最高的要求！当 AI 进行检索或响应时，必须遵守：

### 5.1 ACL 鉴权渗透
当 Agent 通过 Retrieval Node 调取知识点时，底层执行 `vector_store.similarity_search` 或图数据库遍历时，**必须携带当前用户的标记 (User IDs/Roles)**。
*   **要求**：必须调用 `app.auth.permissions` 的相关方法验证用户有权看到哪些 chunk_id / doc_id，不要试图用大模型做鉴权！

### 5.2 数据脱敏引擎 (Desensitization)
检索出的上下文，在喂给 LLM 前，或者 LLM 吐出的回答反馈给用户前：
*   **必须** 显式通过 `app.audit.security.engine.DesensitizationEngine` 进行拦截和掩码（基于全局配置的 `DesensitizationPolicy`）。
*    **严禁** 让未脱敏的 PII 数据（如身份证、电话、密钥）暴露在最终的 SSE 文本流中。

### 5.3 幻觉防范与快速阻断 (Fast Path)
为了保证界面的操作体验，像“跳转到配置页”这类指令，不需要大模型来判定：
*   在 Supervisor 节点开头保留并更新硬编码的 **Fast Path Keyword** 判断，精准阻截路由，返回 UI 命令 (`[ACTION: ...]`)。

---

## 6. AI 代码生成与重构纪律

如果你是一个 AI 代码生成器（比如 AntiGravity）在操作这个项目：
1. 你的职责不仅是实现功能，更要融入上述的架构模式。
2. 遇到 `utils` 缺失，去 `app/utils` 里找或者建。
3. 新增 Tool，必须把类放在 `app/skills` 或具体的插件里，通过依赖倒置提供给 Agent。
4. 任何对基石代码（如 `swarm.py` 主体结构、`deps.py`）的修改，一定要加注释解释原因。
