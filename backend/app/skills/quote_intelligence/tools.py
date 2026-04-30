"""Tools for the quote-intelligence skill.

Each tool wraps :class:`app.services.quote.QuoteIntelligenceService`
so the same pipeline is reachable from:
    - The skill registry (this module's ``get_tools``)
    - REST   (app/api/routes/quotes.py)
    - MCP    (mcp-servers/quote-intel-server/server.py)
"""
from __future__ import annotations

from typing import Any

from langchain_core.tools import tool

from app.core.database import async_session_factory
from app.core.tenant_context import get_current_tenant
from app.models.tenant import DEFAULT_TENANT_ID
from app.services.quote import QuoteIntelligenceService


def _tenant() -> str:
    return get_current_tenant() or DEFAULT_TENANT_ID


@tool
async def quote_intel_run(
    top_n: int = 5,
    ranking: str = "amount_weighted_recency",
) -> dict[str, Any]:
    """Run the full quote-intelligence pipeline for the active tenant.

    Args:
        top_n: How many top quotes to send to the LLM (1-50).
        ranking: ``amount_weighted_recency`` | ``amount_desc`` | ``recency``.

    Returns a dict with ``masked_records``, ``masked_report``,
    ``final_report`` (PII-restored), ``masked_token_count``, ``ranking``,
    ``fetched_count``, ``selected_count``.
    """
    svc = QuoteIntelligenceService()
    async with async_session_factory() as db:
        result = await svc.run(
            db,
            tenant_id=_tenant(),
            top_n=max(1, min(int(top_n), 50)),
            ranking=ranking,  # type: ignore[arg-type]
        )
    return {
        "fetched_count": result.fetched_count,
        "selected_count": result.selected_count,
        "ranking": result.ranking,
        "masked_token_count": result.token_count,
        "masked_records": result.masked_records,
        "masked_report": result.masked_report,
        "final_report": result.final_report,
    }


@tool
async def quote_intel_fetch_masked(
    top_n: int = 10,
    ranking: str = "amount_weighted_recency",
) -> dict[str, Any]:
    """Fetch + mask + top-N only — does **not** invoke the LLM.

    Useful when an outer agent wants to inspect the masked payload before
    deciding how / whether to call an LLM.
    """
    svc = QuoteIntelligenceService()
    async with async_session_factory() as db:
        result = await svc.run(
            db,
            tenant_id=_tenant(),
            top_n=max(1, min(int(top_n), 50)),
            ranking=ranking,  # type: ignore[arg-type]
            skip_llm=True,
        )
    return {
        "fetched_count": result.fetched_count,
        "selected_count": result.selected_count,
        "ranking": result.ranking,
        "masked_token_count": result.token_count,
        "masked_records": result.masked_records,
    }


def get_tools() -> list:
    return [quote_intel_run, quote_intel_fetch_masked]
