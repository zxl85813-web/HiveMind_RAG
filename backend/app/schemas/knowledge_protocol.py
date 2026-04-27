"""
Unified Knowledge Retrieval Protocol
Defines the contract between retrieval services and consumers (Agents/UI).

@covers REQ-008
"""

from typing import Any

from pydantic import BaseModel, Field


class KnowledgeFragment(BaseModel):
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    score: float = 0.0
    kb_id: str
    source_id: str
    chunk_index: int


class KnowledgeQuality(BaseModel):
    max_score: float = 0.0
    avg_score: float = 0.0
    is_satisfactory: bool = True
    quality_tier: str = "GOOD"  # EXCELLENT, GOOD, LOW_RELEVANCE, FAIL


class KnowledgeResponse(BaseModel):
    query: str
    fragments: list[KnowledgeFragment]
    total_found: int
    processing_time_ms: float
    retrieval_strategy: str = "hybrid"
    context_summary: str | None = None
    quality: KnowledgeQuality = Field(default_factory=KnowledgeQuality)
    warnings: list[str] = Field(default_factory=list)
    step_traces: list[str] = Field(default_factory=list)


class KBStatus(BaseModel):
    kb_id: str
    is_healthy: bool
    score_avg: float
    last_failure: str | None = None
    circuit_tripped: bool = False
