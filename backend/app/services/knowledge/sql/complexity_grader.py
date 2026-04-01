"""
SQL Complexity Grader — TASK-KV-003

自动将 SQL 语句分级为 L1（简单）/ L2（中等）/ L3（复杂），并给出分值。

分级规则（可复现，无 LLM 依赖）：
  L1（0-15分）：  单表查询、无子查询、无 CTE、无窗口函数
  L2（16-40分）：  多表 JOIN（1-3个）、有子查询或 GROUP BY/HAVING
  L3（41+分）：  CTE、窗口函数、4+ JOIN、深层嵌套子查询、DDL/DML 混合

分值构成（各维度累加）：
  JOIN 数量      × 8   （最高 40）
  子查询深度     × 10  （最高 50）
  CTE 数量       × 15  （最高 60）
  窗口函数数量   × 12  （最高 48）
  UNION/INTERSECT × 5 （最高 20）
  DDL/DML 语句   × 10  （固定加分）
  聚合函数密度   × 3   （最高 24）
  HAVING         + 5
"""

import re
from dataclasses import dataclass, field

from app.schemas.artifact import SqlComplexityLevel

# --- 正则特征提取 ---

_RE_JOIN = re.compile(r"\b(INNER|LEFT|RIGHT|FULL|CROSS)?\s*JOIN\b", re.IGNORECASE)
_RE_CTE = re.compile(r"\bWITH\b", re.IGNORECASE)
_RE_CTE_BLOCK = re.compile(r"\bWITH\s+(\w+)\s+AS\s*\(", re.IGNORECASE)
_RE_WINDOW_FN = re.compile(r"\b(ROW_NUMBER|RANK|DENSE_RANK|NTILE|LAG|LEAD|FIRST_VALUE|LAST_VALUE|NTH_VALUE|SUM|AVG|COUNT|MIN|MAX)\s*\(.*?\)\s*OVER\s*\(", re.IGNORECASE)
_RE_SUBQUERY = re.compile(r"\(\s*SELECT\b", re.IGNORECASE)
_RE_UNION = re.compile(r"\b(UNION|INTERSECT|EXCEPT)\b", re.IGNORECASE)
_RE_DDL_DML = re.compile(r"\b(INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|MERGE)\b", re.IGNORECASE)
_RE_AGGREGATE = re.compile(r"\b(COUNT|SUM|AVG|MIN|MAX|GROUP_CONCAT|STRING_AGG)\s*\(", re.IGNORECASE)
_RE_HAVING = re.compile(r"\bHAVING\b", re.IGNORECASE)
_RE_GROUP_BY = re.compile(r"\bGROUP\s+BY\b", re.IGNORECASE)


def _count_subquery_depth(sql: str) -> int:
    """计算最深层嵌套 SELECT 的深度。"""
    max_depth = 0
    current_depth = 0
    # 简单括号计数法：遇到 (SELECT 深度+1，遇到配对 ) 深度-1
    i = 0
    while i < len(sql):
        if sql[i:i+1] == "(":
            # 向后看是否跟着 SELECT（允许空白）
            ahead = sql[i + 1:i + 20].lstrip()
            if ahead.upper().startswith("SELECT"):
                current_depth += 1
                max_depth = max(max_depth, current_depth)
        elif sql[i:i+1] == ")":
            if current_depth > 0:
                current_depth -= 1
        i += 1
    return max_depth


@dataclass
class ComplexityReport:
    """复杂度分析报告。"""
    level: SqlComplexityLevel
    score: float
    join_count: int = 0
    cte_count: int = 0
    window_fn_count: int = 0
    subquery_depth: int = 0
    union_count: int = 0
    has_ddl_dml: bool = False
    aggregate_count: int = 0
    has_group_by: bool = False
    has_having: bool = False
    breakdown: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "level": self.level.value,
            "score": round(self.score, 1),
            "join_count": self.join_count,
            "cte_count": self.cte_count,
            "window_fn_count": self.window_fn_count,
            "subquery_depth": self.subquery_depth,
            "union_count": self.union_count,
            "has_ddl_dml": self.has_ddl_dml,
            "aggregate_count": self.aggregate_count,
            "has_group_by": self.has_group_by,
            "has_having": self.has_having,
            "breakdown": self.breakdown,
        }


class SqlComplexityGrader:
    """SQL 复杂度分级器（纯规则，无 LLM，可复现）。"""

    def grade(self, sql: str) -> ComplexityReport:
        """
        对单条或多语句 SQL 进行复杂度分级。

        Args:
            sql: SQL 文本（可含多个语句）

        Returns:
            ComplexityReport
        """
        sql_upper = sql.upper()

        join_count = len(_RE_JOIN.findall(sql))
        cte_count = len(_RE_CTE_BLOCK.findall(sql))
        window_fn_count = len(_RE_WINDOW_FN.findall(sql))
        subquery_depth = _count_subquery_depth(sql)
        union_count = len(_RE_UNION.findall(sql))
        has_ddl_dml = bool(_RE_DDL_DML.search(sql))
        aggregate_count = len(_RE_AGGREGATE.findall(sql))
        has_group_by = bool(_RE_GROUP_BY.search(sql))
        has_having = bool(_RE_HAVING.search(sql))

        # 分值计算
        breakdown = {
            "join":        min(join_count * 8, 40),
            "subquery":    min(subquery_depth * 10, 50),
            "cte":         min(cte_count * 15, 60),
            "window_fn":   min(window_fn_count * 12, 48),
            "union":       min(union_count * 5, 20),
            "ddl_dml":     10 if has_ddl_dml else 0,
            "aggregate":   min(aggregate_count * 3, 24),
            "having":      5 if has_having else 0,
        }
        score = float(sum(breakdown.values()))

        # 分级
        if score <= 15:
            level = SqlComplexityLevel.L1
        elif score <= 40:
            level = SqlComplexityLevel.L2
        else:
            level = SqlComplexityLevel.L3

        return ComplexityReport(
            level=level,
            score=score,
            join_count=join_count,
            cte_count=cte_count,
            window_fn_count=window_fn_count,
            subquery_depth=subquery_depth,
            union_count=union_count,
            has_ddl_dml=has_ddl_dml,
            aggregate_count=aggregate_count,
            has_group_by=has_group_by,
            has_having=has_having,
            breakdown=breakdown,
        )

    def grade_batch(self, sql_list: list[str]) -> list[ComplexityReport]:
        return [self.grade(sql) for sql in sql_list]


# 全局单例
sql_complexity_grader = SqlComplexityGrader()
