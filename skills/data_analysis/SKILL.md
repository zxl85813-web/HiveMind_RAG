---
name: data_analysis
description: "数据分析与可视化 — 执行 SQL 查询、数据处理、统计分析和图表生成。当用户需要对结构化数据进行查询、分析或可视化时使用此 Skill。包括：(1) SQL 查询构建与执行 (2) Pandas 数据处理与清洗 (3) 统计分析与趋势检测 (4) 图表和报告生成 (5) 数据导出（CSV/Excel）。触发关键词：查询数据、统计分析、生成报表、数据可视化、SQL、图表、趋势分析。"
---

# Data Analysis Skill

## Overview

对结构化数据进行查询、分析和可视化。核心原则：**数据正确性 > 分析深度 > 展示美观**。

## Quick Reference

| 任务 | 工具 | 说明 |
|------|------|------|
| SQL 查询 | `execute_sql` | 安全执行 SQL（只读） |
| 数据分析 | `analyze_data` | Pandas 统计分析 |
| 图表生成 | `generate_chart` | 生成可视化图表 |
| 数据导出 | `export_data` | 导出为 CSV/Excel |
| 数据清洗 | `clean_data` | 处理缺失值、异常值 |

---

## SQL 查询

### 安全规则（不可违反）

```python
# ❌ 绝对禁止 — 任何写操作
"DROP TABLE users"
"DELETE FROM messages WHERE ..."
"UPDATE users SET ..."
"INSERT INTO ..."
"TRUNCATE TABLE ..."

# ✅ 只允许 — SELECT 查询
"SELECT * FROM users WHERE created_at > '2026-01-01'"
"SELECT COUNT(*) FROM messages GROUP BY conversation_id"
```

**强制约束：**
- 所有查询都通过只读连接执行
- 自动添加 `LIMIT` 防止全表扫描（默认 `LIMIT 1000`）
- 禁止 `SELECT *` 在大表上使用，必须指定列
- 超时限制：单次查询最长 30 秒

### 查询构建最佳实践

```sql
-- ❌ 错误 — 没有 LIMIT，没有 WHERE
SELECT * FROM messages;

-- ✅ 正确 — 明确列、条件、限制
SELECT 
    m.id,
    m.content,
    m.created_at,
    c.title AS conversation_title
FROM messages m
JOIN conversations c ON m.conversation_id = c.id
WHERE m.created_at >= '2026-02-01'
ORDER BY m.created_at DESC
LIMIT 100;
```

**查询优化：**
- **先查表结构** — 执行 SQL 前先了解表的列名和类型
- **用 COUNT 先探** — 大查询前先 `SELECT COUNT(*)` 评估数据量
- **加 WHERE 过滤** — 尽可能缩小查询范围
- **避免 N+1** — 用 JOIN 替代循环查询
- **使用索引列** — WHERE 条件优先使用有索引的列

### HiveMind 数据库表参考

| 表名 | 主要用途 | 关键列 |
|------|----------|--------|
| `users` | 用户信息 | id, username, email, role, created_at |
| `conversations` | 对话会话 | id, user_id, title, created_at |
| `messages` | 对话消息 | id, conversation_id, role, content, created_at |
| `knowledge_bases` | 知识库 | id, name, description, document_count |
| `documents` | 文档 | id, knowledge_base_id, filename, status |

---

## 数据分析

### 分析流程

```
原始数据 → 数据清洗 → 探索性分析(EDA) → 统计分析 → 可视化 → 结论
```

### 1. 数据清洗

```python
import pandas as pd

# 加载数据
df = pd.read_sql(query, connection)

# 检查数据质量
print(f"行数: {len(df)}")
print(f"缺失值:\n{df.isnull().sum()}")
print(f"数据类型:\n{df.dtypes}")

# 清洗
df = df.dropna(subset=["critical_column"])        # 删除关键列的缺失行
df["value"] = df["value"].fillna(df["value"].median())  # 填充非关键列
df = df.drop_duplicates()                          # 去重
df["date"] = pd.to_datetime(df["date"])            # 类型转换
```

### 2. 探索性分析 (EDA)

```python
# 基础统计
print(df.describe())

# 分布检查
print(df["column"].value_counts())

# 时间趋势
daily = df.groupby(df["created_at"].dt.date).size()

# 相关性
correlation = df[["col_a", "col_b", "col_c"]].corr()
```

### 3. 常见分析模式

**趋势分析：**
```python
# 日/周/月聚合
monthly = df.resample("M", on="created_at").agg({
    "id": "count",          # 数量
    "value": ["mean", "sum"],  # 均值和总和
})
# 环比增长
monthly["growth"] = monthly["id"]["count"].pct_change()
```

