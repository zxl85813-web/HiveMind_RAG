# 🔐 权限-角色-记忆治理（Authorization + Role + Memory）

> 目标：在不牺牲安全边界的前提下，让系统通过“角色与个人分层记忆”变得更聪明。

---

## 一、核心原则（必须同时成立）

1. 权限是硬边界，记忆是软增强。
2. 记忆只能影响“表达/排序/推荐”，不能改变“允许/拒绝”。
3. 所有敏感操作必须可审计、可回放、可解释。
4. 授权结果先于提示词增强生效，且全链路复核。

简式规则：

```
Authorization decides what can be done.
Memory decides how to do it better.
```

---

## 二、三层角色体系与边界

### 2.1 业务权限角色（RBAC）

- 目的：控制用户是否可执行某类动作。
- 典型动作：`kb:create`、`kb:view`、`kb:upload`、`agent:config`。
- 代码锚点：`backend/app/auth/permissions.py`

边界：只回答“是否具备动作权限”，不决定具体资源可见性。

### 2.2 资源访问角色（ACL/Owner/Dept）

- 目的：控制用户对具体知识库/文档的访问范围。
- 授权主体：`user_id`、`role_id`、`department_id`。
- 授权粒度：
- KB：`can_read/can_write/can_manage`
- Document：`can_read/can_write`
- 代码锚点：
- `backend/app/models/security.py`
- `backend/app/services/knowledge/kb_service.py`

边界：只回答“对这个资源是否可访问”，不负责回答风格或个性化。

### 2.3 认知角色（Role Memory + Personal Memory）

- 目的：在已授权范围内优化回答质量与交互体验。
- 作用：术语偏好、风险提示风格、输出结构、检索排序权重。
- 不可作用：越权访问、绕过 ACL、放宽审计要求。

边界：只影响“如何回答”，不影响“能否访问”。

---

## 三、判定链路（建议作为统一实现约束）

```
请求进入
  -> Gate 1: Authentication
  -> Gate 2: RBAC（动作级）
  -> Gate 3: KB ACL（资源级）
  -> Gate 4: Document ACL（内容级）
  -> Prompt Assembly（Role/Personal Memory）
  -> 输出
```

执行要求：

- 任一 Gate 拒绝即终止，并写审计日志。
- Prompt Assembly 只能读取“已授权作用域”内的数据。
- 检索流程必须做文档级二次过滤（数据平面兜底）。

---

## 四、当前代码中的映射（现状）

### 4.1 RBAC（动作权限）

- 文件：`backend/app/auth/permissions.py`
- 要点：`Role`、`Permission`、`ROLE_PERMISSIONS`、`require_permission(...)`

### 4.2 KB 访问控制（资源权限）

- 文件：`backend/app/services/knowledge/kb_service.py`
- 要点：`check_kb_access(kb_id, user, level)`
- 判定维度：`admin`、`owner_id`、`is_public`、`kb_permissions`

### 4.3 路由层拦截（接口权限）

- 文件：`backend/app/api/routes/knowledge.py`
- 要点：读写管权限在路由入口调用 `check_kb_access(...)`

### 4.4 文档级过滤（检索权限）

- 文件：`backend/app/services/retrieval/steps.py`
- 要点：`AclFilterStep` 对候选文档做 `DocumentPermission` 校验

---

## 五、记忆分层规范（建议落地标准）

### 5.1 Role Memory（群体层）

存储建议：

- 域内术语词典（如法务、采购、技术）
- 风险偏好与合规提示模板
- 默认输出模板（摘要/条款对照/行动清单）

生效范围：

- 仅在授权后对答案策略生效
- 可参与检索重排（同域知识优先）

### 5.2 Personal Memory（个人层）

存储建议：

- 用户偏好（语言、格式、篇幅）
- 历史项目上下文（非敏感）
- 常用知识库偏好（仅候选排序）

生效范围：

- 不得扩展授权作用域
- 不得注入未授权资源标识

