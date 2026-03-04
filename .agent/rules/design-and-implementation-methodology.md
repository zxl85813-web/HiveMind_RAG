---
description: 研发方法论 — 从需求解析、系统设计到编码与测试的端到端细化规范
---

# 🧠 研发方法论 (Design & Implementation Methodology)

在基于 Markdown 文档驱动的开发模式（为未来 RAG 驱动打下基础）中，所有的意图、设计、结构和问题都必须显式地记录在案。本规范定义了"如何做设计"、"如何写代码"以及"如何测试"。

## 1. 需求细化阶段 (Requirement Refinement)

一个模糊的需求（如"加上多租户"）不能直接开始设计，必须先将其细化。

### 细化核对表
- [ ] **痛点/目标**: 用户用这个功能到底解决什么问题？
- [ ] **业务流转图**: (使用 Mermaid `graph TD` 绘制主要业务的流转)
- [ ] **边界条件**: 万一网络断了？万一没有权限？最大并发是多少？
- [ ] **数据驻留**: 会产生什么数据？需要存多久？

**输出:** `docs/requirements/REQ-NNN.md` (包含上述四个元素)

---

## 2. 深度架构/设计说明书编制 (Design Documentation)

针对已细化的要求，架构师/Dev 需要输出 `docs/design/DES-NNN.md`，该文档必须包含以下四大领域的严谨设计：

### 2.1 数据库设计 (Database Design)
- **表结构变更**: 所有的表、字段、类型，必须写明是否可 `nullable`。
- **关联关系**: 必须用 Mermaid `erDiagram` 画出 ER 图。
- **索引策略**: 基于哪些字段频繁查询（Where 条件）去建立索引？（例如: `CREATE INDEX ix_user_id ON documents(user_id)`）。
- **数据一致性原则**: 级联删除 (`ondelete="CASCADE"`) 还是软删除 (`is_deleted = True`)。

### 2.2 后端逻辑设计 (Backend Design)
- **职责划分**: 明确指出哪些代码写在 `api/`，哪些在 `services/`，哪些在 `core/`。
- **依赖引用关系**: 绝对禁止循环依赖。标明服务之间谁调用谁。
- **异常清单**: 列出该模块可能引发的自定义异常（如 `DocumentTooLargeError`）。

### 2.3 API 契约协议设计 (API Design)
- 写明 RESTful 路由规范（基于名词，动词放 HTTP Method）。
- **必须包裹响应**: 永远回答 `{ "success": true, "code": 200, "data": {...}, "message": "OK" }`。
- Request / Response Schema，说明字段验证规则（如 `maxLength`, `Regex`）。

### 2.4 前端组件设计 (Frontend Design)
- **组件拆解 (Component Tree)**: 先画出组件树，区分哪些是 Smart Component (接管数据)，哪些是 Dumb Component (只负责渲染)。
- **复用参照点**: **强制** 在设计文档中通过 `grep` 或查看 `REGISTRY.md` / `src/components/common`，标明“我们将复用组件 `XXX`”。
- **状态流转**: 如果状态复杂，写明是要放 `Zustand store` 还是 `useState`。

---

## 3. 开发落地与组件协同准则 (Implementation Execution)

设计文档批复后，进入编码过程：

### 3.1 参照现有体系
1. **寻找轮子**: 在写任何通用 UI 或通用工具函数前，必须 `grep` 现有的 `components/common/` 目录和 `backend/utils/`。
2. **样式继承**: 强制使用 `App.tsx` 中定义的 Ant Design ConfigProvider Token 或 `variables.css`，禁止写死 `#xxx` 或 `14px`。

### 3.2 动态追踪与阻塞标注 (Todo & Blockers Tracking)
项目中 `TODO.md` 是实时工作台。对于需要追踪状态的开发：
- **未完成标注**: 格式必须为 `- [ ] TASK_NAME (Due/Assignee)`
- **阻塞/中断标注**: 发现原 API 设计不合理导致必须停下，立刻去 `TODO.md` 顶端记录:
  `- [ ] 🛑 BLOCKED: TASK_NAME - Reason: <具体问题详情>`
- **设计缺漏标注**: 发现某一项边界流程在 REQ 或 DES 文档里漏了:
  `- [ ] ⚠️ DESIGN_GAP: 边界条件 <XXX> 未说明`
- **组件/工具提取申请**: (参考对应的组件/工具规范)
  `- [ ] 🔧 COMPONENT_NEEDED: [组件名] - [组件干嘛用]`
  `- [ ] 🔧 UTIL_NEEDED: [函数名] - [函数用途]`

## 4. “多视角”评审机制 (Multi-Perspective Review)

