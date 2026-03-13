"""
SQL Summary Card v1 — TASK-KV-005

为 SQL 语句（尤其是 L3 复杂 SQL）生成语义摘要卡，字段：
  purpose     这条 SQL 的业务目的
  inputs      输入表 / 参数 / 来源
  outputs     输出结构 / 关键字段
  logic       核心处理逻辑（JOIN 策略、过滤条件等）
  biz_rules   从 SQL 推断出的业务规则（如 status=1 代表有效）
  risks       潜在风险（如全表扫描、缺少索引条件、PII 字段暴露）
  tags        自动标签
  sql_hash    SHA-256 内容哈希（SQL 变更后摘要自动失效）

失效机制：
  调用 SqlSummaryCardService.get_or_create() 时，
  若传入 SQL 的 sha256 与卡片存储的 sql_hash 不一致，
  则自动标记旧卡片为 stale=True 并重新生成。

存储：
  当前使用 Python 内存 dict 作为存储（MVP 级别），
  可替换为 PostgreSQL 表（字段已定义为 Pydantic 模型，方便迁移）。
"""

import hashlib
import uuid
from datetime import datetime

from loguru import logger
from pydantic import BaseModel, Field


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class SqlSummaryCard(BaseModel):
    """SQL 语义摘要卡（v1 Schema）。"""

    card_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sql_hash: str = Field(..., description="SHA-256 of original SQL content")
    artifact_path: str = Field(default="", description="SQL 文件路径（可选）")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    stale: bool = Field(default=False, description="True 时摘要已失效，需重新生成")

    # 摘要字段（LLM 生成）
    purpose: str = Field(default="", description="业务目的，一句话描述这条 SQL 做什么")
    inputs: list[str] = Field(default_factory=list, description="输入表名 / 参数列表")
    outputs: list[str] = Field(default_factory=list, description="输出字段 / 结果结构")
    logic: str = Field(default="", description="核心处理逻辑描述")
    biz_rules: list[str] = Field(default_factory=list, description="推断出的业务规则")
    risks: list[str] = Field(default_factory=list, description="潜在风险点")
    tags: list[str] = Field(default_factory=list, description="自动生成的标签")

    def is_valid_for(self, sql: str) -> bool:
        """检查摘要是否仍对当前 SQL 有效（hash 匹配且未失效）。"""
        return not self.stale and self.sql_hash == _sha256(sql)


class SqlSummaryCardService:
    """
    SQL 语义摘要卡服务。

    核心流程：
      1. get_or_create(sql): 检查内存缓存 → 若 hash 一致且未 stale 直接返回
      2. 否则调用 LLM 生成新摘要卡并缓存
      3. invalidate(card_id): 手动标记失效

    L3 强制生成原则：
      调用 get_or_create(sql, force_generate=True) 时（L3 场景）
      即使无缓存也必须生成而非返回 None。
    """

    def __init__(self):
        # MVP：内存存储 {sql_hash: SqlSummaryCard}
        self._store: dict[str, SqlSummaryCard] = {}

    def get_by_hash(self, sql: str) -> SqlSummaryCard | None:
        """按 SQL hash 查找有效摘要卡。"""
        h = _sha256(sql)
        card = self._store.get(h)
        if card and card.is_valid_for(sql):
            return card
        if card and not card.is_valid_for(sql):
            # 标记 stale
            card.stale = True
            logger.info(f"[SummaryCard] Card {card.card_id} marked stale (SQL changed)")
        return None

    async def get_or_create(
        self,
        sql: str,
        artifact_path: str = "",
        force_generate: bool = False,
    ) -> SqlSummaryCard:
        """
        获取或生成 SQL 摘要卡。

        Args:
            sql: SQL 文本
            artifact_path: SQL 文件路径（元信息）
            force_generate: True 时即使无缓存也强制生成（L3 SQL 使用）

        Returns:
            SqlSummaryCard
        """
        existing = self.get_by_hash(sql)
        if existing:
            return existing

        if not force_generate:
            # 非强制模式：生成空白占位卡
            h = _sha256(sql)
            placeholder = SqlSummaryCard(
                sql_hash=h,
                artifact_path=artifact_path,
                purpose="[未生成摘要，请调用 force_generate=True]",
            )
            return placeholder

        return await self._generate(sql, artifact_path)

    async def _generate(self, sql: str, artifact_path: str) -> SqlSummaryCard:
        """调用 LLM 生成摘要卡并写入缓存。"""
        from pydantic import BaseModel

        from app.core.algorithms.classification import classifier_service

        h = _sha256(sql)
        logger.info(f"[SummaryCard] Generating summary card for SQL hash={h[:8]}... path={artifact_path}")

        class SummaryExtraction(BaseModel):
            purpose: str
            inputs: list[str]
            outputs: list[str]
            logic: str
            biz_rules: list[str]
            risks: list[str]
            tags: list[str]

        prompt = (
            f"Analyze the following SQL and extract a structured summary.\n\n"
            f"SQL:\n```sql\n{sql[:6000]}\n```\n\n"
            "Return a JSON object with: purpose, inputs (table/param names), "
            "outputs (output column names or result description), logic (core processing logic), "
            "biz_rules (business rules inferred from conditions), "
            "risks (potential performance or data issues), tags (short descriptive tags)."
        )

        try:
            extraction = await classifier_service.extract_model(
                text=prompt,
                target_model=SummaryExtraction,
                instruction="You are a SQL analyst. Extract a structured summary of the given SQL.",
            )
            card = SqlSummaryCard(
                sql_hash=h,
                artifact_path=artifact_path,
                purpose=extraction.purpose,
                inputs=extraction.inputs,
                outputs=extraction.outputs,
                logic=extraction.logic,
                biz_rules=extraction.biz_rules,
                risks=extraction.risks,
                tags=extraction.tags,
            )
        except Exception as e:
            logger.error(f"[SummaryCard] LLM generation failed: {e}")
            # 生成带错误标记的降级卡
            card = SqlSummaryCard(
                sql_hash=h,
                artifact_path=artifact_path,
                purpose=f"[生成失败: {e}]",
                risks=["摘要生成失败，请人工审核"],
            )

        self._store[h] = card
        logger.success(f"[SummaryCard] Card {card.card_id} cached for hash={h[:8]}")
        return card

    def invalidate(self, card_id: str) -> bool:
        """手动失效某张摘要卡。返回是否找到并失效。"""
        for card in self._store.values():
            if card.card_id == card_id:
                card.stale = True
                logger.info(f"[SummaryCard] Manually invalidated card {card_id}")
                return True
        return False

    def invalidate_by_sql(self, sql: str) -> bool:
        """按 SQL 内容失效对应摘要卡。"""
        h = _sha256(sql)
        card = self._store.get(h)
        if card:
            card.stale = True
            return True
        return False

    def list_all(self) -> list[SqlSummaryCard]:
        return list(self._store.values())

    def stats(self) -> dict:
        total = len(self._store)
        stale = sum(1 for c in self._store.values() if c.stale)
        return {"total": total, "valid": total - stale, "stale": stale}


# 全局单例
sql_summary_card_service = SqlSummaryCardService()
