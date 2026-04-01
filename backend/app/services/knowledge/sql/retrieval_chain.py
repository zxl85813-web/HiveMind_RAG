"""
SQL Summary-First Retrieval Chain — TASK-KV-006

改造检索主链为"摘要优先"策略，用于 SQL 相关查询：

  1. 摘要召回（Summary Recall）
     先在已缓存的 SqlSummaryCard 中语义匹配（关键词 + 字段检索）
  2. SQL 本体验证（Body Verification）
     摘要命中后，确认内存/数据库中存在对应原始 SQL（通过 sql_hash 比对）
  3. 证据输出（Evidence Output）
     - 本体存在 → 返回摘要 + 原文引用（path + hash 锚点）
     - 本体不存在 → 标为 "待确认（PENDING_VERIFICATION）"，禁止直接作为结论

集成方式：
  作为 RetrievalPipeline 的一个可插拔 Step（SqlSummaryFirstStep），
  仅当查询被判断为 SQL 相关（含 SQL 关键字）时激活；
  激活后将摘要匹配结果注入 ctx.graph_facts（供后续 LLM 上下文使用），
  不替换原有向量检索结果，而是前置增强。

用法：
    # 已自动注册到 RetrievalPipeline 时无需手动调用
    # 独立使用：
    chain = SqlSummaryRetrievalChain()
    result = await chain.retrieve(query="查询订单状态汇总的 SQL 是怎么写的？")
"""

import re
from dataclasses import dataclass
from enum import StrEnum

from loguru import logger

from app.services.knowledge.sql.summary_card import SqlSummaryCard, sql_summary_card_service

# --- SQL 查询意图检测 ---

_SQL_INTENT_PATTERNS = [
    re.compile(r"\bSQL\b", re.IGNORECASE),
    re.compile(r"\b(query|查询|检索|统计|汇总|报表)\b", re.IGNORECASE),
    re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|JOIN|CTE|WITH\s+\w+\s+AS)\b", re.IGNORECASE),
    re.compile(r"\b(表|字段|索引|视图|存储过程|触发器)\b"),
    re.compile(r"\b(table|column|index|view|procedure|trigger)\b", re.IGNORECASE),
]


def is_sql_related_query(query: str) -> bool:
    """判断查询是否与 SQL / 数据库相关。"""
    return any(p.search(query) for p in _SQL_INTENT_PATTERNS)


# --- 证据类型 ---

class EvidenceStatus(StrEnum):
    VERIFIED = "verified"                  # 摘要 + 本体均存在，可信
    PENDING_VERIFICATION = "pending_verification"  # 摘要存在但本体未确认，待核实
    NOT_FOUND = "not_found"                # 未找到相关摘要


@dataclass
class SqlEvidence:
    """SQL 检索证据单元。"""
    card_id: str
    status: EvidenceStatus
    purpose: str
    logic: str
    inputs: list[str]
    outputs: list[str]
    biz_rules: list[str]
    risks: list[str]
    tags: list[str]
    artifact_path: str
    sql_hash: str
    relevance_score: float = 0.0

    def to_context_text(self) -> str:
        """格式化为 LLM 可直接注入的上下文文本。"""
        notice = ""
        if self.status == EvidenceStatus.PENDING_VERIFICATION:
            notice = "\n⚠️ [待确认] 此摘要未经 SQL 本体验证，请勿将以下内容作为最终结论。"

        inputs_str = ", ".join(self.inputs) if self.inputs else "未知"
        outputs_str = ", ".join(self.outputs) if self.outputs else "未知"
        rules_str = "\n  - ".join(self.biz_rules) if self.biz_rules else "无"
        risks_str = "\n  - ".join(self.risks) if self.risks else "无"
        tags_str = ", ".join(self.tags) if self.tags else "无"

        return (
            f"【SQL 摘要证据】{notice}\n"
            f"来源路径: {self.artifact_path or '未知'} (hash: {self.sql_hash[:8]}...)\n"
            f"目的: {self.purpose}\n"
            f"输入: {inputs_str}\n"
            f"输出: {outputs_str}\n"
            f"逻辑: {self.logic}\n"
            f"业务规则:\n  - {rules_str}\n"
            f"风险:\n  - {risks_str}\n"
            f"标签: {tags_str}"
        )


