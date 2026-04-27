
import uuid
from datetime import datetime
from typing import Any
from sqlmodel import JSON, Field, SQLModel

class SwarmEpisode(SQLModel, table=True):
    """
    [M4.1.2] Episodic Memory: Records of past swarm interactions/summaries.
    """
    __tablename__ = "swarm_episodes"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    conversation_id: str = Field(index=True)
    summary: str
    metadata: dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    tokens_used: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
