"""
Long SQL Splitter — TASK-KV-004

将长 SQL 文本切分为可独立检索的逻辑单元，支持：
  1. 语句边界切分（按 `;` 分隔）
  2. CTE 逻辑段切分（每个 WITH xxx AS (...) 块为独立段落）
  3. 父子关系：CTE 块是主查询语句的子段

切分后每个 SqlSegment 携带：
  - 原文位置（start_offset/end_offset）→ 可回拼定位原文
  - 父段 ID（parent_id）→ CTE -> 主语句
  - 段类型（statement / cte_block / main_query）

验收规则：
  - 超长 SQL 不超时（纯文本处理，无 LLM）
  - 切分后可通过 SqlSplitter.reassemble() 无损回拼
"""

import re
import uuid
from dataclasses import dataclass, field
from enum import StrEnum


class SegmentType(StrEnum):
    STATEMENT = "statement"       # 完整的 SQL 语句（非 CTE 场景）
    CTE_BLOCK = "cte_block"       # 单个 CTE 块（WITH xxx AS (...) 内容）
    MAIN_QUERY = "main_query"     # CTE 后的主查询体


@dataclass
class SqlSegment:
    """SQL 切分单元。"""
    segment_id: str
    content: str
    segment_type: SegmentType
    index: int                        # 在原始 SQL 中的顺序序号
    start_offset: int                 # 在原始 SQL 文本中的字符起始位
    end_offset: int                   # 字符结束位（exclusive）
    parent_id: str | None = None      # CTE/main_query 指向所属 STATEMENT 的 segment_id
    cte_name: str | None = None       # 仅 CTE_BLOCK 有效
    children: list[str] = field(default_factory=list)  # STATEMENT 的子段 ID 列表

    def to_dict(self) -> dict:
        return {
            "segment_id": self.segment_id,
            "segment_type": self.segment_type.value,
            "index": self.index,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "parent_id": self.parent_id,
            "cte_name": self.cte_name,
            "content_preview": self.content[:200],
        }


# --- 内部工具函数 ---

_RE_STMT_SPLIT = re.compile(r";[ \t]*(?:\n|$)", re.MULTILINE)
_RE_CTE_NAMED = re.compile(r"\bWITH\s+(\w+)\s+AS\s*\(", re.IGNORECASE)


def _find_matching_paren(text: str, open_pos: int) -> int:
    """从 open_pos（`(` 的位置）向后找到配对的 `)` 位置。
    返回 `)` 的 index；找不到则返回 len(text)-1。"""
    depth = 0
    i = open_pos
    in_single_quote = False
    in_double_quote = False
    while i < len(text):
        c = text[i]
        if c == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
        elif c == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
        elif not in_single_quote and not in_double_quote:
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return len(text) - 1


def _split_statements(sql: str) -> list[tuple[str, int, int]]:
    """
    按语句边界（`;`）拆分 SQL，返回 (statement_text, start, end) 的列表。
    保留空白行，确保 start+end 可回拼原文。
    """
    segments: list[tuple[str, int, int]] = []
    last = 0
    for m in _RE_STMT_SPLIT.finditer(sql):
        end = m.end()
        stmt = sql[last:end].strip()
        if stmt:
            segments.append((stmt, last, end))
        last = end
    # 尾部没有分号的最后一段
    tail = sql[last:].strip()
    if tail:
        segments.append((tail, last, len(sql)))
    return segments


def _extract_cte_blocks(stmt_text: str, stmt_start: int) -> list[tuple[str, int, int, str]]:
    """
    从单个语句中提取所有 CTE 块的 (cte_text, abs_start, abs_end, cte_name)。
    只提取顶层 CTE（WITH xxx AS (...)）。
    """
    blocks: list[tuple[str, int, int, str]] = []
    for m in _RE_CTE_NAMED.finditer(stmt_text):
        cte_name = m.group(1)
        open_paren = stmt_text.index("(", m.start())
        close_paren = _find_matching_paren(stmt_text, open_paren)
        cte_content = stmt_text[open_paren + 1: close_paren].strip()
        abs_start = stmt_start + open_paren + 1
        abs_end = stmt_start + close_paren
        blocks.append((cte_content, abs_start, abs_end, cte_name))
    return blocks


