"""Token accountant + budget circuit breaker.

Architecture:
- ``TokenAccountant`` keeps an in-memory daily counter per tenant
  (``defaultdict[(tenant_id, date), Counter]``) so the hot path is lock-free
  and never blocks on the DB. A background task flushes deltas to
  ``tenant_usage_daily`` via UPSERT every ``FLUSH_INTERVAL_SEC`` seconds
  (or eagerly on shutdown).
- ``BudgetGate`` answers ``check(tenant_id)``: returns ``True`` if the
  tenant is still within its ``TenantQuota.max_tokens_per_day`` (cached
  in-process for ``QUOTA_CACHE_TTL_SEC``); raises ``BudgetExceededError``
  otherwise.
- The LangChain callback ``BudgetCallbackHandler`` reads the active tenant
  from ``ContextVar`` and reports usage on ``on_llm_end``.

Singleton accessor ``get_token_accountant()`` is *global* (not per-tenant)
because it tracks usage **across** tenants in a single process.
"""
from __future__ import annotations

import asyncio
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from loguru import logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BudgetExceededError
from app.core.tenant_context import get_current_tenant
from app.models.tenant import DEFAULT_TENANT_ID
from app.services.governance.model_cost_table import lookup_price

# ----------------------------------------------------------------------
# Legacy fallback rates — kept for callers that pass explicit per-1k costs.
# Real per-model pricing comes from ``model_cost_table.lookup_price``.
# ----------------------------------------------------------------------
DEFAULT_PROMPT_COST_PER_1K = 200    # $0.0002 / 1K tokens
DEFAULT_COMPLETION_COST_PER_1K = 600  # $0.0006 / 1K tokens

QUOTA_CACHE_TTL_SEC = 60
FLUSH_INTERVAL_SEC = 30

# Once per (tenant, date) we may emit a warning when usage crosses the
# configured threshold (default 80%). Stored in-process — a process restart
# resets the flag, which is fine: at most one duplicate notification per day.
_warned_today: set[tuple[str, date]] = set()


@dataclass
class _UsageBucket:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    request_count: int = 0
    cost_usd_micro: int = 0
    dirty: bool = False  # set when in-memory > last flushed


@dataclass
class _QuotaCacheEntry:
    limit_tokens: int
    limit_cost_micro: int = 0
    warn_threshold_pct: int = 80
    max_rpm: int = 0
    max_rps: int = 0
    max_tokens_per_user_per_day: int = 0
    max_tokens_per_conversation: int = 0
    cached_at: float = field(default_factory=lambda: datetime.utcnow().timestamp())


