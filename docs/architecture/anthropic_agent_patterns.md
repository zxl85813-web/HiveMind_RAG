# 🧬 Anthropic Agent 工程模式参考手册
# HiveMind RAG × Anthropic Best Practices Integration

> **来源**: 15 篇 Anthropic 官方工程博客的系统性提炼  
> **作用**: 作为 HiveMind RAG 架构演进的技术参考基准  
> **创建日期**: 2026-03-05  

---

## 一、总体架构模型

Anthropic 提出的 Agent 系统分为 **Workflows (编排流)** 和 **Agents (自治体)** 两大类：

| 类别 | 控制权 | 适用场景 | HiveMind 对应 |
| :--- | :--- | :--- | :--- |
| **Prompt Chaining** | 代码控制 | 固定步骤的 Pipeline (如：解析→分块→索引) | `PipelineExecutor` |
| **Routing** | 代码控制 | 意图分类后走不同分支 | `Supervisor Fast Path` |
| **Parallelization** | 代码控制 | 安全检查 + 核心任务并行 | `DesensitizationEngine` ∥ `IndexingService` |
| **Orchestrator-Workers** | LLM 动态 | 不可预测的子任务分解 | `SwarmOrchestrator + Agent Nodes` |
| **Evaluator-Optimizer** | LLM 循环 | 迭代式改进输出质量 | `Reflection Node` |
| **Autonomous Agent** | 完全自治 | 开放式任务探索 | `Long-Horizon Agent (TODO)` |

> **核心原则**: 永远从最简单的 Workflow 开始，只在任务确实需要灵活性时才升级为 Agent。

---

## 二、Agent 核心反馈循环

```
┌──────────────────────────────────────────────┐
│           Agent Core Loop                     │
│                                               │
│   ┌─────────┐   ┌──────────┐   ┌──────────┐ │
│   │ Gather  │──▶│  Take    │──▶│ Verify   │ │
│   │ Context │   │  Action  │   │  Work    │ │
│   └─────────┘   └──────────┘   └──────────┘ │
│        ▲                             │        │
│        └─────────────────────────────┘        │
│                 (Repeat)                      │
└──────────────────────────────────────────────┘
```

### 2.1 Gather Context (获取上下文)

| 策略 | 技术 | 优点 | 缺点 | HiveMind 状态 |
| :--- | :--- | :--- | :--- | :--- |
| **Agentic Search** | `grep`/`glob`/`head` 文件探索 | 精准、透明、无索引维护 | 较慢 | ⬜ 待实现 |
| **Semantic Search** | Vector + BM25 Hybrid | 快速、支持语义 | 需维护索引 | ✅ 已实现 |
| **Contextual Retrieval** | 分块前注入文档背景 | 召回率 +49% | 索引成本略增 | ⬜ 待实现 |
| **Subagents** | 并行子Agent分头搜索 | 大规模过滤 | 协调复杂 | ⬜ 待实现 |
| **Compaction** | 自动总结旧消息 | 防止 Token 爆炸 | 可能丢失细节 | ⬜ 待实现 |

### 2.2 Take Action (执行动作)

| 策略 | 技术 | 优点 | HiveMind 状态 |
| :--- | :--- | :--- | :--- |
| **Tool Calling** | 标准工具调用 | 简单直观 | ✅ 已实现 |
| **Dynamic Tool Loading** | `defer_loading` 按需加载 | 节省 90%+ Context | ⬜ 待实现 |
| **Programmatic Execution** | Agent 写代码批量编排工具 | 降低延迟 98.7% | ⬜ 待实现 |
| **MCP Code Mode** | 通过文件系统暴露 MCP 工具为代码 API | Token 节省 98.7% | ⬜ 待实现 |
| **Think Tool** | 显式推理工具 | 提高复杂任务决策准确率 | ⬜ 待实现 |

### 2.3 Verify Work (验证输出)

| 策略 | 技术 | 优点 | HiveMind 状态 |
| :--- | :--- | :--- | :--- |
| **Rules/Linting** | `ruff` / `mypy` / JSON Schema | 确定性、快速 | 🟡 部分 (Reflection Node) |
| **Visual Feedback** | Puppeteer 截图校验 | 捕获视觉 Bug | ⬜ 待实现 |
| **LLM-as-a-Judge** | 模型评审 | 灵活、处理主观质量 | ✅ 已实现 |
| **Multi-Grader** | Code + Model + Human 三合一 | 最全面 | ⬜ 待实现 |

---

## 三、Context Engineering (上下文工程)

### 3.1 Prompt 设计原则
- **最小信息集**: 不要塞进太多规则，找到"刚好够用"的 Goldilocks Zone。
- **结构化分区**: 用 XML 标签或 Markdown Header 分隔 `<instructions>`, `<tools>`, `<examples>`。
- **Few-shot > 规则**: 用典型示例代替大段规则描述。

