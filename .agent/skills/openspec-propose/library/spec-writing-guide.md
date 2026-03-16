# 📖 OpenSpec 编写准则 (Spec Writing Guide)

## 1. 原则 (Core Principles)
- **MECE (Mutually Exclusive, Collectively Exhaustive)**: 所有的设计和任务必须互不重叠且完全覆盖目标。
- **Atomic Tasks**: 每个任务必须是可独立执行且可验证的原子单元。
- **Just-in-Time Context**: 仅包含实现当前 Change 所需的信息，避免冗余。

## 2. 变更提案 (proposal.md)
- **Problem Statement**: 必须清晰描述“痛点”，而不仅仅是“功能”。
- **Success Criteria**: 必须量化。例如：“响应延迟降低 50%”，而不是“提升速度”。

## 3. 技术设计 (design.md)
- **Data Contract**: 在涉及不同模块通讯时，必须写明 Schema（推荐使用 TS Interface 风格）。
- **State Changes**: 必须描述变更导致的状态机迁移。

## 4. 任务清单 (tasks.md)
- **Dependency Flow**: 任务顺序必须符合拓扑逻辑（先底层、后服务、再接口、最后 UI）。
- **Verification Command**: 每个任务必须自带一条检查指令（如 `pytest ...` 或 `ls ...`）。
