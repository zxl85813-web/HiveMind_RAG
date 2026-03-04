---
description: 设计与变更数据库表结构的规范向导，从设计模型到 Alembic 迁移
---

# 🗄️ 数据库设计与变更流水线

## 前置准备：了解设计标准

每次决定变更数据库表之前，**必须阅读**：[`.agent/rules/database-design-standards.md`](../rules/database-design-standards.md) 以确保遵守复数命名、审计字段和约束。

---

## 执行步骤

### Step 1: 确定是否有现成表结构可用
- 查看对应的模块下是否有类似实体 `backend/app/models/`，例如 `KnowledgeBase`。
- 与 PO (人类/主管) 确认，新需求是否在现有的大字段（如 JSON 类型 metadata）中增加冗余字段即可实现，而不一定需要连表外键结构。
- 若确实需要新表，转入下步。

### Step 2: 绘制设计图 (Mermaid ER)
在 `docs/design/DES-NNN.md` 中画下 ER 图（参考标准）。

> [注意] ER 图上必须清清楚楚写明关系是一对多 (`||--o{`) 还是多对多关系。若是多对多，别忘了单独设计关联表。

### Step 3: 在 `models/` 创建类
使用项目中定义的统一 ORM 模型基类（如 `SQLModel`）定义：

```python
# 例如: backend/app/models/user.py
class Chunk(SQLModel, table=True):
    __tablename__ = "chunks"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    document_id: uuid.UUID = Field(foreign_key="documents.id", ondelete="CASCADE")
    content: str = Field(sa_column=Column(Text, nullable=False))
    
    # 审计字段
    created_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"server_default": func.now()})
```

**必须更新 `backend/app/models/__init__.py`！确保在产生 alembic revision 前包含该类。如果在 `__init__.py` 没 import，Alembic 扫描不到将无法追踪变更！**

### Step 4: 产生数据库迁移快照 (Alembic)

// turbo
```bash
cd backend
alembic revision --autogenerate -m "feat(scope): 加上修改的简要说明, 关联 Issue #XXX"
```

### Step 5: 人工复审迁移脚本 (Review)
1. 打开 `backend/alembic/versions/` 刚生成的最新的 `xxxx_feat_scope_.py` 文件。
2. 检查 `upgrade()` 内是否漏掉外键/索引？（特别小心如果是字段改名操作的话，修改 autogenerate 成了 `op.alter_column`）。
3. 如果模型上增加的是非 Nullable 字段并且表里已有数据，**脚本里必须补上 default 值** 或者做先允许 nullable，然后写 Python 处理脚本刷历史数据，最后再将 column 改为 nullable=False 的手动流程。

### Step 6: 数据库应用变更 (Upgrade)

// turbo
```bash
cd backend
alembic upgrade head
```

### Step 7: 更新统一注册表
到 `REGISTRY.md` 下记录新产生的模型。并确保相关 API/Schema 能映射出这套底层结构的变化。
