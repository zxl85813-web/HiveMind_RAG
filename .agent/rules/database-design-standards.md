# 🗄️ 数据库设计与建表核心规范 (Database Design Standards)

本文档定义了 HiveMind RAG 项目中关于关系型数据库 (PostgreSQL / SQLite via SQLModel) 的设计、命名、约束及迁移规范。所有涉及数据模型的变更**必须**遵循此规范。

---

## 1. 命名规范 (Naming Conventions)

### 1.1 表与字段命名
- **表名 (Table Name)**: 使用复数形式的 `snake_case`。例如：`users`, `documents`, `knowledge_bases`, `chat_sessions`。
- **关联表名 (Association Table)**: 使用连接的两个表名，按字母顺序排序，例如：`document_tag_link`。
- **字段名 (Column Name)**: 使用 `snake_case`。例如：`first_name`, `is_active`, `max_tokens`。
- **布尔值字段**: 必须以 `is_`, `has_`, `can_` 开头。例如：`is_deleted`, `has_attachments`。

### 1.2 索引与约束命名 (Index & Constraint Naming)
为了防止通过 Alembic 迁移时出现命名冲突或不可控的匿名约束，必须遵守以下命名约定，并通过 SQLAlchemy 的 `naming_convention` 统一收口：
- **主键 (PK)**: `pk_<table>`
- **外键 (FK)**: `fk_<table>_<column>_<referred_table>`
- **唯一约束 (UQ)**: `uq_<table>_<column>`
- **普通索引 (IX)**: `ix_<table>_<column>`

> *注：项目中后端的 `db/session.py` 中已经配置了全局的 MetaData naming_convention。*

---

## 2. 核心字段要求 (Mandatory Columns)

所有的业务实体表都**必须**继承自基础模型 `HiveMindBaseModel` 或包含以下标准审计字段，以实现统一的生命周期管理：

1. **唯一标识 (`id`)**: 统一使用 `uuid.UUID` (UUID4)。
   - **理由**: 方便分布式系统集成、离线数据合并及前端安全（不泄露数据总量）。
   - **实现**: `Field(default_factory=uuid.uuid4, primary_key=True)`。
2. **审计时间戳**:
   - `created_at`: 创建时间。使用 Python 层 `datetime.now(timezone.utc)` 填充。
   - `updated_at`: 更新时间。使用 Python 层填充，并配合 **SQLAlchemy Event Hooks (before_update)** 自动维护。
   - **注意**: 统一在 Python 应用层处理时间戳，以保持跨数据库（PG/SQLite）的行为一致性。
3. **审计操作人**:
   - `created_by`: 创建者标识 (UUID 或 String ID)。
   - `updated_by`: 最后修改者标识。
4. **软删除 (`is_deleted`)**: 
   - 所有的核心业务模型必须包含此字段，默认为 `False`。
   - **规则**: 除非明确需要物理删除（如临时 Cache），否则禁止直接进行硬删除。

> **技术决策 (Refined)**: 
> - **查询安全**: 所有的查询逻辑**必须手动**包含 `.where(Model.is_deleted == False)`。AI Agent 和代码评审者需严格检查此项以防数据泄露。
> - **自动化**: 项目配置了 SQLAlchemy 拦截器，在 `session.commit()` 前自动同步 `updated_at`，开发者无需在 Service 层显式更新。

---

## 3. 数据类型选择指南 (Data Type Selection)

不要滥用 `String`。SQLModel 底层包装了 SQLAlchemy，遵循以下选型：

| 场景 | SQLAlchemy/SQLModel 类型 | 数据库实际类型 (PG) | 备注 |
|---|---|---|---|
| 短文本 (名字、邮箱、标题) | `String(255)` | `VARCHAR(255)` | 必加长度限制。 |
| 长文本 (文章内容、详细描述) | `Text` | `TEXT` | 无长度限制。 |
| 布尔开关 | `Boolean` | `BOOLEAN` | 必须设置 default 值，不可为 null。 |
| 货币/精度数值 | `Numeric(10, 2)` | `NUMERIC` | 坚决禁止用 Float 存钱。 |
| JSON 结构化数据 | `JSON` / `JSONB` | `JSONB` | 用于无需建立强关系但需要查询的扩展字段 (如 `metadata`)。 |
| 数组 (如果 DB 支持) | `ARRAY(String)` | `VARCHAR[]` | 对于简单的 tag，可考虑用数组替代关联表。 |

---

## 4. 关联关系设计原则 (Relationship Principles)

- **外键级联 (Cascade)**: 
  - 弱实体（如从属于知识库的分割块 `chunks`）：推荐使用 `ondelete="CASCADE"`，知识库删除时，块一同被物理删除引擎清空。
  - 重要关联（如用户和其创建的资源）：推荐软删除或不允许直接级联删除。
- **冗余字段 (Denormalization)**:
  - 尽量避免冗余，遵守三范式。
  - **例外**: 如果跨表 Join 严重影响高频接口性能，考虑在业务写入时冗余计算结果字段（例如 `document_count`，并在变更时加悲观锁/事件钩子同步更新）。

---

## 5. ER 图强制模板 (Mermaid ER Diagram)

在编写任何有关数据库变更的 `设计文档 (DES-NNN.md)` 或 `ADR` 时，**必须使用以下 Mermaid ER 图模板**，清楚标明主外键、一对多关系以及是否允许 Null：

```mermaid
erDiagram
    %% 实体定义示例
    USERS {
        uuid id PK
        string email ""
        string hashed_password ""
        boolean is_active ""
        datetime created_at ""
    }
    
    KNOWLEDGE_BASES {
        uuid id PK
        uuid owner_id FK "nullable: false"
        string name ""
        text description "nullable: true"
    }

    %% 关系连线: 一对多 (One to Many)
    USERS ||--o{ KNOWLEDGE_BASES : "creates"
```
*(注意：在 `{}` 内部，格式为 `[类型] [字段名] [备注(如 PK/FK/nullable)]`)*

---

## 6. Alembic 迁移规范 (Alembic Migration Guidelines)

1. **绝对禁止直接修改生产库表结构**，所有修改必须通过 Alembic Revision 产生。
2. 每次自动生成 Revision 后，**必须人工/AI复审**脚本：
   - Alembic 无法自动探测列名重命名（它会当作 Drop Column + Add Column）。如果重命名列，修改生成的脚本，使用 `op.alter_column`。
   - 确认 Enum 类型在 PostgreSQL 中是否被正确创建。
3. `revision` message 参数必须包含所关联的 Issue ID，例如：`alembic revision --autogenerate -m "feat(rag): add chunk table for Issue #12"`。

---

> 💡 **可扩展性与规则豁免**:
> 本文档定义的是标准场景下的通用规范。如果在极其特殊的业务或性能要求下必须突破这些规则，请参见 [`design-and-implementation-methodology.md`](design-and-implementation-methodology.md) 中的"特例豁免机制"（例如强制要求在代码中写明注释或生成 ADR）。
