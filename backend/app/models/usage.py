"""Per-tenant usage tracking — daily roll-up of LLM token spend.

Used by ``TokenAccountant`` to enforce ``TenantQuota.max_tokens_per_day``
via the budget gate and by admin/usage dashboards.
"""
from datetime import date, datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class TenantUsageDaily(SQLModel, table=True):
    """One row per tenant per UTC date.

    Cumulative counters — updated atomically via UPSERT on every LLM call.
    """
    __tablename__ = "tenant_usage_daily"

    tenant_id: str = Field(foreign_key="tenants.id", primary_key=True, index=True)
    usage_date: date = Field(primary_key=True, index=True)

    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    request_count: int = Field(default=0)

    # Cost is tracked in USD millicents (1/1000 of a cent) to keep
    # everything in integers — avoids float drift over millions of calls.
    cost_usd_micro: int = Field(default=0)

    # Optional break-down of per-model usage as JSON; left simple for now.
    last_updated: datetime = Field(default_factory=datetime.utcnow)