def _extract_main_query(stmt_text: str, stmt_start: int) -> tuple[str, int, int] | None:
    """
    从含 CTE 的语句中提取主查询部分（最后一个 CTE 块之后的 SELECT/INSERT/... 语句）。
    """
    if not _RE_CTE_NAMED.search(stmt_text):
        return None
    # 找到所有 CTE 块结束位置，主查询是最后一个 ) 之后的内容
    last_close = 0
    for m in _RE_CTE_NAMED.finditer(stmt_text):
        open_paren = stmt_text.index("(", m.start())
        close_paren = _find_matching_paren(stmt_text, open_paren)
        last_close = max(last_close, close_paren)
    main_text = stmt_text[last_close + 1:].strip().lstrip(",").strip()
    abs_start = stmt_start + last_close + 1
    abs_end = stmt_start + len(stmt_text)
    return main_text, abs_start, abs_end


class SqlSplitter:
    """
    长 SQL 切分器。
    支持：语句边界切分 + CTE 逻辑段切分 + 父子段落关系。
    """

    def split(self, sql: str) -> list[SqlSegment]:
        """
        切分 SQL 为 SqlSegment 列表。

        总策略：
          1. 先按 `;` 切分出所有语句
          2. 对每条语句检测是否含 CTE；含则进一步切出 CTE 块 + 主查询
          3. 建立父子关系

        Returns:
            list[SqlSegment]，按 index 升序排列
        """
        statements = _split_statements(sql)
        segments: list[SqlSegment] = []
        idx = 0

        for stmt_text, stmt_start, stmt_end in statements:
            stmt_id = str(uuid.uuid4())
            has_cte = bool(_RE_CTE_NAMED.search(stmt_text))

            if has_cte:
                # --- CTE 语句：拆出 CTE 块 + 主查询 ---
                parent_seg = SqlSegment(
                    segment_id=stmt_id,
                    content=stmt_text,
                    segment_type=SegmentType.STATEMENT,
                    index=idx,
                    start_offset=stmt_start,
                    end_offset=stmt_end,
                )
                idx += 1

                cte_blocks = _extract_cte_blocks(stmt_text, stmt_start)
                for cte_content, cte_start, cte_end, cte_name in cte_blocks:
                    cte_id = str(uuid.uuid4())
                    child_seg = SqlSegment(
                        segment_id=cte_id,
                        content=cte_content,
                        segment_type=SegmentType.CTE_BLOCK,
                        index=idx,
                        start_offset=cte_start,
                        end_offset=cte_end,
                        parent_id=stmt_id,
                        cte_name=cte_name,
                    )
                    parent_seg.children.append(cte_id)
                    segments.append(child_seg)
                    idx += 1

                main_result = _extract_main_query(stmt_text, stmt_start)
                if main_result:
                    main_text, main_start, main_end = main_result
                    main_id = str(uuid.uuid4())
                    main_seg = SqlSegment(
                        segment_id=main_id,
                        content=main_text,
                        segment_type=SegmentType.MAIN_QUERY,
                        index=idx,
                        start_offset=main_start,
                        end_offset=main_end,
                        parent_id=stmt_id,
                    )
                    parent_seg.children.append(main_id)
                    segments.append(main_seg)
                    idx += 1

                # 父段插在子段之前（按 index 排序后顺序正确）
                segments.insert(0, parent_seg) if idx == 1 else segments.append(parent_seg)

            else:
                # --- 普通语句：直接作为 STATEMENT ---
                seg = SqlSegment(
                    segment_id=stmt_id,
                    content=stmt_text,
                    segment_type=SegmentType.STATEMENT,
                    index=idx,
                    start_offset=stmt_start,
                    end_offset=stmt_end,
                )
                segments.append(seg)
                idx += 1

        # 按 index 升序
        segments.sort(key=lambda s: s.index)
        return segments

    def reassemble(self, segments: list[SqlSegment], original_sql: str) -> str:
        """
        通过 start_offset/end_offset 从原始 SQL 中无损回拼。
        只取顶层 STATEMENT 段，不重复拼 CTE 子段。
        """
        top_level = [s for s in segments if s.segment_type == SegmentType.STATEMENT]
        top_level.sort(key=lambda s: s.start_offset)
        return "\n".join(original_sql[s.start_offset:s.end_offset] for s in top_level)


# 全局单例
sql_splitter = SqlSplitter()
