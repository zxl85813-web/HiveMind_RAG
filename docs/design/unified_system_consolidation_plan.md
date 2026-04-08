# 🚀 HiveMind 系统开发工具与框架整合统一执行计划 (Consolidation Plan)

> **版本**: 1.0
> **目标**: 将碎片化的开发工具、脚本、文档和 DevOps 流程整合为统一的 **HiveMind DevKit Platform**，实现“从灵感至代码的全生命周期智理”。

---

## 📅 阶段划分 (Phased Roadmap)

### Phase 1: 核心底座与 AI 护栏标准化 (Framework & Harness Hardening)
*   **目标**: 确立统一 SDK，植入 AI 开发的安全护栏。
*   **核心任务**:
    - [ ] **1.1 SDK 物理整合**: 创建 `backend/app/sdk/`，封装 `core`, `common`, `utils`。
    - [ ] **1.2 护栏引擎 (Harness Engine)**: 实现 `sdk/harness/`，集成 Token 熔断、安全沙箱和变更验证逻辑。
    - [ ] **1.3 OpenSpec 原生化**: 开发针对 `openspec/` 的核心解析层，使其作为系统的“真理源”。
    - [ ] **1.4 统一 Bootstrap**: 实现 `app/init/` 逻辑，处理智体运行时的冷启动。

### Phase 2: 命令中心化与智体协同 (Unified CLI & Agentic Swarm)
*   **目标**: 建立 AI 与开发者共用的标准入口。
*   **核心任务**:
    - [ ] **2.1 `hm` CLI (The Commander)**: 封装 80+ 个脚本，支持 `hm spec apply`, `hm doctor`, `hm eval`。
    - [ ] **2.2 自动注册 (Dynamic Registry)**: 代码装饰器联动，实现 `REGISTRY.md` 与图谱的 100% 同步。
    - [ ] **2.3 移交协议 (Swarm Handover)**: 标准化 Agent 间的 Spec 传递协议。

### Phase 3: 架构数字孪生与 DevOps 闭环 (AIOps Loop)
*   **目标**: 让知识图谱成为感知、执行与反馈的终极中枢。
*   **核心任务**:
    - [ ] **3.1 部署感知脚手架**: 改造脚手架，实现代码、配置、Docker 及图谱节点的原子化生成。
    - [ ] **3.2 全链路遥测关联**: 将运行时 Trace 通过 `UnifiedLog` 实时挂载回图谱中的 Requirement/Spec 节点。
    - [ ] **3.3 自愈反馈回路**: 实现基于图谱的故障自动定位与 AI 自动修复建议提示。

### Phase 4: 文档交互化与自学习 (Intelligent Help System)
*   **目标**: 让文档“活起来”。
*   **核心任务**:
    - [ ] **4.1 Docs-as-Service**: 建立针对 L0-L4 文档的专业 RAG 助手。
    - [ ] **4.2 架构看板可视化**: 在前端展示实时演进的架构图谱与系统性能热图。

---

## 🎯 交付标准 (Definition of Done)
1.  **零散脚本清零**: `backend/scripts/` 下的独立脚本全部整合进 `hm` CLI 或 SDK。
2.  **文档代码对齐**: `REGISTRY.md` 覆盖率达到 100%（由脚本自动验证）。
3.  **零配置脚手架**: 运行新功能脚手架后，无需手动配置环境即可通过 CI 门禁。
4.  **图谱闭环**: 任意生产环境错误均可通过图谱追溯至初始 Idea。

---

## 🛡️ 风险提示
- **依赖锁死**: 深度整合可能导致各模块间耦合增加，需通过严格的接口契约（Protocols）进行解耦。
- **迁移成本**: 80+ 个脚本的重构需要保证在迁移过程中功能不中断。

---
> 🔗 **关联文档**:
> - [REGISTRY.md](../../REGISTRY.md)
> - [SYSTEM_OVERVIEW.md](../../docs/SYSTEM_OVERVIEW.md)
