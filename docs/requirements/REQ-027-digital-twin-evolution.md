# REQ-027: Project Digital Twin Evolution (图谱孪生进化)

| 字段 | 值 |
|------|------|
| **编号** | REQ-027 |
| **标题** | Project Digital Twin Evolution (图谱孪生进化) |
| **来源** | 用户对话 (2026-04-07) |
| **优先级** | 高 |
| **状态** | ⬜ 待讨论 |
| **关联设计** | 待定 |
| **关联代码** | `backend/app/core/graph_store.py`, `skills/architectural-mapping/` |

## 需求描述
当前 HiveMind 系统基于 Neo4j 构建了强大的静态“架构资产及研发知识图谱”（涵盖 AST、文档溯源、团队贡献等）。为实现从“代码辅助”到“全局架构生命周期自治”的跃升，需将该静态骨架升级为具备运行时神经和安全免疫系统机制的数据结构，引入**数字孪生 (Digital Twin)** 理念。

## 详细要求
1. **静态安全与供应链 (Phase 1)**
   - 解析项目依赖 (e.g., `pyproject.toml`, `package.json`)。
   - 在图中建立组件、包版本库的溯源关系：`(:File)-[:IMPORTS]->(:Package)`。
   - 实现自动为包含用户私密数据流转及操作的数据模型进行属性级或节点级标记 (e.g., `is_PII=True`) 防范泄露。

2. **动态观测与覆盖率联通 (Phase 2)**
   - 打通自动化测试覆盖率报告 (e.g., pytest-cov XML)，赋予 AST 中 `Function` 等级节点覆盖率标签 (`coverage`)。
   - 提供能力使高频 / 高延时 / 高错误相关的 APM 指标可以旁路注入回 Neo4j 相对应的 `APIEndpoint` 节点，为 Agent 高潜重构提醒提供依据。

3. **问题追踪与缺陷流转闭环 (Phase 3)**
   - 与 Issue 系统双向验证，在图谱内记录并推导破窗缺陷：`(:Bug)-[:AFFECTS]->(:File/Function)`。
   - 增加代码热点感知及脆弱度评估能力。

## 验收标准
- [ ] 能在图谱可视化及 Cypher 查询中检索出系统内的包依赖树 (:Package)。
- [ ] Pydantic 模型可通过 AST 被识别出合规字段并打上 PII 标识。
- [ ] Neo4j 中 `Test` 或 `Function` 承载了代码覆盖率 (Coverage) 实体属性。

## 变更记录
| 日期 | 变更 | 人员 |
|------|------|------|
| 2026-04-07 | 初始创建提取规划 | Antigravity AI |
