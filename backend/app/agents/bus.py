"""
Agent Message Bus — enables real-time peer-to-peer communication between agents.
Break the LangGraph 'State Only' barrier.
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from loguru import logger


@dataclass
class BusMessage:
    """A standard message envelope on the agent bus."""
    topic: str
    sender: str
    payload: Any
    recipient: str | None = None
    timestamp: float = field(default_factory=time.time)

class AgentMessageBus:
    """
    In-process Pub/Sub bus for swarm internal coordination.
    Allows parallel agents to sync context without waiting for node completion.
    """

    def __init__(self):
        # topic -> set of async callback functions
        self._subscribers: dict[str, set[Callable[[BusMessage], Awaitable[None]]]] = {}
        # Global lock for thread safety (though mostly async)
        self._lock = asyncio.Lock()
        logger.info("📡 Agent Message Bus initialized.")

    async def subscribe(self, topic: str, callback: Callable[[BusMessage], Awaitable[None]]):
        """Register a callback for a specific topic (or '*' for all)."""
        async with self._lock:
            if topic not in self._subscribers:
                self._subscribers[topic] = set()
            self._subscribers[topic].add(callback)
            logger.debug(f"📥 [{topic}] New subscriber added.")

    async def unsubscribe(self, topic: str, callback: Callable[[BusMessage], Awaitable[None]]):
        """Remove a subscriber."""
        async with self._lock:
            if topic in self._subscribers:
                self._subscribers[topic].discard(callback)

    async def publish(self, topic: str, sender: str, payload: Any, recipient: str | None = None):
        """
        Broadcast a message to all subscribers of a topic.
        Does not block the publisher (fire and forget for individuals).
        """
        message = BusMessage(topic=topic, sender=sender, payload=payload, recipient=recipient)

        # Determine target subscribers
        targets = set()
        async with self._lock:
            # 1. Direct topic matches
            if topic in self._subscribers:
                targets.update(self._subscribers[topic])
            # 2. Global observers
            if "*" in self._subscribers:
                targets.update(self._subscribers["*"])

        if not targets:
            return

        # Execute all listeners as concurrent tasks
        # Each listener handles its own error to prevent bus crashes
        tasks = []
        for callback in targets:
            tasks.append(self._safe_dispatch(callback, message))

        # Fire and forget - don't wait for all handlers to finish
        asyncio.create_task(asyncio.gather(*tasks, return_exceptions=True))

    async def _safe_dispatch(self, callback: Callable[[BusMessage], Awaitable[None]], message: BusMessage):
        """Guarded execution of a subscriber callback."""
        try:
            await callback(message)
        except Exception as e:
            logger.error(f"❌ [Bus Dispatch Error] Topic={message.topic}, Sender={message.sender}: {e}")

# Global bus instance for the swarm process
_bus = AgentMessageBus()

def get_agent_bus() -> AgentMessageBus:
    return _bus
