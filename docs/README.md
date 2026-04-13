# 📖 HiveMind Intelligence Swarm — 文档体系 (Documentation System)

> **文档与代码绑定，文档驱动开发。智体治理，认知先行。**

---

## 🧬 智体进化阶梯 (Intelligence Evolution Layers)

HiveMind 遵循严格的认知进化路径，每一层级都代表了自治度与治理深度的阶跃：

| 层级 | 核心特征 (Core Features) | 治理机制 (Governance) | 状态 |
| :--- | :--- | :--- | :--- |
| **L1: 助手** | 专项原子智体 (Code, Research) | 手动 Prompt 驱动 | ✅ |
| **L2: 协作** | 多代理蜂群 (Worker Swarm) | 共享黑板、Supervisor 编排 | ✅ |
| **L3: 门禁** | 自动化质量门禁 (Quality Gates) | RAGAS 评估、代码合规审计 | ✅ |
| **L4: 自愈** | **自主进化 (Autonomous)** | **失败自省、L4 过程完整性网关、异常隔离 DAG** | ✅ |
| **L5: 协同** | **共生与对冲 (Synergy)** | **跨集群辩论 (Debate)、人机统帅 (HAT)、需求定界网关** | 🚀 **MVP** |

---

## 🏗️ 核心治理原则 (L5 Architecture Mandates)

1.  **拒绝盲目讨论 (Anti-Blind Discussion)**：严禁在模糊环境下启动 Swarm。ScopingAgent 必须先进行“定界审计”，未确认背景前拒开工。
2.  **人类统帅原则 (Human Steering)**：智体可以自治，但人类拥有“元帅令”级别的逻辑截断权，可随时将发散的学术讨论拉回工程轨道。
3.  **对撞产生稳健 (Robustness via Debate)**：高阶决策必须经过并行 Swarm 的对冲与跨集群审计，由 Synthesizer 融合最终黄金路径。

---

## 🧭 智体自愈阅读顺序 (Recommended Order)

按 `L0 -> L4` 渐进式披露阅读，确保对“蜂巢架构”的深度理解：

1. **L0 系统地图**: 先读项目 [README.md](../../README.md) 与 [SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)。
2. **L1 治理基石**: 必读 [GOV-001 (开发治理与 RDD)](./architecture/GOV-001-DEVELOPMENT_GOVERNANCE.md) 与 [guides/LEARNING_PATH.md](./guides/LEARNING_PATH.md)。
3. **L2 核心设计**: 进入 [docs/design/](./design/) 查阅前端 (DES-001)、后端 (DES-003) 与测试 (DES-002) 规范。
4. **L3 架构专题**: 深入 **[docs/architecture/](./architecture/README.md)** 查阅智体协议、存储治理与 RAG 深度解构。
5. **L4 战略白皮书**: 查阅 [AI_FRONTEND_STRATEGY.md](../../AI_FRONTEND_STRATEGY.md) 了解交互哲学。

---

## 核心文档索引 (SSoT Aligned)

### 🌍 L0 系统全景
- **[SYSTEM_OVERVIEW.md](./SYSTEM_OVERVIEW.md)** — 系统的认知哲学与宏观层级说明。
- **[ROADMAP.md](./ROADMAP.md)** — 里程碑计划与 7 大进化阶段。

### 🛡️ L1 治理与协作 (Guides)
- **[GOV-001 治理规范](./architecture/GOV-001-DEVELOPMENT_GOVERNANCE.md)** — 🆕 开发准则、RDD 注册驱动。
- **[guides/LEARNING_PATH.md](./guides/LEARNING_PATH.md)** — 开发者的“智体化”学习曲线。
- **[guides/COLLABORATIVE_LEARNING.md](./guides/COLLABORATIVE_LEARNING.md)** — 自省↔互学↔共进 三环飞轮。
- **[guides/unified_development_rulebook.md](./guides/unified_development_rulebook.md)** — 统一研发准则手册。
- **[Back-end Standards](./conventions/BACKEND_STANDARDS.md)** — 🐍 后端工程规范。
- **[Front-end Standards](./conventions/FRONTEND_STANDARDS.md)** — ⚛️ 前端工程规范。

### 🏗️ L2 需求与深度设计
- **[docs/requirements/](requirements/)** — REQ 系列功能需求。
- **[docs/design/](design/)** — DES 系列设计说明书（核心：DES-001/002/003）。

### 📐 L3 架构专题图谱
- **[docs/architecture/README.md](./architecture/README.md)** — **权威索引：含存储治理、Agent Swarm、记忆压缩等 18+ 专篇。**
- **[docs/architecture/decisions/](architecture/decisions/)** — ADR 技术选型记录。

### 📝 L4 演进与存档
- **[docs/changelog/archive/](changelog/archive/)** — 历史治理文档与阶段性材料归档。
- **[REVIEW_GUIDELINES.md](./reviews/REVIEW_GUIDELINES.md)** — 🆕 代码评审准则中心。
- **`docs/reviews/`** — 历次代码与架构评审快照。

---

## 🏗️ 空间结构 (Reality-Based V2.0)

```
docs/
├── architecture/              # 📐 深度架构专题 (L3 层级)
│   ├── GOV-001-...            # 开发治理规范
│   └── README.md              # 👈 架构导航地图
│
├── design/                    # 🏗️ 专题设计文档 (L2 层级)
│   ├── DES-001-FRONTEND.md    # 前端权威设计
│   ├── DES-003-BACKEND.md     # 后端核心整合
│   └── ...
│
├── guides/                    # 📚 治理与协作指南 (L1 层级)
│   ├── LEARNING_PATH.md       # 学习路径
│   └── COLLABORATIVE_LEARNING # 共学体系
│
├── changelog/                 # 📝 变更日志
│   └── archive/               # 🆕 过时文档归档库
│
└── README.md                  # 📖 你当前所在的位置 (智体入口)
```

---
> _“文档不只是记录，它是智体蜂巢的数字化记忆。”_