**分组对比：**
```python
# 按维度分组比较
comparison = df.groupby("category").agg({
    "value": ["mean", "median", "std"],
    "id": "count",
})
```

**漏斗分析：**
```python
funnel = {
    "访问": len(df),
    "注册": len(df[df["registered"]]),
    "首次对话": len(df[df["first_chat"]]),
    "活跃用户": len(df[df["active"]]),
}
# 转化率
for i, (stage, count) in enumerate(funnel.items()):
    if i > 0:
        prev_count = list(funnel.values())[i - 1]
        rate = count / prev_count * 100
        print(f"{stage}: {count} ({rate:.1f}%)")
```

---

## 可视化

### 图表选择指南

| 数据类型 | 推荐图表 | 适用场景 |
|----------|----------|----------|
| 时间趋势 | 折线图 | 用户增长、日活趋势 |
| 分类对比 | 柱状图 | 各Agent使用频率对比 |
| 占比分布 | 饼图/环形图 | 知识库类型分布 |
| 双变量关系 | 散点图 | 响应时间 vs 消息长度 |
| 分布形态 | 直方图/箱线图 | 查询延迟分布 |
| 多维数据 | 热力图 | 每小时每天的使用热度 |

### 图表规范

```python
import matplotlib.pyplot as plt
import matplotlib

# 中文字体支持
matplotlib.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]
matplotlib.rcParams["axes.unicode_minus"] = False

# HiveMind 配色方案
COLORS = {
    "primary": "#4F46E5",      # 主色 - 靛蓝
    "secondary": "#10B981",    # 辅色 - 翡翠绿
    "accent": "#F59E0B",       # 强调 - 琥珀
    "danger": "#EF4444",       # 警告 - 红
    "neutral": "#6B7280",      # 中性 - 灰
    "background": "#F9FAFB",   # 背景 - 浅灰
}

PALETTE = [
    "#4F46E5", "#10B981", "#F59E0B", 
    "#EF4444", "#8B5CF6", "#EC4899",
    "#06B6D4", "#84CC16",
]

def create_chart(data, chart_type, title, **kwargs):
    """创建标准化图表"""
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(COLORS["background"])
    
    # 根据类型绘制
    if chart_type == "line":
        ax.plot(data.index, data.values, color=COLORS["primary"], linewidth=2)
    elif chart_type == "bar":
        ax.bar(data.index, data.values, color=PALETTE[:len(data)])
    
    ax.set_title(title, fontsize=14, fontweight="bold", pad=20)
    ax.spines[["top", "right"]].set_visible(False)  # 去掉右上边框
    plt.tight_layout()
    return fig
```

### 呈现规范

每个图表必须包含：
1. **标题** — 清晰描述图表展示的内容
2. **轴标签** — X/Y 轴的含义和单位
3. **数据标注** — 关键数值标注在图表上
4. **时间范围** — 数据的起止时间
5. **数据说明** — 简要文字解释图表传达的洞察

---

## 结果呈现

### 分析报告格式

```markdown
## 📊 数据分析报告

### 概要
- **数据范围**: 2026-01-01 至 2026-02-16
- **记录数**: 12,456 条
- **关键发现**: [1-2 句话概括最重要的发现]

### 关键指标

| 指标 | 当前值 | 环比变化 | 趋势 |
|------|--------|----------|------|
| 日活用户 | 1,234 | +12.3% | 📈 |
| 平均对话轮数 | 8.5 | -2.1% | 📉 |
| 知识库命中率 | 78.2% | +5.4% | 📈 |

### 详细分析
[图表] + [文字解读]

### 建议
基于以上数据，建议：
1. ...
2. ...
```

---

## 常见陷阱

- **不要执行写操作** — 所有 SQL 必须是只读的 SELECT
- **不要信任没有清洗的数据** — 先检查缺失值、异常值、重复数据
- **不要只看平均值** — 均值容易被极端值影响，同时关注中位数和分布
- **不要忽略样本量** — 数据量太少的结论不可靠，要标注样本量
- **不要过度解读噪声** — 短期波动不代表趋势，需要足够的时间跨度
- **不要生成无标题图表** — 每个图表必须有标题、轴标签和数据说明
- **不要在没有 LIMIT 的情况下查大表** — 可能导致超时或内存溢出

---

## Tools

- `execute_sql`: 安全执行只读 SQL 查询
- `analyze_data`: 对查询结果进行统计分析
- `generate_chart`: 生成可视化图表（支持多种类型）
- `export_data`: 导出数据为 CSV/Excel 文件
- `clean_data`: 数据清洗和预处理
