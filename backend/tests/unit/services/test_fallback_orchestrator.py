import pytest
from typing import cast

from app.services.fallback_orchestrator import FallbackOrchestrator


@pytest.mark.asyncio
async def test_recover_prefers_cache(monkeypatch):
    orchestrator = FallbackOrchestrator()

    async def _cache_hit(_query):
        return {"content": "cached-answer"}

    monkeypatch.setattr("app.services.fallback_orchestrator.CacheService.get_cached_response", _cache_hit)

    async def _local():
        return "local-answer"

    text, reason = await orchestrator.recover_text(query="what is cb", local_invoke=_local, backup_invoke=None)
    assert text == "cached-answer"
    assert reason == "fallback.cache_hit"
    stats = cast(dict[str, int], orchestrator.snapshot()["stats"])
    assert stats["cache_hit"] == 1


@pytest.mark.asyncio
async def test_recover_uses_local_when_no_cache(monkeypatch):
    orchestrator = FallbackOrchestrator()

    async def _cache_miss(_query):
        return None

    monkeypatch.setattr("app.services.fallback_orchestrator.CacheService.get_cached_response", _cache_miss)

    async def _local():
        return "local-ok"

    text, reason = await orchestrator.recover_text(query="query", local_invoke=_local, backup_invoke=None)
    assert text == "local-ok"
    assert reason == "fallback.local_lightweight"
    stats = cast(dict[str, int], orchestrator.snapshot()["stats"])
    assert stats["local_lightweight_success"] == 1


@pytest.mark.asyncio
async def test_recover_uses_backup_when_local_fails(monkeypatch):
    orchestrator = FallbackOrchestrator()

    async def _cache_miss(_query):
        return None

    monkeypatch.setattr("app.services.fallback_orchestrator.CacheService.get_cached_response", _cache_miss)

    async def _local():
        raise RuntimeError("local failed")

    async def _backup():
        return "backup-ok"

    text, reason = await orchestrator.recover_text(query="query", local_invoke=_local, backup_invoke=_backup)
    assert text == "backup-ok"
    assert reason == "fallback.backup_provider"
    stats = cast(dict[str, int], orchestrator.snapshot()["stats"])
    assert stats["backup_provider_success"] == 1


@pytest.mark.asyncio
async def test_recover_raises_when_chain_exhausted(monkeypatch):
    orchestrator = FallbackOrchestrator()

    async def _cache_miss(_query):
        return None

    monkeypatch.setattr("app.services.fallback_orchestrator.CacheService.get_cached_response", _cache_miss)

    async def _local():
        raise RuntimeError("local down")

    async def _backup():
        raise RuntimeError("backup down")

    with pytest.raises(RuntimeError, match="Fallback chain exhausted"):
        await orchestrator.recover_text(query="query", local_invoke=_local, backup_invoke=_backup)

    stats = cast(dict[str, int], orchestrator.snapshot()["stats"])
    assert stats["fallback_exhausted"] == 1
