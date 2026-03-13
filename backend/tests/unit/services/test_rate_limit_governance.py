import pytest
from typing import Any, cast

from app.services.rate_limit_governance import RateLimitGovernanceCenter


@pytest.mark.asyncio
async def test_route_limit_blocks_after_capacity():
    center = RateLimitGovernanceCenter()
    center.update_policies(
        [
            {
                "route": "/api/v1/chat/completions",
                "route_rule": {"enabled": True, "capacity": 1, "refill_per_sec": 0.0},
                "user_rule": {"enabled": False, "capacity": 1, "refill_per_sec": 0.0},
                "key_rule": {"enabled": False, "capacity": 1, "refill_per_sec": 0.0},
            }
        ]
    )

    first = center.check(route="/api/v1/chat/completions", user_id="u1", api_key=None)
    assert first["allowed"] is True

    second = center.check(route="/api/v1/chat/completions", user_id="u1", api_key=None)
    assert second["allowed"] is False
    assert second["dimension"] == "route"
    assert cast(int, second["retry_after_sec"]) >= 1


@pytest.mark.asyncio
async def test_user_dimension_isolated_per_user():
    center = RateLimitGovernanceCenter()
    center.update_policies(
        [
            {
                "route": "/api/v1/chat/completions",
                "route_rule": {"enabled": False, "capacity": 1, "refill_per_sec": 0.0},
                "user_rule": {"enabled": True, "capacity": 1, "refill_per_sec": 0.0},
                "key_rule": {"enabled": False, "capacity": 1, "refill_per_sec": 0.0},
            }
        ]
    )

    u1_first = center.check(route="/api/v1/chat/completions", user_id="user-a", api_key=None)
    u1_second = center.check(route="/api/v1/chat/completions", user_id="user-a", api_key=None)
    u2_first = center.check(route="/api/v1/chat/completions", user_id="user-b", api_key=None)

    assert u1_first["allowed"] is True
    assert u1_second["allowed"] is False
    assert u1_second["dimension"] == "user"
    assert u2_first["allowed"] is True


@pytest.mark.asyncio
async def test_hot_update_replaces_policy_set():
    center = RateLimitGovernanceCenter()
    snap_before = center.snapshot()
    assert cast(int, snap_before["policy_count"]) >= 1

    updated = center.update_policies(
        [
            {
                "route": "/api/v1/custom/route",
                "route_rule": {"enabled": True, "capacity": 5, "refill_per_sec": 1.0},
                "user_rule": {"enabled": True, "capacity": 3, "refill_per_sec": 0.5},
                "key_rule": {"enabled": True, "capacity": 4, "refill_per_sec": 0.8},
            }
        ]
    )

    assert cast(int, updated["policy_count"]) == 1
    policies = cast(list[dict[str, Any]], updated["policies"])
    assert len(policies) == 1
    assert policies[0]["route"] == "/api/v1/custom/route"
