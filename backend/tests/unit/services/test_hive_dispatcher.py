from typing import Any, cast

import pytest

from app.services.claw_router_governance import ClawRouterGovernance


@pytest.mark.asyncio
async def test_simple_prompt_prefers_eco_route():
    router = ClawRouterGovernance()
    decision = router.decide([{"role": "user", "content": "hello, summarize this briefly"}])

    assert decision["tier"] in {"eco", "premium"}
    assert isinstance(decision["model"], str)


@pytest.mark.asyncio
async def test_complex_prompt_can_route_premium():
    router = ClawRouterGovernance()
    prompt = (
        "Please provide architecture tradeoff analysis and root cause debugging plan with "
        "multi-step reasoning and benchmark matrix."
    )
    decision = router.decide([{"role": "user", "content": prompt}])

    assert cast(float, decision["score"]) >= 0.0
    assert decision["tier"] in {"eco", "premium"}


@pytest.mark.asyncio
async def test_cost_guard_downgrades_high_token_non_complex():
    router = ClawRouterGovernance()
    plain_text = "status update " * 1500
    decision = router.decide([{"role": "user", "content": plain_text}])

    assert cast(int, decision["estimated_tokens"]) > 2000
    if decision["reason_code"] == "claw_router.cost_guard_downgrade":
        assert decision["tier"] == "eco"

    snap = router.snapshot()
    stats = cast(dict[str, int], snap["stats"])
    assert stats["eco_routes"] + stats["premium_routes"] >= 1
    events = cast(list[dict[str, Any]], snap["recent_events"])
    assert len(events) >= 1


@pytest.mark.asyncio
async def test_hot_update_config_and_weight_normalization():
    router = ClawRouterGovernance()
    updated = router.update_config(
        {
            "premium_threshold": 0.5,
            "max_tokens_for_eco_guard": 1600,
            "cost_guard_enabled": False,
            "weights": {
                "complexity": 2.0,
                "token_pressure": 1.0,
                "sla_pressure": 1.0,
                "cost_pressure": 0.0,
            },
        }
    )

    assert cast(float, updated["premium_threshold"]) == pytest.approx(0.5)
    assert cast(int, updated["max_tokens_for_eco_guard"]) == 1600
    assert cast(bool, updated["cost_guard_enabled"]) is False
    weights = cast(dict[str, float], updated["weights"])
    assert sum(weights.values()) == pytest.approx(1.0)
    assert weights["complexity"] == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_snapshot_metrics_have_ratios_after_decisions():
    router = ClawRouterGovernance()
    router.decide([{"role": "user", "content": "quick summary"}])
    router.decide([{"role": "user", "content": "urgent architecture benchmark debug plan"}])

    metrics = cast(dict[str, float], router.snapshot()["metrics"])
    assert metrics["total_decisions"] >= 2
    assert 0.0 <= metrics["eco_ratio"] <= 1.0
    assert 0.0 <= metrics["premium_ratio"] <= 1.0
    assert 0.0 <= metrics["cost_guard_downgrade_ratio"] <= 1.0
