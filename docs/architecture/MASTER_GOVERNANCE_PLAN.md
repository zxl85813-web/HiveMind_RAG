# 🌪️ HiveMind 全量治理与进化大纲 (Master Governance & Evolution Plan)

> **修订版本**: V2.0 (2026-04-12)  
> **设计哲学**: 治理是一场“无尽的对抗”。通过“实时捕获、自动建档、图谱学习、刚性拦截”实现系统的自愈。

---

## 1. 存量坏账清债计划 (Debt Refactoring) — [正在启动]

针对 `verify_governance.py` 扫描出的 44 处违规点，启动 **“清道夫集群 (Scavenger Swarm)”**:
- **Priority 1**: API 统一化。修复所有未返回 `ApiResponse` 的路由。
- **Priority 2**: 文件瘦身。将超过 300 行的 `agentApi.ts` 和 `main.py` 进行解耦拆分。
- **Priority 3**: 契约对齐。移除前端所有手写的重复 Interface。

## 2. 规约进化闭环 (The Feedback Loop) — [核心逻辑]

当系统遇到一个非预期问题时，执行以下“进化四步法”：

### 第一步：实时捕获 (Intercept)
- **FE**: `ContractGuard` 拦截请求。
- **BE**: `TraceMiddleware` 监控状态漂移。
- **结果**: 触发治理事故上报。

### 第二步：事故存根与自省 (Automatic RCA)
- 系统自动在 `docs/governance/incidents/` 生成 `INC-xxx.md`。
- 治理 Agent 自动进行根因分析（RCA），判定是“代码 Bug”还是“规约缺失”。

### 第三步：知识沉淀 (Rule Crystallization)
- 如果是规约缺失，Agent 会提炼出新的 `GovernanceRule`。
- **动作**: 调用 `scripts/sync_governance_to_graph.py` 将新规则“刻”入 Neo4j。

### 第四步：全量验证 (Immune Resistance)
- 更新 `verify_governance.py` 逻辑。
- 此后，任何类似的违规提交将在 Git Hook 阶段被物理拦截。

## 3. 刚性门禁路线图 (The Hard Gates)

| 阶段 | 治理深度 | 技术手段 |
| :--- | :--- | :--- |
| **Q2-01** | 全量清债 | 运行 `Scavenger Swarm` 消除 44 处存量坏账 |
| **Q2-02** | 物理拦截 | 启用 `Husky (Pre-commit)` 强制跑 `verify_governance.py` |
| **Q2-03** | 契约对齐 | 引入 `Schemathesis` 自动发现后端与 OpenAPI 的一致性漏洞 |
| **Q2-04** | 看板可视 | 前端上线 `Governance Dashboard`，实时监控图谱中的治理热度 |

---
*Approved by Antigravity AI - Chief Architect*
