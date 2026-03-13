import asyncio

import pytest

from app.services.dependency_circuit_breaker import DependencyCircuitBreakerManager


@pytest.fixture
def tuned_cb(monkeypatch):
    # Keep thresholds tiny so tests run quickly and deterministically.
    monkeypatch.setattr("app.services.dependency_circuit_breaker.settings.CB_ENABLED", True)
    monkeypatch.setattr("app.services.dependency_circuit_breaker.settings.CB_WINDOW_SIZE", 5)
    monkeypatch.setattr("app.services.dependency_circuit_breaker.settings.CB_MIN_REQUESTS", 1)
    monkeypatch.setattr("app.services.dependency_circuit_breaker.settings.CB_ERROR_RATE_THRESHOLD", 0.5)
    monkeypatch.setattr("app.services.dependency_circuit_breaker.settings.CB_OPEN_DURATION_SEC", 1)
    monkeypatch.setattr("app.services.dependency_circuit_breaker.settings.CB_HALF_OPEN_PROBES", 1)
    monkeypatch.setattr("app.services.dependency_circuit_breaker.settings.CB_TIMEOUT_LLM_MS", 120)
    monkeypatch.setattr("app.services.dependency_circuit_breaker.settings.CB_TIMEOUT_ES_MS", 120)
    monkeypatch.setattr("app.services.dependency_circuit_breaker.settings.CB_TIMEOUT_NEO4J_MS", 120)
    return DependencyCircuitBreakerManager()


@pytest.mark.asyncio
async def test_opens_after_failure_threshold(tuned_cb):
    async def _boom():
        raise RuntimeError("llm down")

    with pytest.raises(RuntimeError):
        await tuned_cb.execute("llm", _boom)

    snapshot = tuned_cb.snapshot()
    assert snapshot["llm"]["state"] == "OPEN"
    assert snapshot["llm"]["window_failures"] >= 1


@pytest.mark.asyncio
async def test_open_state_blocks_until_half_open(tuned_cb):
    async def _boom():
        raise RuntimeError("es down")

    with pytest.raises(RuntimeError):
        await tuned_cb.execute("es", _boom)

    with pytest.raises(RuntimeError, match="Dependency circuit OPEN: es"):
        await tuned_cb.execute("es", lambda: asyncio.sleep(0))


@pytest.mark.asyncio
async def test_half_open_probe_success_closes_circuit(tuned_cb):
    # Trip first
    async def _boom():
        raise RuntimeError("neo4j down")

    with pytest.raises(RuntimeError):
        await tuned_cb.execute("neo4j", _boom)

    # Fast-forward open duration via internal clock hook.
    clock = {"t": 1000.0}
    tuned_cb._now = lambda: clock["t"]  # type: ignore[method-assign]
    tuned_cb._states["neo4j"].opened_at = 998.0

    async def _ok():
        return {"ok": True}

    result = await tuned_cb.execute("neo4j", _ok)
    assert result == {"ok": True}
    assert tuned_cb.snapshot()["neo4j"]["state"] == "CLOSED"


@pytest.mark.asyncio
async def test_timeout_counts_as_failure(tuned_cb):
    async def _slow():
        await asyncio.sleep(0.3)
        return "late"

    with pytest.raises(Exception):
        await tuned_cb.execute("llm", _slow)

    assert tuned_cb.snapshot()["llm"]["state"] == "OPEN"
