"""
Per-tenant secret manager — encrypted storage of LLM API keys, webhooks, etc.

Design
------
A small backend abstraction so we can swap Fernet (default, zero-ops) for
HashiCorp Vault or AWS KMS later without touching call sites.

Storage model
-------------
Secrets live in the ``tenant_secrets`` table keyed by ``(tenant_id, key_name)``.
Values are stored as ``encrypted_value`` (Fernet ciphertext, base64 url-safe)
plus a ``hint`` (last-4 chars of the plaintext, for masked display in admin
UI). Plaintext is **never** persisted nor returned through any API.

Typical key names:
    llm.openai.api_key
    llm.deepseek.api_key
    llm.kimi.api_key
    llm.siliconflow.api_key
    webhook.budget_warning.url

LLMRouter consults ``SecretManager.get_for_tenant_sync`` per request — value
is cached in-process for ``_CACHE_TTL_SECONDS`` so the hot path is lock-free
after warm-up. Cache is invalidated on PUT/DELETE via ``invalidate(tenant_id)``.

Master key derivation
---------------------
Fernet expects a 32-byte url-safe base64 key. We derive it deterministically
from ``settings.SECRET_KEY`` using HKDF-SHA256 (single-shot, no salt) so the
operator only ever rotates one secret. Override per-deploy by setting
``SECRETS_MASTER_KEY`` in the env (raw 44-char Fernet key).
"""

from __future__ import annotations

import base64
import hashlib
import os
import time
from dataclasses import dataclass
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


_CACHE_TTL_SECONDS = 300  # 5 min — secrets rarely change

# (tenant_id, key_name) -> (value, expires_at)
_cache: dict[tuple[str, str], tuple[Optional[str], float]] = {}


def _derive_master_key() -> bytes:
    """Derive a 32-byte Fernet key from settings.SECRET_KEY (HKDF-SHA256-like)."""
    override = os.getenv("SECRETS_MASTER_KEY")
    if override:
        # Expect a valid Fernet key (44 char base64 of 32 bytes)
        return override.encode("ascii")
    # Single-shot HKDF: HMAC-SHA256(secret, info) truncated to 32 bytes
    base = (settings.SECRET_KEY or "change-me-in-production").encode("utf-8")
    digest = hashlib.sha256(b"hivemind-secret-manager-v1|" + base).digest()
    return base64.urlsafe_b64encode(digest)


_FERNET = Fernet(_derive_master_key())


@dataclass(frozen=True)
class SecretRef:
    """Public-safe view of a stored secret (no plaintext)."""
    key_name: str
    hint: str  # e.g. "sk-...AbCd"
    updated_at_iso: str


class SecretBackend:
    """Abstract backend interface — sync API for hot-path use."""

    async def put(self, session: AsyncSession, tenant_id: str, key_name: str, value: str) -> SecretRef: ...
    async def delete(self, session: AsyncSession, tenant_id: str, key_name: str) -> bool: ...
    async def get(self, session: AsyncSession, tenant_id: str, key_name: str) -> Optional[str]: ...
    async def list_for_tenant(self, session: AsyncSession, tenant_id: str) -> list[SecretRef]: ...