class TokenAccountant:
    """Process-singleton that tracks per-tenant token usage."""

    def __init__(self) -> None:
        # (tenant_id, date) -> bucket
        self._buckets: dict[tuple[str, date], _UsageBucket] = defaultdict(_UsageBucket)
        # tenant_id -> quota cache
        self._quota_cache: dict[str, _QuotaCacheEntry] = {}
        # Secondary counters (in-memory only — not persisted; reset on restart).
        # Keyed by (tenant_id, user_id, date) and (tenant_id, conversation_id).
        # Conversation totals are lifetime (not daily) since chats span days.
        self._user_buckets: dict[tuple[str, str, date], int] = defaultdict(int)
        self._conv_buckets: dict[tuple[str, str], int] = defaultdict(int)
        # Optional async warning sink — set by warning_dispatcher on import.
        self._warning_sink: Optional[Any] = None
        self._lock = threading.Lock()

    def set_warning_sink(self, sink: Any) -> None:
        """Register a callable ``sink(tenant_id, snapshot, quota)`` invoked once per day per tenant."""
        self._warning_sink = sink

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------
    def record(
        self,
        tenant_id: str,
        prompt_tokens: int,
        completion_tokens: int,
        *,
        model: Optional[str] = None,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        prompt_cost_per_1k: Optional[int] = None,
        completion_cost_per_1k: Optional[int] = None,
    ) -> None:
        if not tenant_id:
            tenant_id = DEFAULT_TENANT_ID
        if prompt_tokens <= 0 and completion_tokens <= 0:
            return

        # Resolve pricing: explicit override > model lookup > legacy default.
        if prompt_cost_per_1k is None or completion_cost_per_1k is None:
            price = lookup_price(model)
            if prompt_cost_per_1k is None:
                prompt_cost_per_1k = price.prompt_micro_per_1k
            if completion_cost_per_1k is None:
                completion_cost_per_1k = price.completion_micro_per_1k

        cost = (
            (prompt_tokens * prompt_cost_per_1k) + (completion_tokens * completion_cost_per_1k)
        ) // 1000

        key = (tenant_id, date.today())
        total = max(prompt_tokens, 0) + max(completion_tokens, 0)
        with self._lock:
            b = self._buckets[key]
            b.prompt_tokens += max(prompt_tokens, 0)
            b.completion_tokens += max(completion_tokens, 0)
            b.request_count += 1
            b.cost_usd_micro += cost
            b.dirty = True
            if user_id:
                self._user_buckets[(tenant_id, user_id, date.today())] += total
            if conversation_id:
                self._conv_buckets[(tenant_id, conversation_id)] += total

    def get_today_usage(self, tenant_id: str) -> int:
        """Return total_tokens used today (in-memory snapshot)."""
        key = (tenant_id, date.today())
        b = self._buckets.get(key)
        if not b:
            return 0
        return b.prompt_tokens + b.completion_tokens

    def get_today_cost_micro(self, tenant_id: str) -> int:
        key = (tenant_id, date.today())
        b = self._buckets.get(key)
        return b.cost_usd_micro if b else 0

    def get_user_today_usage(self, tenant_id: str, user_id: str) -> int:
        return self._user_buckets.get((tenant_id, user_id, date.today()), 0)

    def get_conversation_usage(self, tenant_id: str, conversation_id: str) -> int:
        return self._conv_buckets.get((tenant_id, conversation_id), 0)

    def get_today_snapshot(self, tenant_id: str) -> dict[str, int]:
        key = (tenant_id, date.today())
        b = self._buckets.get(key)
        if not b:
            return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0,
                    "request_count": 0, "cost_usd_micro": 0}
        return {
            "prompt_tokens": b.prompt_tokens,
            "completion_tokens": b.completion_tokens,
            "total_tokens": b.prompt_tokens + b.completion_tokens,
            "request_count": b.request_count,
            "cost_usd_micro": b.cost_usd_micro,
        }

    # ------------------------------------------------------------------
    # Quota lookup (cached)
    # ------------------------------------------------------------------
    async def get_quota(self, session: AsyncSession, tenant_id: str) -> Optional[int]:
        """Return ``max_tokens_per_day`` for the tenant, or ``None`` if unlimited.

        Kept for backward compat; new code should use :meth:`get_quota_full`.
        """
        entry = await self.get_quota_full(session, tenant_id)
        return entry.limit_tokens if entry else None

    async def get_quota_full(
        self, session: AsyncSession, tenant_id: str
    ) -> Optional[_QuotaCacheEntry]:
        """Return the full quota entry (tokens + cost cap + warn threshold)."""
        now_ts = datetime.utcnow().timestamp()
        cached = self._quota_cache.get(tenant_id)
        if cached and (now_ts - cached.cached_at) < QUOTA_CACHE_TTL_SEC:
            return cached

        from app.models.tenant import TenantQuota
        quota = await session.get(TenantQuota, tenant_id)
        if not quota:
            return None
        entry = _QuotaCacheEntry(
            limit_tokens=quota.max_tokens_per_day,
            limit_cost_micro=getattr(quota, "max_cost_usd_micro_per_day", 0) or 0,
            warn_threshold_pct=getattr(quota, "warn_threshold_pct", 80) or 0,
            max_rpm=getattr(quota, "max_rpm", 0) or 0,
            max_rps=getattr(quota, "max_rps", 0) or 0,
            max_tokens_per_user_per_day=getattr(quota, "max_tokens_per_user_per_day", 0) or 0,
            max_tokens_per_conversation=getattr(quota, "max_tokens_per_conversation", 0) or 0,
            cached_at=now_ts,
        )
        self._quota_cache[tenant_id] = entry
        return entry

    def invalidate_quota_cache(self, tenant_id: Optional[str] = None) -> None:
        if tenant_id is None:
            self._quota_cache.clear()
            _warned_today.clear()
        else:
            self._quota_cache.pop(tenant_id, None)

    # ------------------------------------------------------------------
    # Persistence (UPSERT current dirty buckets)
    # ------------------------------------------------------------------
    async def flush(self, session: AsyncSession) -> int:
        """Persist any dirty buckets via UPSERT. Returns # rows touched."""
        with self._lock:
            dirty_items = [
                (k, _UsageBucket(b.prompt_tokens, b.completion_tokens, b.request_count, b.cost_usd_micro, False))
                for k, b in self._buckets.items()
                if b.dirty
            ]
            for k, _ in dirty_items:
                self._buckets[k].dirty = False

        if not dirty_items:
            return 0

        # Postgres UPSERT — we replace cumulative counters since the in-memory
        # bucket *is* the cumulative truth for the day until process restart.
        # On restart, the bucket is empty and the next record() call will
        # produce a delta — but since we always UPSERT max(in-memory, db),
        # we won't lose data by using GREATEST().
        sql = text(
            """
            INSERT INTO tenant_usage_daily
                (tenant_id, usage_date, prompt_tokens, completion_tokens,
                 total_tokens, request_count, cost_usd_micro, last_updated)
            VALUES (:tid, :ud, :pt, :ct, :tt, :rc, :cu, NOW())
            ON CONFLICT (tenant_id, usage_date) DO UPDATE SET
                prompt_tokens     = GREATEST(tenant_usage_daily.prompt_tokens, EXCLUDED.prompt_tokens),
                completion_tokens = GREATEST(tenant_usage_daily.completion_tokens, EXCLUDED.completion_tokens),
                total_tokens      = GREATEST(tenant_usage_daily.total_tokens, EXCLUDED.total_tokens),
                request_count     = GREATEST(tenant_usage_daily.request_count, EXCLUDED.request_count),
                cost_usd_micro    = GREATEST(tenant_usage_daily.cost_usd_micro, EXCLUDED.cost_usd_micro),
                last_updated      = NOW()
            """
        )
        n = 0
        for (tid, ud), b in dirty_items:
            await session.execute(sql.bindparams(
                tid=tid, ud=ud,
                pt=b.prompt_tokens, ct=b.completion_tokens,
                tt=b.prompt_tokens + b.completion_tokens,
                rc=b.request_count, cu=b.cost_usd_micro,
            ))
            n += 1
        await session.commit()
        return n


