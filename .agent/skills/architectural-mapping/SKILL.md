---
name: architectural-mapping
description: 基于 Neo4j 的架构资产图谱映射，实现从需求到代码的精准路径发现
---

# 🕸️ 架构资产图谱技能 (Skill)

> **使用场景**: 
> 1. 当需要快速理清一个 `REQ-NNN` 关联的所有设计文档、技能和文件时。
> 2. 当需要节省 Tokens，避免暴力搜索全库，而是通过图谱精准定位上下文时。

## 📚 Skill Assets (Three-Layer Model)

### 1. Knowledge Library (`library/`)
- **ontology-schema.md**: 定义了图谱中所有的 Label (Requirement, Design, File...) 和 Relationship。在构造查询前应阅读此文档。

### 2. Templates (`prompts/`)
- **cypher-generation.j2**: 预定义的 Cypher 查询模板，用于影响分析、上下文发现等高频场景。

### 3. Execution Scripts (`scripts/`)
- **index_architecture.py**: 全量/增量资产索引脚本。
- **query_architecture.py**: 封装好的 Cypher 查询接口。

## 📝 Execution Steps (Advanced)

### Step 1: Schema Ingestion
- Reference `library/ontology-schema.md` to understand available nodes and relations.

### Step 2: Mapping / Querying
- To find context for a task:
  ```powershell
  python .agent/skills/architectural-mapping/scripts/query_architecture.py --req "REQ-XXX"
  ```
- To update the graph after code/doc changes:
  ```powershell
  python .agent/skills/architectural-mapping/scripts/index_architecture.py
  ```

### Step 3: Knowledge Augmentation
- If the graph returns relevant files, use `view_file` to read them and augment your context.
- Use `prompts/cypher-generation.j2` if you need complex traversals.

### Step 4: Code Similarity (Anti-Duplication)
- Before creating a new service or component, run the block-level similarity tool:
  ```powershell
  python skills/architectural-mapping/scripts/code_similarity_tool.py --dir frontend/src --threshold 0.8
  ```
- If a match > 0.8 is found, analyze blocks A and B for refactoring potential.

## 🛡️ Best Practices
- **Impact First**: Perform an impact analysis query before any major refactoring.
- **Sync Often**: Run `index_architecture.py` after completing a DES or REQ document.
- **Clean Logic**: Keep similarity thresholds at 0.8 for design-time and 0.9 for CI-time.