### 3.2 工具设计原则
- **命名空间**: `kb_search`, `kb_create` 而非 `search`, `create`。
- **语义化返回值**: 返回 `name` 而非 `uuid`，返回 `file_type` 而非 `mime_type`。
- **Token 高效**: 支持 `response_format: "concise" | "detailed"` 参数。
- **错误信息明确**: 不返回 traceback，返回 "请尝试缩小搜索范围" 这样的指引。

### 3.3 长会话治理
- **Compaction**: 消息达到阈值时自动总结旧内容。
- **Tool Result Clearing**: 旧工具调用的原始结果被替换为摘要。
- **Structured Note-taking**: Agent 在文件系统中写日志 (`NOTES.md`)，跨会话保留关键决策。

---

## 四、评估体系 (Evals)

### 4.1 评分器类型

```
┌─────────────────────────────────────────────────┐
│              Multi-Grader System                 │
│                                                  │
│  ┌─────────────┐ ┌──────────────┐ ┌───────────┐│
│  │ Code-based  │ │ Model-based  │ │  Human    ││
│  │ (pytest,    │ │ (LLM Rubric, │ │ (Expert   ││
│  │  linter,    │ │  pairwise    │ │  spot-    ││
│  │  schema)    │ │  comparison) │ │  check)   ││
│  └─────────────┘ └──────────────┘ └───────────┘│
│       ▲                ▲               ▲        │
│       └────────────────┴───────────────┘        │
│            Weighted / Binary Scoring             │
└─────────────────────────────────────────────────┘
```

### 4.2 评估策略
- **Capability Evals**: 针对弱点爬坡（初始 Pass Rate 低），持续改进。
- **Regression Evals**: 保护已有能力（Pass Rate 必须 ~100%）。
- **环境隔离**: 每次 Eval 从零开始，禁止残留 Git 历史/缓存。
- **评判输出而非路径**: 不要要求 Agent 必须按特定步骤出结果。

---

## 五、安全与生产治理

### 5.1 沙箱模型
```
┌────────────────────────────────────────┐
│          Sandboxed Runtime             │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │  Filesystem Isolation            │  │
│  │  - Read/Write: ./workspace       │  │
│  │  - Read-only: /tmp               │  │
│  │  - Blocked: ~/.ssh, /etc         │  │
│  └──────────────────────────────────┘  │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │  Network Isolation               │  │
│  │  - Allowed: api.openai.com       │  │
│  │  - Allowed: chroma-db:8080       │  │
│  │  - Blocked: * (all others)       │  │
│  └──────────────────────────────────┘  │
│                                        │
│  OS primitives: bubblewrap / seatbelt  │
└────────────────────────────────────────┘
```

### 5.2 生产可靠性
- **Rainbow Deployment**: 新旧版本共存，存量 Agent 不中断。
- **State Checkpointing**: LangGraph SqliteSaver 提供断点续传。
- **Shadow Evals**: 在生产流量上匿名运行质量评估。
- **Sensitivity Monitoring**: 监控决策模式（不看内容），识别死循环。

---

## 六、Skill 体系 (Agent Skills)

### 6.1 渐进式披露 (Progressive Disclosure)

```
Level 1: System Prompt (仅 name + description)
    ↓ Agent 判定相关
Level 2: 读取 SKILL.md (完整指令)
    ↓ 需要特殊场景
Level 3: 读取子文档 (如 error_handling.md)
    ↓ 需要代码执行
Level 4: 运行捆绑脚本 (如 extract_form.py)
```

### 6.2 技能自进化
- Agent 发现通用编排模式 → 自动保存为 `./skills/` 下的新 Skill。
- 包含 `SKILL.md` + 可执行脚本 + 测试用例。

---

## 七、与 HiveMind 架构的映射关系

| Anthropic 概念 | HiveMind 已有组件 | 演进目标 |
| :--- | :--- | :--- |
| Augmented LLM | `LLMRouter` + `PromptEngine` | 增加 Think Tool |
| Orchestrator-Workers | `SwarmOrchestrator` | 增加 Subagents + Code Mode |
| Compaction | ❌ | `CompactionNode` in Graph |
| Contextual Retrieval | `ChunkingStrategy` | `SituationEnrichmentStep` |
| Tool Search | `SkillRegistry` + `MCPManager` | `DeferredToolLoader` |
| Sandboxing | ❌ | `SandboxedSkillRuntime` |
| Multi-Grader Evals | `EvaluationService` (LLM only) | Code + Model + Human |
| Progressive Disclosure | `.agent/skills/` 结构已具备 | 实现 3-level 加载 |
| State Checkpointing | ❌ | `SqliteSaver` 集成 |

---

> **本文档是"知识编译"的产物** — 15 篇原始文档被解析、结构化、与 HiveMind 交叉对齐后，产出了可直接指导工程实现的"目标代码"。
