"""
Redis Blackboard Service (V3 Architecture).

Provides a high-throughput, cluster-wide shared memory for Agents to exchange
real-time 'Reflections', 'Corrections', and 'Learned Rules' without DB overhead.
"""

import json
from datetime import datetime
from typing import Any

import redis.asyncio as redis
from loguru import logger

from app.core.config import settings


class RedisBlackboard:
    """
    Acts as a 'Shared Brain' for the Swarm cluster.
    """

    def __init__(self, channel: str = "swarm_blackboard"):
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.channel = channel

    async def post_reflection(self, agent_name: str, topic: str, content: Any, ttl: int = 3600):
        """
        Broadcasts a learned insight to the blackboard.
        """
        payload = {
            "agent_name": agent_name,
            "topic": topic,
            "content": content,
            "timestamp": str(datetime.utcnow()) if "datetime" in globals() else "",
        }

        # 1. Store in a hash for lookup
        key = f"blackboard:reflections:{topic}"
        await self.redis_client.set(key, json.dumps(payload), ex=ttl)

        # 2. Publish to subscribers (Real-time sync)
        await self.redis_client.publish(self.channel, json.dumps(payload))
        logger.info(f"🧠 [Blackboard] Agent {agent_name} posted insight on: {topic}")

    async def get_insight(self, topic: str) -> dict | None:
        """
        Retrieve a specific insight from the shared brain.
        """
        key = f"blackboard:reflections:{topic}"
        data = await self.redis_client.get(key)
        return json.loads(data) if data else None

    async def list_recent_topics(self, pattern: str = "blackboard:reflections:*") -> list[str]:
        """
        Discover what the cluster is currently 'thinking' about.
        """
        keys = await self.redis_client.keys(pattern)
        return [k.split(":")[-1] for k in keys]


# Global singleton
_blackboard = None


def get_blackboard() -> RedisBlackboard:
    global _blackboard
    if not _blackboard:
        _blackboard = RedisBlackboard()
    return _blackboard
