"""
WebSocket Connection Manager — manages persistent connections for push notifications.
"""

from typing import Any

from fastapi import WebSocket
from loguru import logger


class ConnectionManager:
    """
    Manages WebSocket connections for all connected clients.

    Responsibilities:
    - Track active connections per user
    - Broadcast messages to specific users or all users
    - Handle subscription channels
    - Heartbeat management
    """

    def __init__(self) -> None:
        # user_id → list of active WebSocket connections
        self._connections: dict[str, list[WebSocket]] = {}
        # user_id → set of subscribed channels
        self._subscriptions: dict[str, set[str]] = {}

    async def connect(self, websocket: WebSocket, user_id: str) -> None:
        """Accept and register a new WebSocket connection."""
        await websocket.accept()
        if user_id not in self._connections:
            self._connections[user_id] = []
        self._connections[user_id].append(websocket)
        logger.info(f"WebSocket connected: user={user_id}, total={self.active_count}")

    async def disconnect(self, websocket: WebSocket, user_id: str) -> None:
        """Remove a disconnected WebSocket."""
        if user_id in self._connections:
            self._connections[user_id].remove(websocket)
            if not self._connections[user_id]:
                del self._connections[user_id]
                self._subscriptions.pop(user_id, None)
        logger.info(f"WebSocket disconnected: user={user_id}, total={self.active_count}")

    async def send_to_user(self, user_id: str, message: dict[str, Any]) -> None:
        """Send a message to all connections of a specific user."""
        if user_id in self._connections:
            for ws in self._connections[user_id]:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send to user={user_id}: {e}")

    async def broadcast(self, message: dict[str, Any], channel: str | None = None) -> None:
        """Broadcast a message to all connected users (optionally filtered by channel)."""
        for user_id, connections in self._connections.items():
            if channel and channel not in self._subscriptions.get(user_id, set()):
                continue
            for ws in connections:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.warning(f"Broadcast failed for user={user_id}: {e}")

    def subscribe(self, user_id: str, channel: str) -> None:
        """Subscribe a user to a notification channel."""
        if user_id not in self._subscriptions:
            self._subscriptions[user_id] = set()
        self._subscriptions[user_id].add(channel)

    def unsubscribe(self, user_id: str, channel: str) -> None:
        """Unsubscribe a user from a notification channel."""
        if user_id in self._subscriptions:
            self._subscriptions[user_id].discard(channel)

    @property
    def active_count(self) -> int:
        """Total number of active connections."""
        return sum(len(conns) for conns in self._connections.values())


# Global singleton
ws_manager = ConnectionManager()
