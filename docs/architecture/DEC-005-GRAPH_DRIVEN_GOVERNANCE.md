# 📐 DEC-005: 图谱驱动的规约治理 (Graph-Driven Governance)

> **修订版本**: V1.0 (2024-04-12)  
> **设计目标**: 将静态的 `docs/conventions` 转化为动态的 Neo4j 知识资产，实现规约的数字化、可视化于自愈闭环。

---

## 1. 知识图谱扩展 (Graph Schema)

我们将规约映射为 Neo4j 中的核心节点：

### 1.1 节点定义 (Nodes)
*   **`GovernanceRule`**: 具体的编程规则（如：RULE-B001）。
    *   属性: `id`, `title`, `level` (Stage 1/2/3), `directive` (AI 提示词).
*   **`Violation`**: 治理事故节点。
    *   属性: `detected_at`, `severity`, `status` (open/fixed).

### 1.2 关系定义 (Relationships)
*   **`(GovernanceRule)-[:APPLIES_TO]->(Design/SoftwareAsset)`**: 定义规则的适用范围。
*   **`(File/Component)-[:VIOLATES]->(GovernanceRule)`**: 实时的治理债务映射。
*   **`(GovernanceRule)-[:EVOLVED_FROM]->(Incident)`**: 记录规约的进化来源（从事故中总结).

---

## 2. 治理闭环 (The Cycle)

为了实现“慢慢补全”，我们遵循以下飞轮效应：

1.  **观察 (Discover)**: 通过 `TraceMiddleware` 或 `ContractGuard` 发现重复出现的异常。
2.  **建模 (Model)**: 将重复问题抽象为 `GovernanceRule` 节点，并关联至相关业务组件。
3.  **同步 (Sync)**: 运行 `verify_governance.py` 生成 `VIOLATES` 关系。
4.  **可视化 (Visualize)**: 在治理看板中展示“规约热力图”，识别系统性治理风险。

---

## 3. 渐进式同步逻辑

*   **全量扫描**: 每日同步一次全局规约执行情况。
*   **热点扫描**: 针对 `REGISTRY.md` 中标记为 `🚧` (开发中) 的组件，进行高频规约审计。

---
*Created by Antigravity AI - Graph Engineering Team*
