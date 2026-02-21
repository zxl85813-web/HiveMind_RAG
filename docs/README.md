# 📖 HiveMind RAG — 文档体系 (Documentation System)

> **文档与代码绑定，文档驱动开发。**

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
