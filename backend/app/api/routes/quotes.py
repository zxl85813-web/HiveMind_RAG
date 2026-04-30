"""Quote-Intelligence demo endpoints.

Exposes the full mask -> top-N -> LLM -> unmask pipeline as a single
one-shot REST call so the example agent can be triggered from the UI or
from external automation.
"""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.chat import User
from app.models.tenant import DEFAULT_TENANT_ID
from app.services.quote import QuoteIntelligenceService


router = APIRouter()


class QuoteIntelRunRequest(BaseModel):
    top_n: int = Field(default=5, ge=1, le=50)
    ranking: Literal["amount_desc", "recency", "amount_weighted_recency"] = (
        "amount_weighted_recency"
    )
    skip_llm: bool = False


class QuoteIntelRunResponse(BaseModel):
    fetched_count: int
    selected_count: int
    ranking: str
    masked_token_count: int
    masked_records: list[dict]
    masked_report: str
    final_report: str


@router.post("/intelligence/run", response_model=QuoteIntelRunResponse)
async def run_quote_intelligence(
    body: QuoteIntelRunRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> QuoteIntelRunResponse:
    """Run the demo quote-intelligence pipeline for the caller's tenant."""
    tenant_id = getattr(user, "tenant_id", None) or DEFAULT_TENANT_ID
    svc = QuoteIntelligenceService()
    result = await svc.run(
        db,
        tenant_id=tenant_id,
        top_n=body.top_n,
        ranking=body.ranking,
        skip_llm=body.skip_llm,
    )
    return QuoteIntelRunResponse(
        fetched_count=result.fetched_count,
        selected_count=result.selected_count,
        ranking=result.ranking,
        masked_token_count=result.token_count,
        masked_records=result.masked_records,
        masked_report=result.masked_report,
        final_report=result.final_report,
    )
