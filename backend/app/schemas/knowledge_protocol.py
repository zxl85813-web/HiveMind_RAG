"""
Unified Knowledge Retrieval Protocol
Defines the contract between retrieval services and consumers (Agents/UI).
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class KnowledgeFragment(BaseModel):
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0
    kb_id: str
    source_id: str
    chunk_index: int

class KnowledgeResponse(BaseModel):
    query: str
    fragments: List[KnowledgeFragment]
    total_found: int
    processing_time_ms: float
    retrieval_strategy: str = "hybrid"
    context_summary: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)

class KBStatus(BaseModel):
    kb_id: str
    is_healthy: bool
    score_avg: float
    last_failure: Optional[str] = None
    circuit_tripped: bool = False
