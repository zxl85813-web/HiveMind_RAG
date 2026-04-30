"""QuoteIntelligenceService — orchestrates the full demo pipeline.

Stages:
    1. fetch    — pull tenant-scoped quotes from PostgreSQL
    2. mask     — replace PII via TokenVault (reversible)
    3. top_n    — algorithmic ranking (default: amount-weighted recency)
    4. analyze  — feed masked top-N to the LLMRouter (BALANCED tier),
                  prompt asks for a markdown sales-intel report
    5. unmask   — fill the PII back in for the human-facing report

The service is callable from:
    - backend/app/api/routes/quotes.py    (REST)
    - backend/app/skills/quote_intelligence/tools.py  (Skill tool)
    - mcp-servers/quote-intel-server/server.py        (MCP tool)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Literal

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.quote import Quote
from app.models.tenant import DEFAULT_TENANT_ID
from app.services.quote.vault import TokenVault


RankingStrategy = Literal["amount_desc", "recency", "amount_weighted_recency"]


@dataclass
class QuoteIntelligenceResult:
    """Structured output of a single pipeline run."""

    masked_records: list[dict[str, Any]] = field(default_factory=list)
    masked_report: str = ""
    final_report: str = ""
    token_count: int = 0
    ranking: str = ""
    fetched_count: int = 0
    selected_count: int = 0


class QuoteIntelligenceService:
    """End-to-end masked LLM pipeline over the quotes table."""

    SYSTEM_PROMPT = (
        "You are a senior sales-intelligence analyst. You will receive a JSON "
        "list of recent sales quotes. Customer-identifying fields have been "
        "replaced with opaque tokens like [CUST_001], [PHONE_002], [EMAIL_003], "
        "[COMPANY_004]. **Treat tokens as opaque IDs and reuse them verbatim** "
        "in your report — do not invent names, do not try to guess identities. "
        "Produce a concise markdown report with these sections:\n"
        "  ## Executive Summary  (3 bullets)\n"
        "  ## Top Opportunities  (table: token, product, amount, status)\n"
        "  ## Risk & Recommendations  (2-4 bullets)\n"
    )

    # ------------------------------------------------------------------
    # 1) fetch
    # ------------------------------------------------------------------
    async def fetch(
        self,
        db: AsyncSession,
        tenant_id: str = DEFAULT_TENANT_ID,
        limit: int = 200,
    ) -> list[Quote]:
        """Pull recent quotes for ``tenant_id`` (newest first)."""
        stmt = (
            select(Quote)
            .where(Quote.tenant_id == tenant_id)
            .order_by(Quote.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = list(result.scalars().all())
        logger.info("QuoteIntel fetch tenant={} count={}", tenant_id, len(rows))
        return rows

    # ------------------------------------------------------------------
    # 2) mask
    # ------------------------------------------------------------------
    def to_dicts(self, quotes: Iterable[Quote]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for q in quotes:
            out.append(
                {
                    "id": q.id,
                    "customer_name": q.customer_name,
                    "customer_phone": q.customer_phone,
                    "customer_email": q.customer_email,
                    "customer_company": q.customer_company,
                    "product_name": q.product_name,
                    "quantity": q.quantity,
                    "amount_cents": q.amount_cents,
                    "currency": q.currency,
                    "region": q.region,
                    "status": q.status,
                    "created_at": q.created_at.isoformat() if q.created_at else None,
                }
            )
        return out

    def mask_records(
        self,
        records: list[dict[str, Any]],
        vault: TokenVault | None = None,
    ) -> tuple[list[dict[str, Any]], TokenVault]:
        v = vault or TokenVault()
        masked = [v.mask_quote_dict(r) for r in records]
        return masked, v

    # ------------------------------------------------------------------
    # 3) algorithmic top-N
    # ------------------------------------------------------------------
    def top_n(
        self,
        records: list[dict[str, Any]],
        n: int,
        ranking: RankingStrategy = "amount_weighted_recency",
    ) -> list[dict[str, Any]]:
        """Score and return the top-N records."""
        if n <= 0 or not records:
            return []

        if ranking == "amount_desc":
            sorted_recs = sorted(records, key=lambda r: r.get("amount_cents", 0), reverse=True)
        elif ranking == "recency":
            sorted_recs = sorted(
                records,
                key=lambda r: r.get("created_at") or "",
                reverse=True,
            )
        else:  # amount_weighted_recency  (default)
            now = datetime.now(timezone.utc)

            def _score(r: dict[str, Any]) -> float:
                amount = float(r.get("amount_cents", 0))
                ts = r.get("created_at")
                age_days = 30.0
                if ts:
                    try:
                        dt = datetime.fromisoformat(ts)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        age_days = max(0.0, (now - dt).total_seconds() / 86400.0)
                    except ValueError:
                        pass
                # Half-life of 30 days; higher amount + fresher == higher score
                decay = math.exp(-age_days / 30.0)
                return amount * decay

            sorted_recs = sorted(records, key=_score, reverse=True)

        return sorted_recs[:n]

    # ------------------------------------------------------------------
    # 4) analyze (LLM)
    # ------------------------------------------------------------------
    async def analyze(self, masked_records: list[dict[str, Any]]) -> str:
        """Send masked records to the BALANCED tier LLM and return its markdown."""
        # Lazy import — keeps this module importable in unit tests / MCP server.
        from app.agents.llm_router import LLMRouter, ModelTier

        router = LLMRouter()
        llm = router.get_model(ModelTier.BALANCED)

        import json

        payload = json.dumps(masked_records, ensure_ascii=False, indent=2)
        messages = [
            SystemMessage(content=self.SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Here are the top {len(masked_records)} masked sales quotes "
                    f"(tokens are opaque IDs, do not de-anonymise):\n\n```json\n"
                    f"{payload}\n```\n\nProduce the report now."
                )
            ),
        ]
        response = await llm.ainvoke(messages)
        text = getattr(response, "content", None) or str(response)
        return text if isinstance(text, str) else str(text)

    # ------------------------------------------------------------------
    # 5) unmask + full pipeline
    # ------------------------------------------------------------------
    async def run(
        self,
        db: AsyncSession,
        tenant_id: str = DEFAULT_TENANT_ID,
        top_n: int = 10,
        ranking: RankingStrategy = "amount_weighted_recency",
        *,
        skip_llm: bool = False,
    ) -> QuoteIntelligenceResult:
        """Run the full pipeline end-to-end.

        ``skip_llm=True`` short-circuits the LLM stage — useful for tests
        and for environments without API keys; the masked payload is still
        produced so callers can inspect masking correctness.
        """
        quotes = await self.fetch(db, tenant_id=tenant_id, limit=max(top_n * 4, 50))
        records = self.to_dicts(quotes)
        masked_all, vault = self.mask_records(records)
        selected = self.top_n(masked_all, top_n, ranking=ranking)

        if skip_llm or not selected:
            masked_report = ""
            final_report = "(LLM stage skipped)"
        else:
            try:
                masked_report = await self.analyze(selected)
            except Exception as exc:  # noqa: BLE001
                logger.warning("QuoteIntel LLM stage failed: {}", exc)
                masked_report = f"(LLM stage failed: {exc})"
            final_report = vault.unmask(masked_report)

        return QuoteIntelligenceResult(
            masked_records=selected,
            masked_report=masked_report,
            final_report=final_report,
            token_count=len(vault),
            ranking=ranking,
            fetched_count=len(records),
            selected_count=len(selected),
        )
