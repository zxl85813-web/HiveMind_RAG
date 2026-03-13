"""
Service Governance utilities for Phase 5 (TASK-SG-001).

Provides:
- Topology mode inspection (monolith/split)
- Gray release decision for split-path rollout
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class TopologyDecision:
    mode: str
    path: str
    is_split_enabled: bool
    gray_percent: int


def _normalized_mode() -> str:
    mode = (settings.SERVICE_TOPOLOGY_MODE or "monolith").strip().lower()
    return mode if mode in {"monolith", "split"} else "monolith"


def _stable_bucket(seed: str) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def choose_topology_path(*, user_id: str | None = None, query: str | None = None) -> TopologyDecision:
    """
    Decide request path for gray rollout.

    - monolith mode: always `monolith`
    - split mode: percentage-based routing between `split` and `monolith`
    """
    mode = _normalized_mode()
    gray = max(0, min(100, int(settings.SERVICE_GOVERNANCE_GRAY_PERCENT)))

    if mode != "split":
        return TopologyDecision(mode="monolith", path="monolith", is_split_enabled=False, gray_percent=0)

    seed = f"{user_id or 'anon'}|{(query or '')[:128]}"
    bucket = _stable_bucket(seed)
    route_to_split = bucket < gray

    return TopologyDecision(
        mode="split",
        path="split" if route_to_split else "monolith",
        is_split_enabled=True,
        gray_percent=gray,
    )


def get_topology_snapshot() -> dict[str, object]:
    mode = _normalized_mode()
    gray = max(0, min(100, int(settings.SERVICE_GOVERNANCE_GRAY_PERCENT)))
    return {
        "topology_mode": mode,
        "gray_percent": gray if mode == "split" else 0,
        "retrieval_service_url": settings.RETRIEVAL_SERVICE_URL,
        "ingestion_service_url": settings.INGESTION_SERVICE_URL,
        "is_split_enabled": mode == "split",
    }
