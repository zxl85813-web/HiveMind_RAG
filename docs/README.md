# 📖 HiveMind RAG — 文档体系 (Documentation System)

> **文档与代码绑定，文档驱动开发。**

## 渐进式披露阅读顺序（推荐）

按 `L0 -> L4` 阅读，避免直接跳进实现细节导致理解断层：

1. `L0 系统地图`：先读 [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md) 与 [architecture.md](./architecture.md)
2. `L1 能力地图`：再读 [AGENT_GOVERNANCE.md](./AGENT_GOVERNANCE.md)、[DATA_GOVERNANCE.md](./DATA_GOVERNANCE.md)、[DEV_GOVERNANCE.md](./DEV_GOVERNANCE.md)
3. `L2 流程地图`：进入 [LEARNING_PATH.md](./LEARNING_PATH.md) 的章节化流程说明
4. `L3 实现地图`：根据每章代码锚点跳到 `backend/app/...` 与 `skills/...`
5. `L4 证据层`：用 `backend/tests/`、`docs/reviews/`、`docs/changelog/` 做验证与回归

执行原则：每一层都要能回答 4 个问题

- 上层来源是什么
- 代码实现在哪里
- 测试证据在哪里
- 下一层深挖入口是什么

## 核心文档索引（已同步）

### L0 系统地图

- [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)
- [architecture.md](./architecture.md)
- [ROADMAP.md](./ROADMAP.md)

### L1 能力治理

- [AGENT_GOVERNANCE.md](./AGENT_GOVERNANCE.md)
- [DATA_GOVERNANCE.md](./DATA_GOVERNANCE.md)
- [DEV_GOVERNANCE.md](./DEV_GOVERNANCE.md)
- [guides/collaboration_and_delivery_playbook.md](./guides/collaboration_and_delivery_playbook.md)
- [LEARNING_PATH.md](./LEARNING_PATH.md)

### L2 需求与设计

- `docs/requirements/`（REQ 系列）
- `docs/design/`（专题设计）

### L3 架构专题

- `docs/architecture/`（分层架构、分支策略、工作流等）
- `docs/architecture/decisions/`（ADR 记录）

### L4 证据与演进

- [changelog/CHANGELOG.md](./changelog/CHANGELOG.md)
- `docs/changelog/devlog/`
- `docs/reviews/`

## 候选归档区（待确认）

以下文档偏向阶段性材料，建议按“保留/归档/删除”做一次决策：

- [TEAM_TASK_GUIDE_M7.md](./TEAM_TASK_GUIDE_M7.md)
- [team_collaboration_guide.md](./team_collaboration_guide.md)
- [github_advanced_integrations.md](./github_advanced_integrations.md)

建议策略：

- 若仍在执行，保留并补充“最近更新时间”和“适用范围”
- 若阶段已结束，移动到 `docs/changelog/devlog/` 或新增 `docs/archive/`
- 若内容已被其他文档覆盖，直接删除

---

## 文档体系结构

```
docs/
├── requirements/              # 📋 需求文档 — 从对话中提取
│   ├── REQ-001-agent-swarm.md
│   ├── REQ-002-shared-memory.md
│   └── ...
│
├── design/                    # 🏗️ 设计文档 — 架构与方案
│   ├── architecture.md        # 整体架构
│   ├── DES-001-agent-swarm.md
│   └── ...
│
├── api/                       # 🔌 API 文档
│   ├── overview.md            # API 总览
│   ├── chat.md                # 对话 API
│   ├── knowledge.md           # 知识库 API
│   ├── agents.md              # Agent API
│   ├── websocket.md           # WebSocket 协议
│   └── learning.md            # 外部学习 API
│
├── guides/                    # 📚 开发指南
│   ├── getting-started.md     # 快速开始
│   ├── backend-guide.md       # 后端开发指南
│   ├── frontend-guide.md      # 前端开发指南
│   └── skill-development.md   # Skill 开发指南
│
├── changelog/                 # 📝 变更日志
│   ├── CHANGELOG.md           # 版本变更记录
│   └── decisions/             # 架构决策记录 (ADR)
│       ├── ADR-001-sse-ws-hybrid.md
│       └── ...
│
├── reviews/                   # 🔍 评审记录
│   ├── REVIEW-v0.1.md
│   └── ...
│
└── README.md                  # 文档索引
```

## 文档编号规则

| 类型 | 前缀 | 示例 |
|------|------|------|
| 需求文档 | REQ-NNN | REQ-001-agent-swarm.md |
| 设计文档 | DES-NNN | DES-001-agent-swarm.md |
| 架构决策 | ADR-NNN | ADR-001-sse-ws-hybrid.md |
| 评审记录 | REVIEW-vX.Y | REVIEW-v0.1.md |

## 文档与代码绑定

每份文档和相关代码通过**交叉引用**绑定：

- 文档中引用代码: `实现: backend/app/agents/swarm.py > SwarmOrchestrator`
- 代码中引用文档: `参见: docs/requirements/REQ-001-agent-swarm.md`
- 均在 REGISTRY.md 的 traceability 表中记录
