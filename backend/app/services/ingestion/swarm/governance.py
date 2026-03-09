"""
Swarm Circuit Breaker (V3 Architecture).

Provides a distributed mechanism to track failures per Knowledge Base and
temporarily halt processing for unstable sources.
"""

from datetime import datetime

import redis
from loguru import logger

from app.core.config import settings


class SwarmCircuitBreaker:
    """
    Stateful circuit breaker using Redis.
    Transitions: CLOSED -> OPEN (on threshold) -> HALF-OPEN (on timeout) -> CLOSED (on success)
    """

    def __init__(self, kb_id: str, threshold: int = 20, timeout_sec: int = 300):
        self.kb_id = kb_id
        self.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.threshold = threshold
        self.timeout_sec = timeout_sec
        self._key_prefix = f"swarm:cb:{kb_id}"

    def is_available(self) -> bool:
        """Check if processing is allowed for this KB."""
        state = self.redis.get(f"{self._key_prefix}:state") or "CLOSED"

        if state == "OPEN":
            # Check if timeout passed
            opened_at_str = self.redis.get(f"{self._key_prefix}:opened_at")
            if opened_at_str:
                opened_at = datetime.fromisoformat(opened_at_str)
                if (datetime.utcnow() - opened_at).total_seconds() > self.timeout_sec:
                    logger.info(f"🟡 [CircuitBreaker] KB {self.kb_id} entering HALF-OPEN state.")
                    self.redis.set(f"{self._key_prefix}:state", "HALF-OPEN")
                    return True
            return False

        return True

    def record_failure(self):
        """Increment failure count and open circuit if threshold exceeded."""
        fail_count = self.redis.incr(f"{self._key_prefix}:fails")
        # Expire fail records if they don't hit threshold quickly
        self.redis.expire(f"{self._key_prefix}:fails", 3600)

        if fail_count >= self.threshold:
            logger.error(f"🔴 [CircuitBreaker] KB {self.kb_id} threshold met. OPENING CIRCUIT.")
            self.redis.set(f"{self._key_prefix}:state", "OPEN")
            self.redis.set(f"{self._key_prefix}:opened_at", datetime.utcnow().isoformat())

    def record_success(self):
        """Reset failure count and close circuit."""
        state = self.redis.get(f"{self._key_prefix}:state")
        if state in ["OPEN", "HALF-OPEN"]:
            logger.success(f"🟢 [CircuitBreaker] KB {self.kb_id} recovered. CLOSING CIRCUIT.")

        self.redis.delete(f"{self._key_prefix}:fails")
        self.redis.set(f"{self._key_prefix}:state", "CLOSED")
        self.redis.delete(f"{self._key_prefix}:opened_at")
