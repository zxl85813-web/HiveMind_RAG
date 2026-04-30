"""Quote (sales quotation) model — demo for end-to-end quote-intelligence agent.

Each row carries a few PII-bearing fields (customer name / phone / email)
intentionally so the QuoteIntelligenceService can demonstrate reversible
masking before LLM analysis and re-fill of the values in the final report.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from app.models.tenant import DEFAULT_TENANT_ID


class Quote(SQLModel, table=True):
    """A sales quote / proposal record."""

    __tablename__ = "quotes"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    tenant_id: str = Field(
        default=DEFAULT_TENANT_ID,
        foreign_key="tenants.id",
        index=True,
        max_length=64,
    )

    # ---- PII (will be masked before LLM call) ----
    customer_name: str = Field(max_length=128)
    customer_phone: str = Field(max_length=32)
    customer_email: str = Field(max_length=128)
    customer_company: Optional[str] = Field(default=None, max_length=128)

    # ---- Non-PII (sent to LLM as-is) ----
    product_name: str = Field(max_length=128)
    quantity: int = Field(default=1)
    unit_price_cents: int = Field(default=0)
    amount_cents: int = Field(default=0)  # quantity * unit_price - discount
    currency: str = Field(default="USD", max_length=8)
    region: Optional[str] = Field(default=None, max_length=64)
    status: str = Field(default="draft", max_length=16)  # draft|sent|won|lost

    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
