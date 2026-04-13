# 📈 HiveMind 架构成熟度模型 (Architecture Maturity Model, AMM)

为了实现规约的“渐进式曝露”与“完全执行”，我们将治理过程分为三个阶段。

---

## 阶段 0: 原型与混沌期 (Prototype)
- **目标**: 快速验证业务。
- **治理力度**: 低。
- **核心规约**:
    - [x] 后端 `snake_case`，前端 `camelCase`。
    - [x] 关键 API 使用 `ApiResponse`。

## 阶段 1: 标准化与契约期 (Standardized) — [当前阶段]
- **目标**: 消除前后端歧义，实现认知对齐。
- **治理力度**: 中。
- **核心规约**:
    - [x] **SSoT 驱动**: 所有的 API 类型必须由 `sync-api` 生成。
    - [x] **统一响应包**: 全站 API 强制遵循 `UnifiedResponse` (success, data, message, error_code)。
    - [ ] **领域驱动分包**: 物理目录结构从层级（models/views）向领域（auth/knowledge）迁移。

## 阶段 2: 工业化与智体自愈期 (Industrialized)
- **目标**: 代码对 AI 极其友好，零重复，高内聚。
- **治理力度**: 高（CI 拦截）。
- **核心规约**:
    - [ ] **LLM 极致亲和**: 文件大小强制控制在 300 行以内。
    - [ ] **语义内聚**: 所有的 Docstring 必须包含 I/O 示例以便智体理解。
    - [ ] **契约测试**: 每一处 API 修改必须附带生成的契约变化审计。

---

## 📅 曝露策略 (Disclosure Strategy)
1. **开发者视角**: 当智体在修改一个文件时，如果该文件属于“频繁变动区”，则强制曝露“阶段 2”的规约；如果是“稳定陈旧区”，则仅曝露“阶段 0”规约。
2. **Review 视角**: 治理 Agent 会根据代码的层级（Core vs Feature）动态调整评审项的阈值。

---
*Created by Antigravity AI - System Evolutionary Team*
