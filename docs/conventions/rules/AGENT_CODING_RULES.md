# 🤖 HiveMind 智体编程指令集 (Agentic Coding Directives)

> **修订版本**: V1.0 (2026-04-12)  
> **设计目标**: 既然大部分代码是由 AI (Antigravity/Subagents) 生成，代码必须具有极高的“语义显性”与“结构预测性”。

---

## 🏗️ 规则组 A: 语义显性 (Semantic Explicitness)

### [RULE-A001] 命名抗歧义 (Unambiguous Naming)
- **要求**: 变量名禁止缩写（除非是业界通用的 `id`, `db`, `kb`）。
- **BAD**: `ctx`, `res`, `idx`
- **GOOD**: `generation_context`, `api_response_body`, `document_list_index`
- **为何**: AI 在长上下文中会遗忘局部缩写的含义。

### [RULE-A002] 类型强声明 (Strong Type Hinting)
- **要求**: 所有的 Python 函数必须包含完整类型加注。
- **示例**: `def process_node(node: DAGNode, context: dict[str, Any]) -> TaskResult:`
- **为何**: 让 Subagent 在调用他人代码时能通过类型推断直接理解边界，不再需要 `view_file` 查看实现。

---

## 📦 规则组 B: 结构预测性 (Structural Predictability)

### [RULE-B001] "300原则" (Small Context Files)
- **要求**: 单个源代码文件行数**严禁超过 300 行**。
- **治理**: 超过 300 行时，必须按业务领域拆分为子模块（如 `chat.py` -> `chat/routes.py`, `chat/logic.py`）。
- **为何**: 保持文件在 LLM 的黄金注意力窗口内（24K tokens 以下），避免“中间丢失”效应。

### [RULE-B002] 单一事实出口 (Single Exit Point)
- **要求**: 业务逻辑层禁止直接返回 `None`。必须返回包含明确 `success` 标记的数据结构。
- **为何**: 智体对 `None` 的处理极易发生逻辑分支穿透导致崩溃。

---

## 🛰️ 规则组 C: 治理绑定 (Governance Binding)

### [RULE-C001] 变更自愈 (Self-Healing Registration)
- **要求**: 任何涉及 API 入参/出参的修改，必须同步运行 `scripts/export_openapi.py`。
- **AI 指令**: 如果你修改了 Model，你**必须**在同一个 Turn 内调起同步脚本。

### [RULE-C002] 测试先导 (Test-First Guard)
- **要求**: 任何 Service 层的逻辑修改，对应的单元测试文件必须放在 `tests/` 目录下且通过 100% 覆盖验收。

### [RULE-C003] 鉴权引用闭环 (Auth Dependency Integrity)
- **要求**: 所有的鉴权依赖（如 `get_current_user`）必须通过 FastAPI 的 `Depends` 注入。**严禁**手动调用鉴权函数并传入 `None`。
- **为何**: 手动透传 `None` 会绕过 Security Scheme 的自动提取逻辑，导致即便请求带有 Token 也会返回 401。
- **事故来源**: [INC-20260412-001](../../governance/incidents/INC-20260412-001.md)

### [RULE-B003] 零僵尸引用 (No Zombie References)
- **要求**: 严禁在 API 路由层调用尚未在 Service 层正式实现的方法。智体在新增调用前，必须通过工具验证目标方法的物理存在性。
- **为何**: Service 层的缺失会导致系统抛出 `AttributeError` 并触发 500 崩溃，严重影响前端组件渲染。
- **事故来源**: [INC-20260412-002](../../governance/incidents/INC-20260412-002.md)

### [RULE-C004] 契约先行自检 (Pre-Contract Audit)
- **要求**: 修改或新增跨模块调用时，必须同时更新/校验被调用方的参数签名（Signature）。

### [RULE-B004] 默认安全但不破坏功能
- **要求**: 权限降级逻辑（如无法匹配角色时的兜底）必须有对应的日志输出。严禁静默将活跃用户降级为零权限角色。
- **事故来源**: [INC-20260412-003](../../governance/incidents/INC-20260412-003.md)

### [RULE-CS-001] 契约命名对齐 (Contract Naming Parity)
- **要求**: 涉及角色 (Role)、权限 (Permission)、状态 (Status) 的枚举定义，前端必须与后端模型保持 1:1 命名对齐。

---
*Created by Antigravity AI - Protocol Engineering Team*
