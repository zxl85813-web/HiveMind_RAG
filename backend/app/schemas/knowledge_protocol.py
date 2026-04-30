"""
Unified Knowledge Retrieval Protocol
Defines the contract between retrieval services and consumers (Agents/UI).

Protocol versioning:
- v1 (2026-03): basic structure, score-only, no citations.
- v2 (2026-04): adds confidence, citations, query intent echo, model
  fingerprint and forward-compatible `extensions` slot.
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

PROTOCOL_VERSION = "2.0"


class Citation(BaseModel):
    """Stable citation pointer for a knowledge fragment.

    Designed so that any downstream consumer (LLM prompt, UI link, audit
    log) can render or re-resolve the source without re-querying.
    """

    citation_id: str = Field(..., description="Stable id usable as [^id] in markdown")
    kb_id: str
    source_id: str
    document_title: Optional[str] = None
    chunk_index: Optional[int] = None
    page: Optional[int] = None
    location: Optional[str] = Field(
        None,
        description="Free-form locator e.g. 'p.3 §2.1' or 'lines 120-145'",
    )
    url: Optional[str] = Field(
        None, description="Optional deep-link to view the source in the UI"
    )


class KnowledgeFragment(BaseModel):
    """A single retrieved chunk of knowledge, agent/LLM friendly."""

    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    score: float = Field(0.0, description="Raw retrieval score (cosine / bm25 / fused)")
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Normalised 0-1 confidence after rerank/calibration",
    )
    kb_id: str
    source_id: str
    chunk_index: int
    citation: Optional[Citation] = Field(
        None, description="Resolved citation pointer; populated by the gateway"
    )
    # Forward-compatible extension bag for new fields without breaking consumers.
    extensions: Dict[str, Any] = Field(default_factory=dict)


class KnowledgeResponse(BaseModel):
    """Top-level response returned by the RAG gateway."""

    protocol_version: str = Field(default=PROTOCOL_VERSION)
    query: str
    fragments: List[KnowledgeFragment]
    citations: List[Citation] = Field(
        default_factory=list,
        description="Aggregated unique citations for the whole response.",
    )
    total_found: int
    processing_time_ms: float
    retrieval_strategy: str = "hybrid"
    query_intent: Optional[str] = Field(
        None, description="Echoed intent classification (factoid/compare/summary/...)"
    )
    confidence: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Aggregate confidence across fragments (max or weighted mean)",
    )
    context_summary: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    # Diagnostics that consumers (UI / Agent supervisor) can inspect.
    kb_ids: List[str] = Field(default_factory=list)
    cache_hit: bool = False
    extensions: Dict[str, Any] = Field(default_factory=dict)

    # ------------------------------------------------------------------
    # Convenience helpers — keep consumers free of formatting boilerplate.
    # ------------------------------------------------------------------
    def to_prompt_context(
        self,
        max_chars: Optional[int] = None,
        include_citations: bool = True,
    ) -> str:
        """Render fragments into a deterministic prompt-ready block.

        Each fragment is prefixed with a `[^id]` tag so the LLM can produce
        inline citations that map back to ``self.citations``.
        """

        lines: List[str] = []
        used = 0
        for frag in self.fragments:
            tag = ""
            if include_citations and frag.citation is not None:
                tag = f"[^{frag.citation.citation_id}] "
            piece = f"{tag}{frag.content.strip()}"
            if max_chars is not None and used + len(piece) > max_chars:
                lines.append("…[truncated]")
                break
            lines.append(piece)
            used += len(piece)
        return "\n\n".join(lines)

    def top_sources(self, limit: int = 5) -> List[Citation]:
        """Return up to ``limit`` distinct citations ordered by appearance."""
        seen: set[str] = set()
        out: List[Citation] = []
        for frag in self.fragments:
            if frag.citation is None:
                continue
            key = frag.citation.citation_id
            if key in seen:
                continue
            seen.add(key)
            out.append(frag.citation)
            if len(out) >= limit:
                break
        return out


class KnowledgeRetrieveRequest(BaseModel):
    """Request body for the smart multi-KB retrieval endpoint."""

    query: str
    kb_ids: Optional[List[str]] = Field(
        None,
        description="Explicit KB scope. If omitted, the gateway will auto-route.",
    )
    top_k: int = Field(5, ge=1, le=50)
    strategy: Literal["hybrid", "vector", "bm25", "graph"] = "hybrid"
    include_citations: bool = True
    max_context_chars: Optional[int] = Field(
        None, description="If set, response.context_summary is pre-rendered."
    )


class KBStatus(BaseModel):
    kb_id: str
    is_healthy: bool
    score_avg: float
    last_failure: Optional[str] = None
    circuit_tripped: bool = False
