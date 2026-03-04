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
- **阻塞/有问题标注**: 格式必须为 `- [ ] 🛑 BLOCKED: TASK_NAME - Reason: <具体问题详情>`。
> 开发中如果发现原 API 设计不合理导致必须停下，应立刻去 `TODO.md` 记录 `🛑 BLOCKED: API Schema 不匹配`，并提醒要求修补设计。

---

## 4. “双视角”测试方法论 (Dual-View Testing)

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

---

## 5. RAG 愿景铺垫
以上所有 Markdown 文档 (REQ, DES, ADR, TODO) 目前由开发者与大模型通过文件读写协同维护。
未来，随着 `HiveMind RAG` 系统本身的成熟，项目自身的 `docs/` 将被本地化向量入库。当我们询问内部的 `code_agent` 时，它可以立刻基于已有的设计模式生成准确的新功能实现代码。因此，**Markdown 的格式严谨性至关重要**。