### 5.3 Forbidden Influence（禁止项）

以下字段不得用于授权判断：

- role prompt 文本内容
- personal memory 命中结果
- LLM 推断出的“可能身份/关系”

授权判断仅可读取：

- 认证身份（user_id）
- 组织属性（role/department）
- ACL/RBAC 持久化策略

---

## 六、审计与可观测要求

每次请求至少记录：

- `request_id`
- `user_id`
- `action`
- `resource_type/resource_id`
- `decision`（allow/deny）
- `deny_reason`（rbac_denied/kb_acl_denied/doc_acl_denied）
- `memory_applied`（none/role/personal/both）

目标：确保“为什么能看/为什么不能看”可被审计解释。

---

## 七、实施计划（文档版）

### Phase A：权限基线固化

- 明确默认策略（推荐 default deny）
- 统一所有入口的 Gate 顺序
- 补齐 deny_reason 审计字段

### Phase B：记忆分层上线

- 新增 Role Memory schema 与 Personal Memory schema
- 在 Prompt Engine 中分层注入
- 增加“授权作用域裁剪”中间件

### Phase C：评估与回归

- 权限回归：越权访问必须失败
- 智能回归：答案质量提升但权限不变化
- 审计回归：拒绝路径日志完整

---

## 八、验收标准

1. 任意记忆命中均不能改变授权结果。
2. 任意未授权 KB/Document 不能出现在最终上下文。
3. 所有权限拒绝都有原因码与审计记录。
4. Role/Personal 记忆可解释且可关闭。

---

## 九、相关文档

- `docs/AGENT_GOVERNANCE.md`
- `docs/DATA_GOVERNANCE.md`
- `backend/app/auth/permissions.py`
- `backend/app/services/knowledge/kb_service.py`
- `backend/app/services/retrieval/steps.py`

---

## 十、当前细化（As-Is Baseline）

### 10.1 当前权限模型定性

- 当前是 `RBAC + ACL/ABAC` 混合模型，带有 `ReBAC` 倾向但尚未形成关系策略引擎。
- RBAC 负责动作权限，ACL/ABAC 负责资源与内容权限，检索层做数据面二次过滤。

### 10.2 当前已具备能力（可直接复用）

- 动作权限：`Role -> Permission`（`permissions.py`）。
- KB 资源权限：`owner_id`、`is_public`、`kb_permissions`（`kb_service.py`）。
- 文档权限：`document_permissions` + 检索阶段 `AclFilterStep`（`steps.py`）。
- 接口拦截：知识库相关路由在入口进行 `check_kb_access(...)`。

### 10.3 当前主要缺口（需优先收敛）

- 缺口 A：默认策略未完全统一为 `default deny`（部分路径仍有 MVP 放行语义）。
- 缺口 B：多 KB 聚合入口缺少统一的 `authorized_kb_ids` 前置裁剪约束。
- 缺口 C：审计字段尚未标准化到统一原因码（`deny_reason`）与记忆应用标记。
- 缺口 D：Role Memory / Personal Memory 尚未形成可执行 Schema 与注入契约。

---

## 十一、未来 TODO（分阶段执行）

> 原则：先固化权限硬边界，再引入记忆增强；任何阶段都不得让记忆参与授权判定。

### P0（本周）权限基线固化

- [x] P0-1 统一授权顺序：`Auth -> RBAC -> KB ACL -> Document ACL -> Prompt`。
- [x] P0-2 统一默认策略：明确并落地 `default deny`（含例外清单）。
- [x] P0-3 标准化拒绝原因：`rbac_denied` / `kb_acl_denied` / `doc_acl_denied`。
- [x] P0-4 建立“授权结果只读上下文”对象，供后续 Prompt 层消费。

验收：任意越权请求在任一 Gate 被拦截，且审计可解释。

### P1（下阶段）记忆分层落地

