"""
Intent and Prefetch Cache Models (HMER Phase 1).
"""
from datetime import datetime
from typing import Any

from sqlmodel import JSON, Field, SQLModel


class IntentCache(SQLModel, table=True):
    """
    Caches prefetched retrieval results based on predicted intent.
    HMER Phase 1: Predictive Prefetching.
    """

    __tablename__ = "obs_intent_cache"

    # Use query hash or partial query hash as PK for quick lookups
    query_hash: str = Field(primary_key=True)

    predicted_intent: str = Field(index=True)
    confidence: float = Field(default=0.0)

    # JSON storage for the prefetched evidence/snippets
    raw_results: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)

    # Lifecycle management
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(index=True)

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at
