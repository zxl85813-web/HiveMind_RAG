
import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel, JSON
from typing import Any

class CognitiveDirective(SQLModel, table=True):
    """
    Consolidated cognitive rules derived from past agent failures (L4 Learning).
    These are injected into ALL future swarm planning cycles.
    """
    __tablename__ = "swarm_cognitive_directives"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    topic: str = Field(index=True)           # e.g., "RAG_RELIABILITY", "SECURITY_CRITIQUE"
    directive: str                          # The actual mandatory instruction
    source_reflections: list[str] = Field(default_factory=list, sa_type=JSON) # IDs of original reflections
    confidence_score: float = 0.0
    is_active: bool = Field(default=False, index=True)
    status: str = Field(default="pending", index=True)  # pending, approved, rejected
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1
