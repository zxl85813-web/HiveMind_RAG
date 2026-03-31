# 🧠 HiveMind 动态图谱记忆体系 (Dynamic Graph Memory)

> **核心定位**: 基于 Neo4j 图谱实现的两种超级 AI 能力 —— **Hybrid GraphRAG (全知架构检索)** 与 **Agent Style Memory (智体风格偏好记忆)**。本系统通过实体关联与反思注入，从根本上解决大模型遗忘代码风格与缺乏架构上下文的问题。

---

## 🚀 核心能力一：Hybrid GraphRAG 混合图谱增强检索
突破传统的 “单纯向量文本匹配”，赋予 RAG 强大的“架构跳跃扩展”能力。

### 1.1 它是如何工作的？
- **触发入口**: `RAGGateway.retrieve_for_development` (位于 `backend/app/services/rag_gateway.py`)。
- **混合逻辑**: 
  1. 依据用户的自然语言 Query (如 "knowledge") 或底层向量检索匹配的文件名寻找图谱中的起点。
  2. 使用 Cypher 自动向外扩展 1-2 跳，查询围绕起点的架构关系树。
  3. 将诸如 `[:MAPPED_TO_CODE]`, `[:DEPENDS_ON]`, `[:DEFINES_MODEL]` 等关系，以超级片段 (`[GraphRAG Context]`) 的形式组装回提示词，赋予 `Score: 0.95` 最高展示权重。

### 1.2 本地测试效果演示
通过执行 `python backend/scripts/test_graphrag.py` 验证：
```text
🚀 Testing Hybrid GraphRAG Query
--------------------------------------------------
Query: 'knowledge'
✅ Response Strategy: hybrid-graphrag
✅ Total Found: 15

Fragments Returned (Top Highlights):
 [Score: 0.95] [GraphRAG Context] ArchNode(backend/app/models/knowledge.py) -[DEFINES_MODEL]-> ArchNode(KnowledgeBase)
 [Score: 0.95] [GraphRAG Context] ArchNode(backend/app/api/routes/knowledge.py) -[EXPOSES_API]-> ArchNode(POST /api/v1/knowledge)
 [Score: 0.95] [GraphRAG Context] ArchNode(frontend/src/store/knowledgeStore.ts) -[DEPENDS_ON]-> ArchNode(frontend/src/api/knowledge.ts)
```
*这保证了编排器分配 Agent 任务时，AI 对某个文件的周边依赖关系了若指掌，代码生成极难出错。*

---

## 🎭 核心能力二：Agent Style Memory (智体编程风格记忆)
让 AI 开发者的产出充满你的“个性编码洁癖”。针对不同的具体干活 Agent (Worker)，单独记忆和注入诸如注释粒度、命名规则等用户偏好。

### 2.1 它是如何工作的？
由 `backend/app/services/memory/tier/graph_index.py` 内的两个核心方法承载：
- **记忆提取与写入 (Write)**: `record_agent_preference(agent_name, user_feedback)` 运用大模型 (LLM) 获取并分类用户的吐槽或严格指令，生成 `CognitiveAsset {type: 'Preference'}` 偏好节点，并通过 `[:FOLLOWS_STYLE]` 并附加置信度权限将它和指定 `IntelligenceNode` 智体建立永久纽带。
- **启动时注入 (Read)**: `get_agent_preferences(agent_name)` 会在每次分发某个 Agent 开工前触发，将超过信任阈值 (0.5) 的偏好拉出，并塞进它的 `System Prompt` 绝对铁律集里。

### 2.2 本地测试效果演示
通过执行 `python backend/scripts/test_agent_memory.py` 验证记忆提取流程：
```text
🧠 Testing Agent Style Memory Extraction & Retrieval
--------------------------------------------------
User Feedback: 'I noticed you didn't add comments. From now on, all TypeScript components MUST have detailed JSDoc comments explaining the props and return values. Also, strictly use camelCase for variables.'

... Extracting via LLM and storing to Neo4j for agent 'ReactFrontendCoder' ...
2026-03-31 05:55:21 | INFO | 🧠 Tier-2 Indexed 2 style preferences for agent 'ReactFrontendCoder'.

... Retrieving stored preferences from Neo4j ...

✅ Found injected preferences for System Prompt:
  - [COMMENT_STYLE] All TypeScript components MUST have detailed JSDoc comments explaining the props and return values.
  - [NAMING] Strictly use camelCase for variables.
```

### 2.3 直观效果对比 (Before vs After)
为了更直白地理解记忆注入的核心价值，我们来看面对同一个需求，Agent 在 **无记忆** 和 **有记忆** 状态下的天壤之别：

**任务需求**: “写一个简单的用户信息提取组件。”

#### 🔴 Without Memory (无记忆的初始 AI)
大模型会依赖预训练权重随便写一段功能正确的代码，**完全无视你的架构与注释洁癖**：
```typescript
interface props {
  id: string; // 只有干巴巴的定义
}

export const user_profile = ({id}: props) => {
  return <div>{id}</div>; // 蛇形命名 (Snake Case)，零注释
}
```