# ======================================================================
#  Budget gate
# ======================================================================
class BudgetGate:
    def __init__(self, accountant: TokenAccountant) -> None:
        self.accountant = accountant

    async def check(
        self,
        session: AsyncSession,
        tenant_id: Optional[str] = None,
        *,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
    ) -> None:
        """Raise BudgetExceededError / RateLimitExceeded if any cap trips.

        Layered defenses (cheapest checks first):
        1. Sliding-window rate limit (RPS, then RPM) — in-memory, sub-microsecond.
        2. Hard token cap (tenant-wide).
        3. Hard $-spend cap (tenant-wide).
        4. Per-user daily token cap (in-memory, best-effort).
        5. Per-conversation lifetime token cap (in-memory, best-effort).
        6. Warn-once-per-day at ``warn_threshold_pct``.
        """
        tid = tenant_id or get_current_tenant()
        # 'default' tenant is unbounded by convention so single-user installs
        # are never gated.
        if tid == DEFAULT_TENANT_ID:
            return

        quota = await self.accountant.get_quota_full(session, tid)
        if not quota:
            return

        # ---- 1. Sliding-window rate limit ----
        # RPS first (smaller window) so a sudden burst is flagged precisely.
        if quota.max_rps > 0 or quota.max_rpm > 0:
            from app.services.governance.rate_limiter import (
                get_rate_limiter, RateLimitExceeded,
            )
            limiter = get_rate_limiter()
            try:
                if quota.max_rps > 0:
                    limiter.hit(
                        scope="tenant_rps", key=tid,
                        limit=quota.max_rps, window_sec=1,
                    )
                if quota.max_rpm > 0:
                    limiter.hit(
                        scope="tenant_rpm", key=tid,
                        limit=quota.max_rpm, window_sec=60,
                    )
            except RateLimitExceeded:
                raise

        used_tokens = self.accountant.get_today_usage(tid)
        used_cost = self.accountant.get_today_cost_micro(tid)

        token_limit = quota.limit_tokens or 0
        cost_limit = quota.limit_cost_micro or 0

        # ---- 2. Tenant token cap ----
        if token_limit > 0 and used_tokens >= token_limit:
            logger.warning(
                "🛑 Budget gate tripped (tokens): tenant={} used={} limit={}",
                tid, used_tokens, token_limit,
            )
            raise BudgetExceededError(tenant_id=tid, used=used_tokens, limit=token_limit)

        # ---- 3. Tenant $-spend cap ----
        if cost_limit > 0 and used_cost >= cost_limit:
            logger.warning(
                "🛑 Budget gate tripped ($): tenant={} used_micro={} limit_micro={}",
                tid, used_cost, cost_limit,
            )
            raise BudgetExceededError(tenant_id=tid, used=used_cost, limit=cost_limit)

        # ---- 4. Per-user daily cap ----
        if user_id is None:
            try:
                from app.core.tenant_context import get_current_user_id
                user_id = get_current_user_id()
            except Exception:  # noqa: BLE001
                user_id = None
        if user_id and quota.max_tokens_per_user_per_day > 0:
            user_used = self.accountant.get_user_today_usage(tid, user_id)
            if user_used >= quota.max_tokens_per_user_per_day:
                logger.warning(
                    "🛑 Per-user budget tripped: tenant={} user={} used={} limit={}",
                    tid, user_id, user_used, quota.max_tokens_per_user_per_day,
                )
                raise BudgetExceededError(
                    tenant_id=f"{tid}/user:{user_id}",
                    used=user_used, limit=quota.max_tokens_per_user_per_day,
                )

        # ---- 5. Per-conversation lifetime cap ----
        if conversation_id is None:
            try:
                from app.core.tenant_context import get_current_conversation_id
                conversation_id = get_current_conversation_id()
            except Exception:  # noqa: BLE001
                conversation_id = None
        if conversation_id and quota.max_tokens_per_conversation > 0:
            conv_used = self.accountant.get_conversation_usage(tid, conversation_id)
            if conv_used >= quota.max_tokens_per_conversation:
                logger.warning(
                    "🛑 Per-conversation budget tripped: tenant={} conv={} used={} limit={}",
                    tid, conversation_id, conv_used, quota.max_tokens_per_conversation,
                )
                raise BudgetExceededError(
                    tenant_id=f"{tid}/conv:{conversation_id}",
                    used=conv_used, limit=quota.max_tokens_per_conversation,
                )

        # ---- 6. Warn-once-per-day ----
        warn_pct = quota.warn_threshold_pct
        if warn_pct and warn_pct > 0:
            today = date.today()
            warn_key = (tid, today)
            tripped = False
            if token_limit > 0 and (used_tokens * 100) >= (token_limit * warn_pct):
                tripped = True
            if cost_limit > 0 and (used_cost * 100) >= (cost_limit * warn_pct):
                tripped = True
            if tripped and warn_key not in _warned_today:
                _warned_today.add(warn_key)
                await self._fire_warning(session, tid, used_tokens, used_cost, quota)

    async def _fire_warning(
        self,
        session: AsyncSession,
        tenant_id: str,
        used_tokens: int,
        used_cost_micro: int,
        quota: "_QuotaCacheEntry",
    ) -> None:
        """Emit warning to logs + audit log + optional sink."""
        token_pct = (used_tokens * 100 // quota.limit_tokens) if quota.limit_tokens else 0
        cost_pct = (used_cost_micro * 100 // quota.limit_cost_micro) if quota.limit_cost_micro else 0
        logger.warning(
            "⚠️  Budget warning: tenant={} tokens={}% ({}/{}) cost={}% (${:.4f}/${:.4f})",
            tenant_id,
            token_pct, used_tokens, quota.limit_tokens,
            cost_pct, used_cost_micro / 1_000_000, quota.limit_cost_micro / 1_000_000,
        )

        # Best-effort audit log entry
        try:
            from app.models.security import AuditLog
            import json as _json
            session.add(AuditLog(
                tenant_id=tenant_id,
                user_id=None,
                action="budget_warning",
                resource_type="tenant_quota",
                resource_id=tenant_id,
                details=_json.dumps({
                    "used_tokens": used_tokens,
                    "limit_tokens": quota.limit_tokens,
                    "used_cost_usd_micro": used_cost_micro,
                    "limit_cost_usd_micro": quota.limit_cost_micro,
                    "threshold_pct": quota.warn_threshold_pct,
                }),
            ))
            await session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.debug("Audit log skipped: {}", exc)

        # Optional async sink (e.g. webhook dispatcher)
        sink = self.accountant._warning_sink
        if sink:
            try:
                snapshot = self.accountant.get_today_snapshot(tenant_id)
                result = sink(tenant_id, snapshot, quota)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as exc:  # noqa: BLE001
                logger.warning("Warning sink failed: {}", exc)


# ======================================================================
#  Singletons
# ======================================================================
_accountant: Optional[TokenAccountant] = None
_gate: Optional[BudgetGate] = None
_singleton_lock = threading.Lock()


def get_token_accountant() -> TokenAccountant:
    global _accountant
    if _accountant is None:
        with _singleton_lock:
            if _accountant is None:
                _accountant = TokenAccountant()
                logger.info("💰 TokenAccountant initialized")
    return _accountant


def get_budget_gate() -> BudgetGate:
    global _gate
    if _gate is None:
        with _singleton_lock:
            if _gate is None:
                _gate = BudgetGate(get_token_accountant())
    return _gate


# ======================================================================
#  Background flusher
# ======================================================================
_flush_task: Optional[asyncio.Task] = None


async def _flush_loop() -> None:
    from app.core.database import get_db_session  # local to avoid import cycle
    accountant = get_token_accountant()
    while True:
        try:
            await asyncio.sleep(FLUSH_INTERVAL_SEC)
            async for session in get_db_session():
                n = await accountant.flush(session)
                if n:
                    logger.debug("💰 Flushed {} tenant_usage_daily rows", n)
                break
        except asyncio.CancelledError:
            break
        except Exception as exc:  # noqa: BLE001
            logger.warning("Token accountant flush failed: {}", exc)


def start_background_flusher(loop: Optional[asyncio.AbstractEventLoop] = None) -> None:
    """Spawn the periodic flush task. Idempotent."""
    global _flush_task
    if _flush_task and not _flush_task.done():
        return
    loop = loop or asyncio.get_event_loop()
    _flush_task = loop.create_task(_flush_loop())
    logger.info("💰 Token accountant flush loop started (every {}s)", FLUSH_INTERVAL_SEC)


async def stop_background_flusher() -> None:
    global _flush_task
    if _flush_task and not _flush_task.done():
        _flush_task.cancel()
        try:
            await _flush_task
        except asyncio.CancelledError:
            pass
        _flush_task = None


# ======================================================================
#  LangChain callback handler
# ======================================================================
def _extract_token_usage(response: Any) -> tuple[int, int]:
    """Best-effort extraction of token counts from a LangChain LLMResult."""
    try:
        usage = response.llm_output.get("token_usage") if response.llm_output else None
        if usage:
            return int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
    except Exception:  # noqa: BLE001
        pass

    # Try generation-level usage_metadata (LangChain >= 0.2)
    try:
        gens = getattr(response, "generations", None) or []
        for chunk in gens:
            for g in chunk:
                msg = getattr(g, "message", None)
                meta = getattr(msg, "usage_metadata", None) if msg else None
                if meta:
                    return int(meta.get("input_tokens", 0)), int(meta.get("output_tokens", 0))
    except Exception:  # noqa: BLE001
        pass
    return 0, 0


def _extract_model_name(response: Any, serialized: Any, kwargs: dict) -> Optional[str]:
    """Find the model name from any of the LangChain hooks' arguments."""
    # Preferred — kwargs from on_llm_start has invocation_params with model
    try:
        inv = kwargs.get("invocation_params") if isinstance(kwargs, dict) else None
        if isinstance(inv, dict):
            for k in ("model", "model_name", "_type"):
                if inv.get(k):
                    return str(inv[k])
    except Exception:  # noqa: BLE001
        pass

    try:
        if response is not None:
            llm_output = getattr(response, "llm_output", None) or {}
            for k in ("model_name", "model"):
                if llm_output.get(k):
                    return str(llm_output[k])
    except Exception:  # noqa: BLE001
        pass

    try:
        if isinstance(serialized, dict):
            kw = serialized.get("kwargs") or {}
            for k in ("model", "model_name"):
                if kw.get(k):
                    return str(kw[k])
    except Exception:  # noqa: BLE001
        pass

    return None


try:
    from langchain_core.callbacks import BaseCallbackHandler  # type: ignore
except Exception:  # pragma: no cover - langchain optional in some test envs
    BaseCallbackHandler = object  # type: ignore


class BudgetCallbackHandler(BaseCallbackHandler):  # type: ignore[misc]
    """Records token usage + cost to the accountant after each LLM call.

    Captures the model name on ``on_llm_start`` (so we have it available even
    when the response payload omits it) and uses it on ``on_llm_end`` to apply
    the correct per-model price from ``model_cost_table``.
    """

    def __init__(self) -> None:  # type: ignore[no-untyped-def]
        super().__init__()
        # Per-run model name keyed by LangChain run_id
        self._model_by_run: dict[str, str] = {}

    def on_llm_start(  # type: ignore[override]
        self, serialized: Any, prompts: Any, *, run_id: Any = None, **kwargs: Any
    ) -> None:
        try:
            model = _extract_model_name(None, serialized, kwargs)
            if model and run_id is not None:
                self._model_by_run[str(run_id)] = model
        except Exception as exc:  # noqa: BLE001
            logger.debug("BudgetCallbackHandler.on_llm_start ignored: {}", exc)

    def on_chat_model_start(  # type: ignore[override]
        self, serialized: Any, messages: Any, *, run_id: Any = None, **kwargs: Any
    ) -> None:
        # Same logic — chat models route through this hook in newer LangChain
        self.on_llm_start(serialized, messages, run_id=run_id, **kwargs)

    def on_llm_end(self, response: Any, *, run_id: Any = None, **kwargs: Any) -> None:  # type: ignore[override]
        try:
            prompt, completion = _extract_token_usage(response)
            if not (prompt or completion):
                return
            tenant_id = get_current_tenant()
            # Pull user / conversation from ContextVar so per-user / per-conv
            # secondary quotas can be enforced. Best-effort — None means "no scope".
            user_id = None
            conv_id = None
            try:
                from app.core.tenant_context import (
                    get_current_user_id, get_current_conversation_id,
                )
                user_id = get_current_user_id()
                conv_id = get_current_conversation_id()
            except Exception:  # noqa: BLE001
                pass
            model = None
            if run_id is not None:
                model = self._model_by_run.pop(str(run_id), None)
            if not model:
                model = _extract_model_name(response, None, kwargs)
            get_token_accountant().record(
                tenant_id, prompt, completion,
                model=model, user_id=user_id, conversation_id=conv_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("BudgetCallbackHandler ignored error: {}", exc)

    def on_llm_error(self, error: Any, *, run_id: Any = None, **kwargs: Any) -> None:  # type: ignore[override]
        if run_id is not None:
            self._model_by_run.pop(str(run_id), None)
