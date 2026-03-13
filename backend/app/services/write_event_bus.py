"""
Write Event Bus (Phase 5 / TASK-SG-002).

Publishes write-side events so read-side services can invalidate caches
or trigger async reconciliation.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from app.core.config import settings

_EVENT_CHANNEL = "hivemind:kb_write_events"


async def publish_write_event(
    *,
    event_type: str,
    kb_id: str,
    doc_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> None:
    event = {
        "event_type": event_type,
        "kb_id": kb_id,
        "doc_id": doc_id,
        "payload": payload or {},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Best-effort Redis publish; fallback to structured log if Redis package/runtime unavailable.
    try:
        import redis.asyncio as redis  # type: ignore

        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            await client.publish(_EVENT_CHANNEL, json.dumps(event, ensure_ascii=False))
        finally:
            await client.close()
    except Exception as exc:
        logger.warning(f"[WriteEventBus] Redis publish skipped: {exc}")

    logger.info(f"[WriteEventBus] {event}")


def fire_and_forget_write_event(**kwargs: Any) -> None:
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(publish_write_event(**kwargs))
        else:
            loop.run_until_complete(publish_write_event(**kwargs))
    except Exception as exc:
        logger.warning(f"[WriteEventBus] Scheduling failed: {exc}")