#### 🟢 With Agent Graph Memory (开启记忆注入的大师)
编排器在动笔前，一秒钟去 Neo4j 里查出了你的“底线法则”，并写进了系统提示词。此刻 AI 的产出瞬间带上了 **你的“个性基因”**：
```typescript
/**
 * UserProfileComponent
 * 
 * 获取并渲染特定用户的详情展示区块。
 * 
 * @param {string} userId - 全局系统中的唯一用户识别符 (遵循 Graph Rule: JSDoc 必须详细描述 props)
 * @returns React.ReactElement
 */
interface UserProfileProps {
  userId: string; 
}

// 遵循 Graph Rule: 强制要求 camelCase 命名法则
export const userProfileComponent = ({ userId }: UserProfileProps) => {
  return <div className="userProfileCard">{userId}</div>;
}
```
*对比可见：有了图谱记忆，你再也不需要在每个新任务里反复唠叨“注意命名和加注释”。图谱就是你开发规范的影子架构师。*

### 2.4 深度架构级优势比对 (Graph Memory vs Static Prompts / Spec)
如果要向团队阐述我们不使用传统的硬编码 `prompt.md` 或者超长的 `spec.yaml`，而选用 Neo4j 动态图谱记忆的原因，可以从以下四大维度进行降维对比展示：

| 演进维度 | 🔴 传统 Spec / 静态 Prompt 体系 | 🟢 Agent Graph Memory (动态图谱记忆) |
| :--- | :--- | :--- |
| **更新频率 (维护)** | **被动修改**：每次踩坑必须由人类去文件末尾加一行规矩，日积月累变成上千行的“无脑念经档”。 | **动态进化**：在 Review 或聊天时吐槽一句，底层 Reflection 自动提炼、建图。这是在真正的“结对编程”中自然成长。 |
| **注意力分配 (性能)** | **塞爆上下文**：不管干啥都要让 AI 读一遍全套《团队架构指南》，不仅极度浪费 Token，还会引发著名的 AI 遗忘症 (Lost in the Middle)。 | **JIT 精准注入**：在 Neo4j 中沿着 `[:FOLLOWS_STYLE]` 召回。干前端的 AI 只被注入 CSS 和 TypeScript 铁律，干后端的全看不见。精准且致命。 |
| **局部作用域 (绑定)** | **扁平文本**：极难设定“只在给 `auth.py` 加代码时才遵守本规则”，通用指令经常导致整个项目的“误伤”。 | **多维解耦绑定**：偏好可以直接通过图谱连线 `[:APPLIES_TO]` 强行绑定在某个业务模块节点甚至具体的 `CodePrimitive` 节点上，实现微操控制。 |
| **错误迭代 (更新)** | **规则冲突**：当开发标准变更，必须人工翻遍原文件去删改，否则两个冲突指令会让大模型“精神分裂”。 | **权重自愈 (Decay)**：基于置信度 (`confidence`) 和时间戳的模型。最新、被反复提及的偏好天然压制旧有认知，拥有自我修正的新陈代谢。 |

*一句话总结：写在文件里的 Spec 只是给 AI 发了一本《员工纪律手册》；长在图谱里的 Memory 则是一个懂你心思的“克隆人老员工”。*

---



## 🎯 系统应用接入指南 (Integration Guide)

### 1. 开发调度时的使用方法
当正在搭建一个新的大模型对话 Worker，在生成给 LLM 的系统指令前：
```python
from app.services.memory.tier.graph_index import graph_index

agent_name = "ReactFrontendCoder"

# 1. 查询图谱长期记忆
style_rules = await graph_index.get_agent_preferences(agent_name)

# 2. 组装为神圣不可违背的格式
if style_rules:
    system_rules = "You MUST strictly adhere to the following learned styles from past user interactions:\n"
    system_rules += "\n".join(style_rules)
    base_system_prompt += f"\n\n[LONG-TERM MEMORY]\n{system_rules}"
```

### 2. GraphRAG 增强搜索的使用方法
如果你在为一个需要全系统理解上下文的 Agent 获取 RAG 片段：
```python
from app.services.rag_gateway import RAGGateway

rag = RAGGateway()
response = await rag.retrieve_for_development(
    query="Auth modules handling token generation", 
    kb_ids=["kb-backend"], 
    strategy="hybrid",
    include_graph=True # 👈 确保此处设为 True 即可开启上帝架构跳跃
)
```

## 🏗️ 进阶用例三：架构治理 —— 技术债热力图 (Timebomb Detection)

基于图谱中的 `DEPENDS_ON` (依赖) 与 `VERIFIES` (测试验证) 关系，我们可以实现精准的架构排雷。

### 3.1 核心逻辑
通过 Cypher 查询找出具备以下特征的“定时炸弹”：
1. **高耦合 (High Coupling)**: 被大量其他组件依赖（图入度中心性高）。
2. **零测试 (Zero Tests)**: 在图谱中没有任何关联的测试节点。

### 3.2 扫描报表展示
执行 `python backend/scripts/detect_timebombs.py` 即可获得：

| Severity | Component | Type | Coupling Score | Test Count |
| :--- | :--- | :--- | :--- | :--- |
| 💣💣 | GET:/api/v1/knowledge | APIEndpoint | 3 | 0 (Uncovered) |
| 💣 | TodoItem | DatabaseModel | 1 | 0 (Uncovered) |
| 💣 | User | DatabaseModel | 1 | 0 (Uncovered) |

*这为团队提供了比单纯代码覆盖率更具“架构意义”的测试补全优先级建议。*

---
有了此体系，不论你的代码库如何膨胀，Neo4j 皆能忠诚地**“记住你的好、看透整个局”**。
