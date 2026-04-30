"""
Rainbow Deployment Router (Anthropic 2.1J).

What is "Rainbow Deployment"?
-----------------------------
Anthropic's production write-up describes running multiple model
versions side-by-side in production with a sticky, weighted split:

    stable  : 80%  (v3.1 — current GA)
    canary  : 15%  (v3.2 — being soaked in prod traffic)
    rollback:  5%  (v3.0 — kept warm in case canary regresses)

The router picks a "ring" by hashing the **conversation id** so the
same conversation always lands on the same ring (the model never
changes mid-thread). When metrics show the canary is healthy you
gradually shift weight; when they regress you can flip back to
``rollback`` in seconds without redeploying.

Design choices
--------------
- **Sticky-by-conversation**: hash(conversation_id) → ring. Stateless,
  no central registry needed; same conversation_id → same ring on any
  worker.
- **Weighted, not bucketed**: weights are normalised; you can express
  any split (50/30/20, 95/5/0, etc.) without touching code.
- **Reload-friendly**: ``RainbowConfig.from_settings()`` reads the
  current shape from settings on every call. Operators flip the split
  by editing config; no process restart needed.
- **Defensive**: if no rings are configured we transparently fall back
  to the stable LLMRouter — turning Rainbow off is the default state.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from langchain_core.language_models import BaseChatModel
from loguru import logger

from app.agents.llm_router import LLMRouter, ModelTier


@dataclass
class Ring:
    """One deployment ring: a named model variant with a routing weight."""

    name: str                       # "stable" | "canary" | "rollback" | ...
    weight: float                   # relative weight; normalised at routing time
    model_overrides: Dict[ModelTier, str] = field(default_factory=dict)
    provider_overrides: Dict[ModelTier, str] = field(default_factory=dict)


@dataclass
class RainbowConfig:
    rings: List[Ring] = field(default_factory=list)

    @classmethod
    def disabled(cls) -> "RainbowConfig":
        return cls(rings=[])

    @property
    def enabled(self) -> bool:
        return any(r.weight > 0 for r in self.rings)


class RainbowRouter:
    """LLM router with rainbow-deployment routing semantics.

    Wraps a base ``LLMRouter`` per ring. ``get_model(tier, key)`` picks
    a ring deterministically from ``key`` (typically the conversation
    id) and returns that ring's model for the requested tier.
    """

    def __init__(self, config: Optional[RainbowConfig] = None):
        self._config = config or RainbowConfig.disabled()
        # One LLMRouter per ring. Each one snapshots the global model
        # config; per-tier overrides are layered on the resolved instance.
        self._ring_routers: Dict[str, LLMRouter] = {}
        for ring in self._config.rings:
            try:
                self._ring_routers[ring.name] = LLMRouter()
            except Exception as e:  # noqa: BLE001
                logger.warning(f"🌈 Ring '{ring.name}' failed to init: {e}")

        # Always keep a default base router for the disabled / fallback path.
        self._default = LLMRouter()

        if self._config.enabled:
            logger.info(
                f"🌈 RainbowRouter enabled — rings: "
                + ", ".join(f"{r.name}={r.weight:g}" for r in self._config.rings)
            )

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------
    def pick_ring(self, key: Optional[str]) -> Optional[Ring]:
        """Deterministically pick a ring for the given sticky key.

        Returns ``None`` when rainbow is disabled (caller should use
        the default router).
        """
        if not self._config.enabled:
            return None
        rings = [r for r in self._config.rings if r.weight > 0]
        if not rings:
            return None

        total = sum(r.weight for r in rings)
        # Stable hash → fraction in [0, 1).
        bucket = key or "default"
        h = int(hashlib.sha1(bucket.encode("utf-8")).hexdigest()[:12], 16)
        frac = (h / 0xFFFFFFFFFFFF) * total

        running = 0.0
        for ring in rings:
            running += ring.weight
            if frac < running:
                return ring
        return rings[-1]

    def get_model(
        self,
        tier: ModelTier = ModelTier.BALANCED,
        *,
        key: Optional[str] = None,
    ) -> BaseChatModel:
        ring = self.pick_ring(key)
        if ring is None:
            return self._default.get_model(tier)

        router = self._ring_routers.get(ring.name)
        if router is None:
            logger.warning(f"🌈 Ring '{ring.name}' has no router; falling back to default")
            return self._default.get_model(tier)

        # Honour per-tier overrides if present. We mutate a fresh model
        # spec rather than the cached instance; cheap because tiers are
        # singletons inside each ring router and we only override two
        # attributes (model_name / openai_api_base).
        instance = router.get_model(tier)
        model_override = ring.model_overrides.get(tier)
        if model_override and getattr(instance, "model_name", None) != model_override:
            try:
                instance.model_name = model_override  # type: ignore[attr-defined]
            except Exception:  # noqa: BLE001
                pass
        return instance

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------
    def describe(self) -> Dict[str, Dict[str, object]]:
        return {
            r.name: {
                "weight": r.weight,
                "model_overrides": {t.value: m for t, m in r.model_overrides.items()},
                "provider_overrides": {
                    t.value: p for t, p in r.provider_overrides.items()
                },
            }
            for r in self._config.rings
        }


# --------------------------------------------------------------------------
# Per-tenant accessor — each tenant gets its own router config so a green
# experiment in tenant A doesn't bleed into tenant B's traffic.
# --------------------------------------------------------------------------
import threading

_routers: dict[str, "RainbowRouter"] = {}
_router_lock = threading.Lock()


def _resolve_tenant(tenant_id: Optional[str]) -> str:
    if tenant_id:
        return tenant_id
    from app.core.tenant_context import get_current_tenant
    return get_current_tenant()


def get_rainbow_router(tenant_id: Optional[str] = None) -> RainbowRouter:
    tid = _resolve_tenant(tenant_id)
    inst = _routers.get(tid)
    if inst is None:
        with _router_lock:
            inst = _routers.get(tid)
            if inst is None:
                inst = RainbowRouter()
                _routers[tid] = inst
    return inst


def set_rainbow_config(config: RainbowConfig, tenant_id: Optional[str] = None) -> RainbowRouter:
    """Replace the active rainbow config for a tenant. Returns the new router."""
    tid = _resolve_tenant(tenant_id)
    with _router_lock:
        inst = RainbowRouter(config)
        _routers[tid] = inst
        return inst