class FernetBackend(SecretBackend):
    """Fernet (AES-128-CBC + HMAC-SHA256) backend — DB-backed, zero external deps."""

    @staticmethod
    def _hint(value: str) -> str:
        v = value.strip()
        if len(v) <= 6:
            return "***"
        return f"{v[:3]}...{v[-4:]}"

    @staticmethod
    def _encrypt(value: str) -> str:
        return _FERNET.encrypt(value.encode("utf-8")).decode("ascii")

    @staticmethod
    def _decrypt(token: str) -> Optional[str]:
        try:
            return _FERNET.decrypt(token.encode("ascii")).decode("utf-8")
        except InvalidToken:
            logger.error("SecretManager: failed to decrypt — master key rotated without re-encryption?")
            return None

    async def put(self, session: AsyncSession, tenant_id: str, key_name: str, value: str) -> SecretRef:
        from app.models.tenant import TenantSecret  # local import — avoid cycle

        if not value or not value.strip():
            raise ValueError("secret value must be non-empty")
        from datetime import datetime
        now = datetime.utcnow()
        cipher = self._encrypt(value)
        hint = self._hint(value)

        existing = (
            await session.execute(
                select(TenantSecret).where(
                    TenantSecret.tenant_id == tenant_id,
                    TenantSecret.key_name == key_name,
                )
            )
        ).scalar_one_or_none()

        if existing is None:
            row = TenantSecret(
                tenant_id=tenant_id,
                key_name=key_name,
                encrypted_value=cipher,
                hint=hint,
                created_at=now,
                updated_at=now,
            )
            session.add(row)
        else:
            existing.encrypted_value = cipher
            existing.hint = hint
            existing.updated_at = now
            row = existing

        await session.commit()
        invalidate(tenant_id, key_name)
        return SecretRef(key_name=key_name, hint=hint, updated_at_iso=now.isoformat())

    async def delete(self, session: AsyncSession, tenant_id: str, key_name: str) -> bool:
        from app.models.tenant import TenantSecret

        existing = (
            await session.execute(
                select(TenantSecret).where(
                    TenantSecret.tenant_id == tenant_id,
                    TenantSecret.key_name == key_name,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            return False
        await session.delete(existing)
        await session.commit()
        invalidate(tenant_id, key_name)
        return True

    async def get(self, session: AsyncSession, tenant_id: str, key_name: str) -> Optional[str]:
        from app.models.tenant import TenantSecret

        row = (
            await session.execute(
                select(TenantSecret).where(
                    TenantSecret.tenant_id == tenant_id,
                    TenantSecret.key_name == key_name,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        return self._decrypt(row.encrypted_value)

    async def list_for_tenant(self, session: AsyncSession, tenant_id: str) -> list[SecretRef]:
        from app.models.tenant import TenantSecret

        rows = (
            await session.execute(
                select(TenantSecret).where(TenantSecret.tenant_id == tenant_id)
            )
        ).scalars().all()
        return [
            SecretRef(
                key_name=r.key_name,
                hint=r.hint,
                updated_at_iso=r.updated_at.isoformat() if r.updated_at else "",
            )
            for r in rows
        ]


# === Module singleton ===
_backend: SecretBackend = FernetBackend()


def get_backend() -> SecretBackend:
    return _backend


def set_backend(backend: SecretBackend) -> None:
    """Override (for tests / future Vault backend)."""
    global _backend
    _backend = backend
    invalidate(None)


# ---------- Hot-path cache helpers ----------

def invalidate(tenant_id: Optional[str], key_name: Optional[str] = None) -> None:
    """Drop cache entries. Pass ``None`` to clear everything."""
    if tenant_id is None:
        _cache.clear()
        return
    if key_name is None:
        for k in [k for k in _cache if k[0] == tenant_id]:
            _cache.pop(k, None)
    else:
        _cache.pop((tenant_id, key_name), None)


async def get_secret(
    session: AsyncSession,
    tenant_id: str,
    key_name: str,
) -> Optional[str]:
    """Cached read. Returns plaintext or None."""
    now = time.monotonic()
    key = (tenant_id, key_name)
    cached = _cache.get(key)
    if cached is not None and cached[1] > now:
        return cached[0]
    value = await _backend.get(session, tenant_id, key_name)
    _cache[key] = (value, now + _CACHE_TTL_SECONDS)
    return value


def get_secret_cached_only(tenant_id: str, key_name: str) -> Optional[str]:
    """Read cached value without DB hit — returns None on miss/expired.

    Used in sync hot paths (e.g. LLMRouter._create_llm) where we cannot
    await. Callers should pre-warm via ``ensure_loaded`` during request setup.
    """
    cached = _cache.get((tenant_id, key_name))
    if cached is None:
        return None
    if cached[1] <= time.monotonic():
        return None
    return cached[0]


async def ensure_loaded(
    session: AsyncSession,
    tenant_id: str,
    key_names: list[str],
) -> None:
    """Pre-warm cache for a request (call from auth middleware / chat entry)."""
    for k in key_names:
        await get_secret(session, tenant_id, k)
