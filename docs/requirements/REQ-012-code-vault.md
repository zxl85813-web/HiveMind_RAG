# REQ-012: Code Vault (代码资产知识库)

| 字段 | 值 |
|------|------|
| **编号** | REQ-012 |
| **标题** | Code Vault (代码资产知识库) |
| **来源** | 用户对话 (2026-03-06) |
| **优先级** | 高 |
| **状态** | ⬜ 待讨论 / 🟡 设计中 / 🟢 方案已定 / ✅ 已实现 |
| **关联设计** |  |
| **关联代码** |  |
| **GitHub Issue** | [#5](https://github.com/zxl85813-web/HiveMind_RAG/issues/5) |

## 需求描述
构建一个"代码资产知识库"和"治理模块"，将研发过程中的代码实现、功能设计、API 设计统筹存入向量数据库(pgvector)和图数据库(Neo4j)中，并关联开发者信息。
核心目标是为 AI 编程提供经过人类验证的高质量 RAG 上下文，同时通过积分回授建立开发者质量飞轮。

## 详细要求
1. **基础设施与图模型**: 扩展 DB 与 Neo4j 模型以支持多种 Reviewer 角色 (Code/Biz/Arch) 和资产状态机 (Development, Starter, Reviewing, Tested_OK, Online, Deprecated)。
2. **精细化资产类别**: 摄取时必须区分并标记 🗄️ SQL Recipes、🔧 Common Utility 以及 🧩 Business Logic，防止重复造轮子。
3. **定制化 Ingestion**: 开发处理结构化数据 (AST 语法树、Swagger/OpenAPI 设计) 的解析 Skill 和关系挂载引擎。
4. **多重评审流转系统**: 资产需要经过人类不同角色的审批才能上线，并支持前端控制台进行交互。
5. **RAG 引擎注入与飞轮限制**: 
    - 针对不同代码生成场景，配置强制过滤及注入规则 (例如写业务代码前必须预先查询并注入 Common 函数)。
    - 实现溯源积分算法：AI 生成代码时参考的历史节点，其对应开发者应当获得 Star 积分。

## 验收标准
- [ ] 能够成功解析 Python AST 并写入图谱与向量库。
- [ ] 资产状态能顺畅地从 `Development` 切换到 `Online` 并触发变更。
- [ ] RAG 回调时能正确执行 `status` 过滤条件和 `Starter` / `Common` 的高优召回。

## 变更记录
| 日期 | 变更 | 人员 |
|------|------|------|
| 2026-03-06 | 初始创建 | AI (Antigravity) |
