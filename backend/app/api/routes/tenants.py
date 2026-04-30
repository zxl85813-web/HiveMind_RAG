"""Tenant admin API — list/create tenants, manage quotas.

All endpoints require admin role. The 'default' tenant is reserved.
"""
from datetime import datetime
from typing import Optional, Sequence

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_db, get_current_user, require_admin
from app.models.chat import User
from app.models.tenant import DEFAULT_TENANT_ID, Tenant, TenantQuota

router = APIRouter()


class TenantCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=128)
    plan: str = Field(default="free", max_length=32)


class TenantQuotaUpdate(BaseModel):
    max_users: Optional[int] = None
    max_conversations_per_day: Optional[int] = None
    max_subagents_concurrent: Optional[int] = None
    max_tokens_per_day: Optional[int] = None
    max_kb_count: Optional[int] = None
    max_cost_usd_micro_per_day: Optional[int] = None
    warn_threshold_pct: Optional[int] = None
    max_rpm: Optional[int] = None
    max_rps: Optional[int] = None
    max_tokens_per_user_per_day: Optional[int] = None
    max_tokens_per_conversation: Optional[int] = None


class TenantOut(BaseModel):
    id: str
    slug: str
    name: str
    plan: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[TenantOut])
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Sequence[Tenant]:
    """List all tenants. Admin only."""
    res = await db.execute(select(Tenant).order_by(Tenant.created_at))
    return res.scalars().all()