- [ ] P1-1 定义 Role Memory Schema（术语、模板、风险偏好）。
- [ ] P1-2 定义 Personal Memory Schema（偏好、历史上下文、常用资源）。
- [ ] P1-3 Prompt Engine 分层注入（Role 层 + Personal 层）。
- [ ] P1-4 增加作用域裁剪器：记忆只能读取已授权资源。

验收：记忆命中前后，授权结果保持一致；仅回答质量与排序变化。

### P2（后续）向 ReBAC 演进（可选增强）

- [ ] P2-1 定义关系边类型（owner/member/steward/reviewer 等）。
- [ ] P2-2 引入关系策略样式（单跳规则优先，不做黑盒多跳）。
- [ ] P2-3 审计扩展：记录命中的关系规则与路径摘要。

验收：关系授权可解释、可回放，且不替代 RBAC/ACL 硬边界。

### P3（持续）质量与治理

- [ ] P3-1 建立权限回归测试集（允许/拒绝用例对照）。
- [ ] P3-2 建立记忆安全回归（验证“记忆不越权”）。
- [ ] P3-3 建立月度审计复盘机制（拒绝原因分布、误拦截率、漏拦截率）。

验收：每次发布前通过权限与记忆双回归。

---

## 十二、文件级实施清单（File-Level Checklist）

> 用法：按 `ARM-P0 -> ARM-P1 -> ARM-P2` 顺序执行。每项完成后同步更新 `TODO.md` 对应条目。

### 12.1 ARM-P0（权限基线固化）

#### ARM-P0-1 统一授权顺序

- [x] `backend/app/api/routes/knowledge.py`
  - 统一路由入口检查顺序：先动作级（RBAC），再资源级（KB ACL），最后数据级（Document ACL）。
  - 避免在不同 endpoint 出现先查资源再判动作的顺序漂移。
- [ ] `backend/app/api/routes/chat.py`
  - 移除 `CURRENT_USER_ID` 固定用户，接入真实 `get_current_user` 依赖，避免鉴权绕过。
- [x] `backend/app/services/chat_service.py`
  - 在触发检索/上下文拼装前接入授权作用域对象，确保仅查询可访问 KB/文档。

验证：

- [x] `backend/tests/unit/services/knowledge/test_kb_service.py` 新增/补齐顺序相关用例。
- [x] `backend/tests/unit/services/test_chat_service.py` 解除/替换跳过用例中的鉴权假设。

#### ARM-P0-2 统一默认策略为 default deny

- [x] `backend/app/services/retrieval/steps.py`
  - 收敛 `AclFilterStep` 的“无权限记录即放行”语义，改为默认拒绝或显式白名单。
- [x] `backend/app/services/knowledge/kb_service.py`
  - `check_kb_access` 对不存在授权关系时保持严格拒绝，避免隐式放行路径。
- [ ] `backend/app/models/security.py`
  - 补充注释/约束说明默认策略，减少模型层与服务层语义偏差。

验证：

- [x] `backend/tests/unit/services/retrieval/test_retrieval_steps.py` 增加 default-deny 场景。
- [x] `backend/tests/integration/test_security_api.py` 增加未授权访问返回 403 场景。

#### ARM-P0-3 标准化拒绝原因码

- [x] `backend/app/core/exceptions.py`
  - 为权限异常补充可机读 reason code 字段（如 `rbac_denied`）。
- [x] `backend/app/api/routes/knowledge.py`
  - 在访问判定处输出标准化拒绝原因。
- [x] `backend/app/services/retrieval/steps.py`
  - 在 ACL 过滤中记录 `doc_acl_denied` 统计与原因。
- [ ] `backend/app/services/audit_service.py`
  - 统一写入 `deny_reason`、`resource_type`、`resource_id`、`user_id`。

验证：

- [x] `backend/tests/integration/test_security_api.py` 断言响应/日志包含原因码。

#### ARM-P0-4 授权作用域只读上下文

