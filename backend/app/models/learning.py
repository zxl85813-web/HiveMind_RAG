import uuid
from datetime import datetime
from typing import Any
from sqlmodel import JSON, Field, SQLModel

class TechSubscription(SQLModel, table=True):
    """
    [M7.1.1] Persistent subscription for technology topics.
    """
    __tablename__ = "swarm_learning_subscriptions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    topic: str = Field(index=True)
    is_active: bool = Field(default=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TechDiscovery(SQLModel, table=True):
    """
    [M7.1.2] Persistent storage for crawled tech signals.
    """
    __tablename__ = "swarm_learning_discoveries"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    title: str = Field(index=True)
    summary: str = ""
    url: str = Field(index=True)
    category: str = Field(default="article", index=True)  # article | paper | tool
    relevance_score: float = 0.5
    details: dict = Field(default_factory=dict, sa_type=JSON)
    status: str = Field(default="new", index=True)  # new | ingested | rejected
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
