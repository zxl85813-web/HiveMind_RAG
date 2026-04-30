"""
Tenant / Organization model — the unit of multi-tenancy.

A Tenant owns:
- users (a User belongs to exactly one Tenant)
- knowledge bases, conversations, audit events, quotas
- secrets / API keys (per-tenant LLM credentials, future)

The default-tenant ("default") is auto-seeded so single-tenant deployments
keep working without any migration noise.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


# Reserved id for single-tenant / pre-multi-tenant data backfilled by the
# migration. Code that defaults a missing tenant should use this value.
DEFAULT_TENANT_ID = "default"


class Tenant(SQLModel, table=True):
    __tablename__ = "tenants"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    slug: str = Field(unique=True, index=True, max_length=64)
    name: str = Field(max_length=128)
    plan: str = Field(default="free", max_length=32)  # free | pro | enterprise
    is_active: bool = Field(default=True)
    settings_json: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TenantQuota(SQLModel, table=True):
    """Per-tenant limits — enforced by middleware/services."""

    __tablename__ = "tenant_quotas"

    tenant_id: str = Field(foreign_key="tenants.id", primary_key=True)
    max_users: int = Field(default=10)
    max_conversations_per_day: int = Field(default=1000)
    max_subagents_concurrent: int = Field(default=4)
    max_tokens_per_day: int = Field(default=1_000_000)
    max_kb_count: int = Field(default=10)
    # Hard $-spend ceiling per UTC day. 0 means unlimited (only token cap applies).
    # Stored in USD micro-cents (1 USD = 1_000_000) to match accountant accounting.
    max_cost_usd_micro_per_day: int = Field(default=0)
    # Notify webhooks/audit when usage crosses this fraction (0..100). 0 disables.
    warn_threshold_pct: int = Field(default=80)
    # --- Sliding-window rate limit (0 = disabled) ---
    max_rpm: int = Field(default=0)  # requests per 60s, tenant-wide
    max_rps: int = Field(default=0)  # requests per 1s, tenant-wide (burst guard)
    # --- Secondary quotas (defense-in-depth: one user can't drain the tenant) ---
    max_tokens_per_user_per_day: int = Field(default=0)  # 0 = unlimited
    max_tokens_per_conversation: int = Field(default=0)  # 0 = unlimited (lifetime, not daily)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class TenantSecret(SQLModel, table=True):
    """Encrypted per-tenant secrets (LLM API keys, webhook URLs, ...).

    Plaintext is never stored. ``encrypted_value`` is Fernet ciphertext;
    ``hint`` is a masked preview ("sk-...AbCd") safe to return through admin APIs.
    Composite primary key on (tenant_id, key_name).
    """

    __tablename__ = "tenant_secrets"

    tenant_id: str = Field(foreign_key="tenants.id", primary_key=True, max_length=64)
    key_name: str = Field(primary_key=True, max_length=128)
    encrypted_value: str = Field(max_length=4096)
    hint: str = Field(default="***", max_length=64)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