- [x] `backend/app/auth/permissions.py`
  - 新增或导出统一授权结果结构（如 `AuthorizationContext`）类型定义。
- [x] `backend/app/services/knowledge/kb_service.py`
  - 提供 `authorized_kb_ids` 获取方法（已存在可标准化返回结构）。
- [x] `backend/app/services/retrieval/pipeline.py`
  - `RetrievalContext` 注入授权作用域字段。
- [x] `backend/app/services/retrieval/protocol.py`
  - 明确定义授权作用域字段（只读）和传递契约。

验证：

- [ ] `backend/tests/unit/services/retrieval/test_retrieval_pipeline_variants.py` 断言不同变体下授权作用域不丢失。

### 12.2 ARM-P1（记忆分层落地）

#### ARM-P1-1 Role Memory Schema

- [x] `backend/app/services/memory/memory_service.py`
  - 增加 Role Memory 结构定义（术语字典、模板、风险偏好）。
- [ ] `backend/app/api/routes/memory.py`
  - 增加角色记忆查询/更新接口（带权限控制）。

验证：

- [ ] `backend/tests/unit/services/memory/test_tier1_abstract.py` 增加角色记忆存取与序列化测试。

#### ARM-P1-2 Personal Memory Schema

- [x] `backend/app/services/memory/memory_service.py`
  - 增加 Personal Memory 结构定义（语言偏好、输出风格、常用 KB）。
- [ ] `backend/app/api/routes/memory.py`
  - 用户级记忆接口增加鉴权与作用域校验。

验证：

- [ ] `backend/tests/unit/services/memory/test_tier1_abstract.py` 增加个人记忆读写与隔离测试。

#### ARM-P1-3 Prompt 分层注入

- [x] `backend/app/prompts/engine.py` — 通过 Swarm 编排器实现注入
  - 明确注入顺序：`AuthorizationContext -> RoleMemory -> PersonalMemory -> TaskContext`。
  - 增加注入开关，支持灰度与回滚。
- [ ] `backend/app/prompts/loader.py`
  - 新增/加载角色与个人记忆模板段（可选）。
- [x] `backend/app/services/chat_service.py`
  - 构建 prompt 时按分层注入，禁止将记忆用于授权判断。

验证：

- [ ] `backend/tests/unit/services/test_prompt_engine_variants.py` 增加分层注入顺序与开关测试。

#### ARM-P1-4 作用域裁剪器

- [x] `backend/app/services/retrieval/steps.py`
  - 记忆参与检索重排前先按授权作用域裁剪候选集合。
- [x] `backend/app/services/chat_service.py`
  - 在上下文拼装前执行“未授权资源剔除”。

验证：

- [ ] `backend/tests/unit/services/retrieval/test_retrieval_steps.py` 增加“记忆命中但未授权资源不返回”用例。

### 12.3 ARM-P2（ReBAC 试点，可选）

- [ ] `backend/app/models/security.py`
  - 扩展关系边模型（owner/member/steward/reviewer）或关系字段。
- [ ] `backend/app/services/security_service.py`
  - 实现单跳关系策略解析（避免黑盒多跳）。
- [ ] `backend/app/api/routes/security.py`
  - 增加关系授权策略管理接口。

验证：

- [ ] `backend/tests/integration/test_security_api.py` 增加关系授权允许/拒绝对照测试。

### 12.4 交付与回归命令（建议）

- [x] `cd backend && pytest tests/unit/services/knowledge/test_kb_service.py -q`
- [x] `cd backend && pytest tests/unit/services/retrieval/test_retrieval_steps.py -q`
- [x] `cd backend && pytest tests/integration/test_security_api.py -q`
- [ ] `cd backend && pytest tests/unit/services/test_prompt_engine_variants.py -q`

完成定义：

- [x] 所有新增权限拒绝路径均带 `deny_reason`。
- [x] 记忆启用/禁用前后，授权结果一致。
- [x] 未授权资源在 API 响应与最终 Prompt 上下文中均不可见。
