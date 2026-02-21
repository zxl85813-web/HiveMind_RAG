"""
WebSocket message protocol schemas.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel

# ==========================================
#  Server → Client message types
# ==========================================


class ServerEventType(str, Enum):
    """Events pushed from server to client."""

    AGENT_STATUS = "agent_status"  # Agent execution progress
    NOTIFICATION = "notification"  # System notifications
    SUGGESTION = "suggestion"  # AI proactive suggestions
    TODO_UPDATE = "todo_update"  # Shared TODO list changes
    REFLECTION = "reflection"  # Agent self-reflection results
    LEARNING_UPDATE = "learning_update"  # External learning discoveries
    TASK_COMPLETE = "task_complete"  # Background task completion
    HEARTBEAT = "heartbeat"  # Keep-alive


class ServerMessage(BaseModel):
    """Base message from server to client."""

    event: ServerEventType
    data: dict
    timestamp: datetime


# ==========================================
#  Client → Server message types
# ==========================================


class ClientEventType(str, Enum):
    """Events sent from client to server."""

    CANCEL = "cancel"  # Cancel ongoing generation
    PING = "ping"  # Heartbeat
    SUBSCRIBE = "subscribe"  # Subscribe to event channels
    UNSUBSCRIBE = "unsubscribe"  # Unsubscribe from event channels


class ClientMessage(BaseModel):
    """Base message from client to server."""

    event: ClientEventType
    data: dict = {}