@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    payload: TenantCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Tenant:
    """Create a new tenant + default quota row."""
    if payload.slug == DEFAULT_TENANT_ID:
        raise HTTPException(status_code=400, detail="'default' is reserved")

    existing = await db.execute(select(Tenant).where(Tenant.slug == payload.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Slug '{payload.slug}' already exists")

    tenant = Tenant(slug=payload.slug, name=payload.name, plan=payload.plan)
    db.add(tenant)
    await db.flush()  # populate tenant.id
    db.add(TenantQuota(tenant_id=tenant.id))
    await db.commit()
    await db.refresh(tenant)
    return tenant


@router.get("/{tenant_id}", response_model=TenantOut)
async def get_tenant(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.get("/{tenant_id}/quota")
async def get_quota(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    quota = await db.get(TenantQuota, tenant_id)
    if not quota:
        raise HTTPException(status_code=404, detail="Quota not found")
    return quota


@router.put("/{tenant_id}/quota")
async def update_quota(
    tenant_id: str,
    payload: TenantQuotaUpdate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    quota = await db.get(TenantQuota, tenant_id)
    if not quota:
        # Auto-create if the row was missing for some reason.
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        quota = TenantQuota(tenant_id=tenant_id)
        db.add(quota)

    updates = payload.model_dump(exclude_none=True)
    for k, v in updates.items():
        if v is not None and v < 0:
            raise HTTPException(status_code=400, detail=f"{k} must be >= 0")
        setattr(quota, k, v)
    quota.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(quota)

    # Drop the in-memory cache so the new limit is honored on the next call.
    try:
        from app.services.governance.token_accountant import get_token_accountant
        get_token_accountant().invalidate_quota_cache(tenant_id)
    except Exception:
        pass

    return quota


@router.get("/_me/current", response_model=TenantOut)
async def current_tenant(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Tenant:
    """Return the caller's tenant — handy for the frontend to render the badge."""
    tid = getattr(user, "tenant_id", None) or DEFAULT_TENANT_ID
    tenant = await db.get(Tenant, tid)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


# ----------------------------------------------------------------------
# Usage / budget endpoints (P0 #3)
# ----------------------------------------------------------------------
class UsageSnapshot(BaseModel):
    tenant_id: str
    usage_date: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 0
    cost_usd_micro: int = 0
    quota_tokens_per_day: Optional[int] = None
    quota_used_pct: Optional[float] = None
    quota_cost_usd_micro_per_day: Optional[int] = None
    quota_cost_used_pct: Optional[float] = None
    warn_threshold_pct: Optional[int] = None
    # Rate limit + secondary quotas (echoed back so the dashboard can show them)
    quota_max_rpm: Optional[int] = None
    quota_max_rps: Optional[int] = None
    quota_max_tokens_per_user_per_day: Optional[int] = None
    quota_max_tokens_per_conversation: Optional[int] = None


async def _build_snapshot(db: AsyncSession, tenant_id: str) -> UsageSnapshot:
    from datetime import date as _date
    from app.services.governance.token_accountant import get_token_accountant
    from app.models.usage import TenantUsageDaily

    accountant = get_token_accountant()
    snap = accountant.get_today_snapshot(tenant_id)

    # Merge with persisted row (in case process just restarted)
    row = await db.get(TenantUsageDaily, (tenant_id, _date.today()))
    if row:
        snap["prompt_tokens"] = max(snap["prompt_tokens"], row.prompt_tokens)
        snap["completion_tokens"] = max(snap["completion_tokens"], row.completion_tokens)
        snap["total_tokens"] = max(snap["total_tokens"], row.total_tokens)
        snap["request_count"] = max(snap["request_count"], row.request_count)
        snap["cost_usd_micro"] = max(snap["cost_usd_micro"], row.cost_usd_micro)

    quota = await accountant.get_quota_full(db, tenant_id)
    token_pct = None
    cost_pct = None
    if quota:
        if quota.limit_tokens > 0:
            token_pct = round(100.0 * snap["total_tokens"] / quota.limit_tokens, 2)
        if quota.limit_cost_micro > 0:
            cost_pct = round(100.0 * snap["cost_usd_micro"] / quota.limit_cost_micro, 2)

    return UsageSnapshot(
        tenant_id=tenant_id,
        usage_date=_date.today().isoformat(),
        prompt_tokens=snap["prompt_tokens"],
        completion_tokens=snap["completion_tokens"],
        total_tokens=snap["total_tokens"],
        request_count=snap["request_count"],
        cost_usd_micro=snap["cost_usd_micro"],
        quota_tokens_per_day=quota.limit_tokens if quota else None,
        quota_used_pct=token_pct,
        quota_cost_usd_micro_per_day=quota.limit_cost_micro if quota else None,
        quota_cost_used_pct=cost_pct,
        warn_threshold_pct=quota.warn_threshold_pct if quota else None,
        quota_max_rpm=quota.max_rpm if quota else None,
        quota_max_rps=quota.max_rps if quota else None,
        quota_max_tokens_per_user_per_day=quota.max_tokens_per_user_per_day if quota else None,
        quota_max_tokens_per_conversation=quota.max_tokens_per_conversation if quota else None,
    )


@router.get("/_me/usage", response_model=UsageSnapshot)
async def my_usage(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UsageSnapshot:
    """Today's usage for the caller's tenant."""
    tid = getattr(user, "tenant_id", None) or DEFAULT_TENANT_ID
    return await _build_snapshot(db, tid)


@router.get("/{tenant_id}/usage", response_model=UsageSnapshot)
async def tenant_usage(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UsageSnapshot:
    """Today's usage for any tenant (admin)."""
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return await _build_snapshot(db, tenant_id)


@router.post("/{tenant_id}/usage/flush", status_code=status.HTTP_202_ACCEPTED)
async def flush_usage(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Force-flush in-memory accountant counters to the DB (admin)."""
    from app.services.governance.token_accountant import get_token_accountant
    n = await get_token_accountant().flush(db)
    return {"flushed_rows": n}


# ----------------------------------------------------------------------
# Usage history (for the frontend dashboard)
# ----------------------------------------------------------------------
class UsageHistoryPoint(BaseModel):
    date: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    request_count: int
    cost_usd_micro: int


class UsageHistory(BaseModel):
    tenant_id: str
    days: int
    points: list[UsageHistoryPoint]


async def _build_history(db: AsyncSession, tenant_id: str, days: int) -> UsageHistory:
    """Return last N days of usage (oldest first). Missing days are zero-filled."""
    from datetime import date as _date, timedelta
    from app.models.usage import TenantUsageDaily

    # Always flush in-memory first so today's row is up to date.
    from app.services.governance.token_accountant import get_token_accountant
    try:
        await get_token_accountant().flush(db)
    except Exception:  # noqa: BLE001
        pass

    today = _date.today()
    start = today - timedelta(days=days - 1)

    res = await db.execute(
        select(TenantUsageDaily).where(
            TenantUsageDaily.tenant_id == tenant_id,
            TenantUsageDaily.usage_date >= start,
            TenantUsageDaily.usage_date <= today,
        )
    )
    rows = {r.usage_date: r for r in res.scalars().all()}

    points: list[UsageHistoryPoint] = []
    for i in range(days):
        d = start + timedelta(days=i)
        r = rows.get(d)
        points.append(UsageHistoryPoint(
            date=d.isoformat(),
            prompt_tokens=r.prompt_tokens if r else 0,
            completion_tokens=r.completion_tokens if r else 0,
            total_tokens=r.total_tokens if r else 0,
            request_count=r.request_count if r else 0,
            cost_usd_micro=r.cost_usd_micro if r else 0,
        ))
    return UsageHistory(tenant_id=tenant_id, days=days, points=points)


@router.get("/_me/usage/history", response_model=UsageHistory)
async def my_usage_history(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UsageHistory:
    """Last `days` of daily usage for the caller's tenant (default 30)."""
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be 1..365")
    tid = getattr(user, "tenant_id", None) or DEFAULT_TENANT_ID
    return await _build_history(db, tid, days)


@router.get("/{tenant_id}/usage/history", response_model=UsageHistory)
async def tenant_usage_history(
    tenant_id: str,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UsageHistory:
    """Last `days` of daily usage for any tenant (admin)."""
    if days < 1 or days > 365:
        raise HTTPException(status_code=400, detail="days must be 1..365")
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return await _build_history(db, tenant_id, days)


# ============================================================================
# Per-tenant secrets (encrypted LLM API keys, webhook URLs, ...)
# ============================================================================

class SecretPut(BaseModel):
    """Write-only payload — value is encrypted at rest and never returned."""
    value: str = Field(min_length=1, max_length=4096)


class SecretRefOut(BaseModel):
    key_name: str
    hint: str
    updated_at: str


def _validate_secret_key(key_name: str) -> None:
    # Whitelist scheme to prevent arbitrary key injection.
    # Format: <namespace>.<provider>.<field>  e.g. llm.openai.api_key
    import re
    if not re.fullmatch(r"[a-z][a-z0-9_]*(\.[a-z0-9_]+){1,3}", key_name):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="key_name must match <namespace>.<provider>[.<field>] (lowercase, dot-separated)",
        )


async def _ensure_tenant_exists(db: AsyncSession, tenant_id: str) -> None:
    if tenant_id == DEFAULT_TENANT_ID:
        return
    t = await db.get(Tenant, tenant_id)
    if t is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")


@router.get("/{tenant_id}/secrets", response_model=list[SecretRefOut])
async def list_secrets(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """List secret key names + masked hints. Plaintext is never returned."""
    from app.services.governance.secret_manager import get_backend
    await _ensure_tenant_exists(db, tenant_id)
    refs = await get_backend().list_for_tenant(db, tenant_id)
    return [
        SecretRefOut(key_name=r.key_name, hint=r.hint, updated_at=r.updated_at_iso)
        for r in refs
    ]


@router.put("/{tenant_id}/secrets/{key_name}", response_model=SecretRefOut)
async def put_secret(
    tenant_id: str,
    key_name: str,
    payload: SecretPut,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Create or rotate an encrypted secret. Value is write-only."""
    from app.services.governance.secret_manager import get_backend

    _validate_secret_key(key_name)
    await _ensure_tenant_exists(db, tenant_id)
    ref = await get_backend().put(db, tenant_id, key_name, payload.value)

    # Drop any cached LLM instance for this tenant so the new key takes effect immediately.
    try:
        from app.agents.llm_router import LLMRouter
        # The router lives as a singleton on app.state; best-effort lookup.
        from app.main import app as _app  # noqa: WPS433
        router_inst = getattr(_app.state, "llm_router", None)
        if router_inst is not None:
            router_inst.invalidate_tenant(tenant_id)
    except Exception:  # noqa: BLE001
        pass

    return SecretRefOut(key_name=ref.key_name, hint=ref.hint, updated_at=ref.updated_at_iso)


@router.delete("/{tenant_id}/secrets/{key_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(
    tenant_id: str,
    key_name: str,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Permanently delete a tenant secret."""
    from app.services.governance.secret_manager import get_backend

    _validate_secret_key(key_name)
    await _ensure_tenant_exists(db, tenant_id)
    deleted = await get_backend().delete(db, tenant_id, key_name)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="secret not found")

    try:
        from app.main import app as _app  # noqa: WPS433
        router_inst = getattr(_app.state, "llm_router", None)
        if router_inst is not None:
            router_inst.invalidate_tenant(tenant_id)
    except Exception:  # noqa: BLE001
        pass
    return None
