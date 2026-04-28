"""
Service Governance utilities for Phase 5 (TASK-SG-001).

Provides:
- Topology mode inspection (monolith/split)
- Gray release decision for split-path rollout

v2: 灰度百分比和拓扑模式现在通过 FeatureFlagService 读取，
    支持 Harness Feature Flags 动态控制，无需重启服务。
    降级链: Harness FF → settings 环境变量 → 默认值
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.core.config import settings
from app.sdk.feature_flags import ff


@dataclass
class TopologyDecision:
    mode: str
    path: str
    is_split_enabled: bool
    gray_percent: int


def _normalized_mode() -> str:
    # 优先从 Feature Flag 读取，降级到 settings
    mode = ff.get_str("service_topology_mode", default=settings.SERVICE_TOPOLOGY_MODE or "monolith")
    mode = mode.strip().lower()
    return mode if mode in {"monolith", "split"} else "monolith"


def _stable_bucket(seed: str) -> int:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def choose_topology_path(*, user_id: str | None = None, query: str | None = None) -> TopologyDecision:
    """
    Decide request path for gray rollout.

    - monolith mode: always `monolith`
    - split mode: percentage-based routing between `split` and `monolith`

    灰度百分比通过 Harness Feature Flag `service_gray_percent` 动态控制，
    无需重启服务即可调整流量比例。
    """
    mode = _normalized_mode()
    # 通过 Feature Flag 读取灰度百分比，支持实时调整
    gray = max(0, min(100, ff.get_int("service_gray_percent", user_id=user_id or "anon", default=0)))

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
    gray = max(0, min(100, ff.get_int("service_gray_percent", default=0)))
    return {
        "topology_mode": mode,
        "gray_percent": gray if mode == "split" else 0,
        "retrieval_service_url": settings.RETRIEVAL_SERVICE_URL,
        "ingestion_service_url": settings.INGESTION_SERVICE_URL,
        "is_split_enabled": mode == "split",
        # 新增：标明当前值来源（harness | settings | default）
        "flag_sources": {
            "service_topology_mode": ff.get_snapshot().get("service_topology_mode", {}).get("source", "unknown"),
            "service_gray_percent": ff.get_snapshot().get("service_gray_percent", {}).get("source", "unknown"),
        },
    }