从设计产出到代码生成，都必须经过**严格的人机联合评审 (Review)**。评审不能凭感觉，必须拿着"观点" (Viewpoint) 作为尺子去衡量：

### 4.1 架构/设计评审观点 (Design Review Viewpoint)
在 `DES-NNN` 生成后执行：
- **业务对齐度**: 是否100%覆盖了 `REQ-NNN` 中的痛点和验收流？
- **一致性**: API 命名是否复用了旧名词？前端组件树是否最大化利用了 `components/common/` 现存组件？
- **扩展性缺口**: 数据库 ER 图设计有没有为未来 3 个月可能出现的需求留有余地（如是否加了 metadata JSON 字段扩展）？

- **安全性与数据隔离**: 
  - **软删除检查**: 检查所有的 `select` 查询是否补全了 `.where(Model.is_deleted == False)` 过滤条件？
  - **权限检查**: 关键数据查询是否带有 `user_id` 或 `owner_id` 过滤？
- **规范遵守度**: 严格比对 `backend-design-standards.md` 或 `frontend-component-standards.md`（有没有写死色值？有没有在 controller 堆砌逻辑？）
- **安全与性能**: 警惕 N+1 数据库查询；警惕没有分页的 List 接口；警惕没有做 XSS 过滤或脱敏（参考 REQ-010）的输出。

---

## 5. “双视角”测试方法论 (Dual-View Testing)

为了产出高可靠的代码，测试用例应当在两个不同维度被设计出来：

### 4.1 设计观点的测试 (Black-box / Contract Testing)
站在系统的外部，验证设计文档中的承诺是否兑现。
- **依据来源**: 根据 API Schema、需求文档的验收标准来设计。
- **关注点**: 
  - 输入正确的 payload，能否以标准的 `ApiResponse` 拿到正确的 200 ？
  - 触发了边界规则（如超出 500行），能否拿到符合预期的 400 Bad Request？
- **手段**: Python `FastAPI TestClient`（模拟 HTTP 请求） / 前端 Playwright E2E。

### 4.2 代码观点的测试 (White-box / Logic Testing)
深入代码内部，覆盖异常分支与核心算法。
- **依据来源**: 根据代码中的 `if/else`, `try/except` 块。
- **关注点**:
  - 数据库连接断开时，抛出什么异常？
  - LLM 超时（Timeout），Fallback 策略是否生效？
  - 共享对象是否产生数据竞态竞争？
- **手段**: Pytest 针对 `services/` 和 `agents/` 进行直接调用，结合重度 Mocking (如 `AsyncMock` 或内存型 sqlite)。

## 6. 标准的可扩展与特例豁免原则 (Extensibility & Exemptions)

所有的规范指南（无论是 DB 设计、API 命名还是前端逻辑拆解）其核心都是为了提升系统的健壮性和开发协同效率，**而非不可违抗的教条**。本系统支持在面对具体业务情况时灵活调整：

### 6.1 "特例"的边界判定 (Case-by-case evaluation)
当严格遵守某个规则（如：前端要求所有复杂组件绝对 Dumb）会导致极度的性能衰退（如巨大的重渲染树）或是增加了巨大的不必要的抽象成本时，此时应启动**具体情况具体分析**。

### 6.2 豁免与适配机制 (How to Override)
如果开发者或 Agent 决定修改或不采用某项具体标准：
1. **不要偷偷破坏**: 必须在代码注释或合并拉取请求 (PR) 时 explicitly 声明。
2. **出具设计决策记录 (ADR)**: 若是影响较广的规则违抗（比如：为了海量日志，放弃 PostgreSQL 而采用 MongoDB，从而违背了 `database-design-standards` 里的 SQLModel 映射规范），必须在 `docs/architecture/decisions/` 中通过 `ADR-NNN` 来陈述为何当前的权宜之计是最优解。
3. **沉淀为新规范**: 如果这种扩展（如新的性能方案）在项目中多次出现并且被证明行之有效，**必须反过来提炼出新的规则内容**，补充更新回 `.agent/rules/` 内的相关文件。永远不要让成文标准和实际运行系统的潜规则脱节。

---

## 7. RAG 愿景铺垫
以上所有 Markdown 文档 (REQ, DES, ADR, TODO) 目前由开发者与大模型通过文件读写协同维护。
未来，随着 `HiveMind RAG` 系统本身的成熟，项目自身的 `docs/` 将被本地化向量入库。当我们询问内部的 `code_agent` 时，它可以立刻基于已有的设计模式生成准确的新功能实现代码。因此，**Markdown 的格式严谨性至关重要**。
