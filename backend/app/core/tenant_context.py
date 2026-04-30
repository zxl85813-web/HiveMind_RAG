"""
Tenant context — process-wide source of truth for the current tenant.

Why ContextVar?
---------------
We want "what tenant am I serving?" to be answerable from anywhere
(services, singletons, background tasks) **without threading a
``tenant_id`` argument through every layer**. ContextVar gives us a
per-async-task slot that:

- Inherits across ``asyncio.create_task`` boundaries (so subagents
  fork-spawned with ``asyncio.gather`` automatically inherit the
  parent's tenant).
- Is **thread-safe and async-safe** by construction (unlike a global).
- Is cheap to read (single attribute access).

Set the tenant once at the request boundary (FastAPI middleware /
dependency, WebSocket handshake, Celery task entry) via
``set_current_tenant``. Read it via ``get_current_tenant`` — the
default fallback is the reserved single-tenant id so pre-multi-tenant
code paths still work.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Iterator, Optional

from app.models.tenant import DEFAULT_TENANT_ID

_current_tenant: ContextVar[str] = ContextVar(
    "current_tenant", default=DEFAULT_TENANT_ID
)
# Optional sub-tenant identifiers — used by per-user / per-conversation quotas
# and rate limiting. Default to None (anonymous / unscoped).
_current_user: ContextVar[Optional[str]] = ContextVar("current_user", default=None)
_current_conversation: ContextVar[Optional[str]] = ContextVar(
    "current_conversation", default=None
)


def get_current_tenant() -> str:
    """Return the tenant id active for the current task. Always non-empty."""
    return _current_tenant.get() or DEFAULT_TENANT_ID


def get_current_user_id() -> Optional[str]:
    return _current_user.get()


def get_current_conversation_id() -> Optional[str]:
    return _current_conversation.get()


def set_current_tenant(tenant_id: Optional[str]) -> Token:
    """Set the active tenant. Returns a token to restore via ``reset_tenant``."""
    return _current_tenant.set(tenant_id or DEFAULT_TENANT_ID)


def set_current_user(user_id: Optional[str]) -> Token:
    return _current_user.set(user_id)


def set_current_conversation(conversation_id: Optional[str]) -> Token:
    return _current_conversation.set(conversation_id)


def reset_tenant(token: Token) -> None:
    _current_tenant.reset(token)


@contextmanager
def tenant_scope(
    tenant_id: Optional[str],
    *,
    user_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> Iterator[str]:
    """``with tenant_scope("acme", user_id="u1"): ...`` — sets and auto-restores."""
    t_token = set_current_tenant(tenant_id)
    u_token = _current_user.set(user_id) if user_id is not None else None
    c_token = _current_conversation.set(conversation_id) if conversation_id is not None else None
    try:
        yield get_current_tenant()
    finally:
        if c_token is not None:
            _current_conversation.reset(c_token)
        if u_token is not None:
            _current_user.reset(u_token)
        reset_tenant(t_token)