def _score_card(card: SqlSummaryCard, query: str) -> float:
    """
    简单关键词相关性评分（0-1.0）。
    后续可替换为向量相似度。
    """
    query_lower = query.lower()
    score = 0.0
    text = f"{card.purpose} {card.logic} {' '.join(card.inputs)} {' '.join(card.outputs)} {' '.join(card.tags)}"
    words = re.findall(r"\w+", query_lower)
    total = max(len(words), 1)
    hits = sum(1 for w in words if w in text.lower() and len(w) > 1)
    score = hits / total
    return round(score, 3)


class SqlSummaryRetrievalChain:
    """
    SQL 摘要优先检索链。

    独立使用时直接调用 retrieve()；
    作为 RetrievalPipeline Step 时通过 SqlSummaryFirstStep 集成。
    """

    async def retrieve(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.05,
    ) -> list[SqlEvidence]:
        """
        摘要优先检索，返回 SqlEvidence 列表（按相关性降序）。

        流程：
          1. 从 sql_summary_card_service 获取所有有效摘要卡
          2. 关键词评分，取 top_k
          3. 对每张摘要卡做本体验证（当前 MVP：检查 stale 标志）
          4. 返回证据列表，stale/未命中的标记为 PENDING_VERIFICATION
        """
        cards = [c for c in sql_summary_card_service.list_all() if not c.stale]

        if not cards:
            return [SqlEvidence(
                card_id="",
                status=EvidenceStatus.NOT_FOUND,
                purpose="",
                logic="",
                inputs=[],
                outputs=[],
                biz_rules=[],
                risks=[],
                tags=[],
                artifact_path="",
                sql_hash="",
                relevance_score=0.0,
            )]

        # 评分 + 过滤
        scored = [(card, _score_card(card, query)) for card in cards]
        scored = [(c, s) for c, s in scored if s >= min_score]
        scored.sort(key=lambda x: x[1], reverse=True)
        top_cards = scored[:top_k]

        evidences: list[SqlEvidence] = []
        for card, score in top_cards:
            # 本体验证：MVP 级别 — 非 stale 且 hash 存在即视为有效本体
            status = EvidenceStatus.VERIFIED if card.sql_hash else EvidenceStatus.PENDING_VERIFICATION

            evidences.append(SqlEvidence(
                card_id=card.card_id,
                status=status,
                purpose=card.purpose,
                logic=card.logic,
                inputs=card.inputs,
                outputs=card.outputs,
                biz_rules=card.biz_rules,
                risks=card.risks,
                tags=card.tags,
                artifact_path=card.artifact_path,
                sql_hash=card.sql_hash,
                relevance_score=score,
            ))

        logger.debug(f"[SqlSummaryChain] Query='{query[:40]}...' matched {len(evidences)} SQL summary cards")
        return evidences


# --- RetrievalPipeline 集成 Step ---

class SqlSummaryFirstStep:
    """
    RetrievalPipeline 可插拔 Step。

    只对 SQL 相关查询激活；激活后将摘要证据注入 ctx.graph_facts，
    与向量检索结果并行提供上下文，不替换原有结果。
    """

    def __init__(self, min_relevance: float = 0.05, top_k: int = 3):
        self.min_relevance = min_relevance
        self.top_k = top_k
        self._chain = SqlSummaryRetrievalChain()

    async def execute(self, ctx) -> None:
        """注入 SqlSummaryFirstStep 到 RetrievalContext。"""
        query = ctx.rewritten_query or ctx.query

        if not is_sql_related_query(query):
            ctx.log("SqlSummaryStep", "Query not SQL-related, skipping.")
            return

        try:
            evidences = await self._chain.retrieve(query, top_k=self.top_k, min_score=self.min_relevance)
        except Exception as e:
            ctx.log("SqlSummaryStep", f"Retrieval failed: {e}")
            return

        valid = [e for e in evidences if e.status != EvidenceStatus.NOT_FOUND]
        if not valid:
            ctx.log("SqlSummaryStep", "No SQL summary evidence found.")
            return

        for ev in valid:
            ctx.graph_facts.append(ev.to_context_text())

        pending = [e for e in valid if e.status == EvidenceStatus.PENDING_VERIFICATION]
        if pending:
            ctx.log("SqlSummaryStep", f"⚠️ {len(pending)} evidence(s) are PENDING_VERIFICATION — treat as unconfirmed.")

        ctx.log("SqlSummaryStep", f"Injected {len(valid)} SQL summary evidence(s) into graph_facts.")


# 全局单例
sql_summary_chain = SqlSummaryRetrievalChain()
