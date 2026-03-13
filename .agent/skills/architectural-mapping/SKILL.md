---
name: architectural-mapping
description: 基于 Neo4j 的架构资产图谱映射，实现从需求到代码的精准路径发现
---

# 🕸️ 架构资产图谱技能 (Skill)

> **使用场景**: 
> 1. 当需要快速理清一个 `REQ-NNN` 关联的所有设计文档、技能和文件时。
> 2. 当需要节省 Tokens，避免暴力搜索全库，而是通过图谱精准定位上下文时。

## 🛠 前提条件

1.  确保 Neo4j 数据库已运行。
2.  确保 `backend/.env` 中已配置 `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`。

## 📝 执行步骤

### 步骤 1: 资产索引 (Indexing)
每次项目结构有重大变更（新增 REQ, DES 或 Skill）后执行：
// turbo
```powershell
python skills/architectural-mapping/scripts/index_architecture.py
```

### 步骤 2: 路径查找 (Querying)
当你需要为一个需求提供实现建议，但不确定该读哪些文件时：
// turbo
```powershell
python skills/architectural-mapping/scripts/query_architecture.py --req "REQ-011"
```

## 🛡️ 最佳实践
- **图谱优先**: 在开始任何重大型重构前，先查询图谱，识别“受影响节点”。
- **闭环维护**: 在 `update-todo` 流程中，建议顺便执行一次 `index_architecture.py` 以保持图谱最新。
- **精准注入**: 只读取图谱返回的路径文件，而非使用全局 `grep` 产生大量噪音。
