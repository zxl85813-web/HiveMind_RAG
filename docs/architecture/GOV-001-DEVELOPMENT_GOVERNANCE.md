# 🛡️ GOV-001: HiveMind 治理体系与工程效能规范 (V1.1)

> **核心宗旨**: 以“确定性的工程边界”约束“非确定性的智体行为”，确保 HiveMind 智体蜂巢在演进中不发生架构偏航。

---

## 1. 注册驱动开发 (Registration-Driven Development, RDD)

**规则**: “无注册，不开发；无对齐，不合并”。

*   **唯一索引**: [REGISTRY.md](../../REGISTRY.md) 是 HiveMind 的物理骨架。
*   **准入流程**:
    1.  **Propose**: 新功能需在 `REGISTRY.md` 响应章节占位（状态设为 `🚧`）。
    2.  **Define**: 更新 [DES-001](../design/DES-001-FRONTEND_ARCHITECTURE.md) 以涵盖新组件的交互逻辑。
    3.  **Implement**: 开发实现并将状态更新为 `✅`。

---

## 2. 事实唯一来源 (Single Source of Truth, SSoT)

**规则**: 文档是机器可读的“认知接口”，非纯文字堆砌。

*   **文档索引化**: 所有设计（DES）必须挂载在 `docs/architecture/README.md` 下。
*   **低熵管理**: 归档冗余信息，保持工作区对 Agent 的高性能读写亲和力。

---

## 3. Schema 驱动的认知治理 (Schema-First)

**规则**: 指标是系统自我进化的“第一语料”。

*   **前端校验**: 通过 Zod 确保遥测数据符合 HMER 审计契约。
*   **后端感知**: 检索接口必须支持 `is_prefetch` 预感应协议。
*   **HMER (AI Architecture Metric)**: 强力驱动架构质量审计，利用 AI 审计员对每一次 Phase 做准出判断。

---

## 4. 蜂群协作与 Agent 交互规范

**规则**: 为 Agent 的每一次推理提供确定的环境。

*   **Agent 指令亲和性**: 组件实现应保持高可测性，方便 Subagent 无痛执行 TDD。
*   **错误自愈**: 强调 `ErrorBoundary` 与 `ResilientStream` 机制。

---
> _“代码会腐蚀，但由严密治理构建的智体蜂巢，将随着数据的汇聚而愈发强大。”_
