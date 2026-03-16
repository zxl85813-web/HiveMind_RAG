# 🕸️ 架构资产图谱本体定义 (Ontology Schema)

## 1. 节点标签 (Node Labels)

- **`Requirement`**: 表示业务需求 (REQ-NNN)。
  - `id`: 需求 ID (如 REQ-011)
  - `title`: 标题
  - `path`: 文件路径
- **`Design`**: 表示技术设计 (DES-NNN)。
  - `id`: 设计 ID
  - `title`: 标题
  - `path`: 文件路径
- **`Skill`**: 表示 Agent 技能包。
  - `name`: 技能名称
  - `description`: 简单描述
- **`File`**: 表示代码库中的具体文件。
  - `path`: 绝对或相对路径
  - `extension`: 文件扩展名
- **`Component`**: 表示前端或后端的核心组件/服务。

## 2. 关系定义 (Relationships)

- `(:Requirement)-[:EVOLVES_TO]->(:Design)`: 需求演进为设计。
- `(:Design)-[:IMPLEMENTED_BY]->(:File)`: 设计落位到具体代码文件。
- `(:Design)-[:REQUIRES_SKILL]->(:Skill)`: 完成该设计需要特定的 Agent 技能。
- `(:File)-[:DEPENDS_ON]->(:File)`: 代码层面的文件依赖。
- `(:Requirement)-[:TAGGED_WITH]->(:Concept)`: 需求涉及的关键技术概念。

## 3. Cypher 常规查询模式

### 查找需求关联的所有代码
```cypher
MATCH (r:Requirement {id: $req_id})-[:EVOLVES_TO]->(d:Design)-[:IMPLEMENTED_BY]->(f:File)
RETURN f.path
```

### 查找受文件变更影响的设计范围
```cypher
MATCH (f:File {path: $file_path})<-[:IMPLEMENTED_BY]-(d:Design)
RETURN d.id, d.title
```
