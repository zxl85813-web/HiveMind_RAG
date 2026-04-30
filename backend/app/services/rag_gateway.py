"""
RAG Gateway — single, governed entry point for knowledge retrieval.

Responsibilities:
- Run the real ``RetrievalPipeline`` (no more stubbed fragments).
- Convert ``VectorDocument`` results into the public ``KnowledgeResponse``
  protocol (v2): citations, normalised confidence, query intent echo,
  warnings, optional pre-rendered prompt context.
- Per-KB circuit breaker (open / half-open / closed).
- Aggregate-level fault isolation so a single failing KB cannot drag
  down the whole call.

This module is intentionally consumer-agnostic: Agents, Skills and the
REST API all call ``RAGGateway.retrieve`` and receive the exact same
shape.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from app.core.config import settings
from app.core.vector_store import SearchType, VectorDocument
from app.schemas.knowledge_protocol import (
    Citation,
    KBStatus,
    KnowledgeFragment,
    KnowledgeResponse,
)
from app.services.retrieval.pipeline import RetrievalPipeline, get_retrieval_service


def _normalise_scores(scores: List[float]) -> List[float]:
    """Min-max normalise to [0, 1]; degenerate to 1.0 when all equal."""
    if not scores:
        return []
    lo, hi = min(scores), max(scores)
    if hi - lo < 1e-9:
        return [1.0 for _ in scores]
    return [(s - lo) / (hi - lo) for s in scores]


def _make_citation(kb_id: str, doc: VectorDocument, fallback_idx: int) -> Citation:
    """Build a stable, semantically-aliased citation pointer.

    Citation IDs the agent sees look like ``doc-rfc2119-1#3`` instead of
    ``ab12cd:9f8e7d6c5b4a#3``. Aliases are sticky (same raw id always
    maps to the same alias) so the model can reliably copy them back
    into tool calls.
    """
    from app.services.semantic_id_mapper import get_semantic_id_mapper

    md = doc.metadata or {}
    source_id = str(
        md.get("source_id")
        or md.get("document_id")
        or md.get("source")
        or md.get("file")
        or f"{kb_id}-doc-{fallback_idx}"
    )
    chunk_index = md.get("chunk_index")
    try:
        chunk_index = int(chunk_index) if chunk_index is not None else None
    except (TypeError, ValueError):
        chunk_index = None

    mapper = get_semantic_id_mapper()
    title_hint = md.get("title") or md.get("file_name") or md.get("source")
    doc_alias = mapper.alias_for(source_id, kind="doc", hint=title_hint)
    citation_id = doc_alias if chunk_index is None else f"{doc_alias}#{chunk_index}"

    return Citation(
        citation_id=citation_id,
        kb_id=kb_id,
        source_id=source_id,
        document_title=md.get("title") or md.get("file_name") or md.get("source"),
        chunk_index=chunk_index,
        page=md.get("page"),
        location=md.get("location"),
        url=md.get("url"),
    )


class RAGGateway:
    """The single entry point for knowledge retrieval requests."""

    _instance: Optional["RAGGateway"] = None
    _circuit_breakers: Dict[str, Dict[str, Any]] = {}

    def __init__(self, pipeline: Optional[RetrievalPipeline] = None):
        self.pipeline = pipeline or get_retrieval_service()
        self.max_failures = getattr(settings, "RAG_GATEWAY_MAX_FAILURES", 3)
        self.recovery_timeout = getattr(settings, "RAG_GATEWAY_RECOVERY_TIMEOUT", 60)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def retrieve(
        self,
        query: str,
        kb_ids: List[str],
        top_k: int = 5,
        strategy: str = "hybrid",
        *,
        user_id: Optional[str] = None,
        is_admin: bool = False,
        recall_top_k: Optional[int] = None,
        max_context_chars: Optional[int] = None,
    ) -> KnowledgeResponse:
        """Retrieve fragments from one or more KBs through the pipeline.

        ``recall_top_k`` controls the wide-net recall stage that feeds
        the reranker; ``top_k`` is the final cut. Defaults aim for the
        Anthropic-recommended ``150 → rerank → top_k`` shape.
        """

        start_time = time.time()
        warnings: List[str] = []

        # --- 1. Circuit breaker filter -------------------------------------
        active_kbs: List[str] = []
        for kb_id in kb_ids or []:
            if self._is_circuit_open(kb_id):
                warnings.append(
                    f"KB '{kb_id}' temporarily unavailable (circuit OPEN)."
                )
                logger.warning(
                    f"🚨 [RAGGateway] Skipping {kb_id} due to open circuit."
                )
                continue
            active_kbs.append(kb_id)

        if not active_kbs:
            return KnowledgeResponse(
                query=query,
                fragments=[],
                citations=[],
                total_found=0,
                processing_time_ms=(time.time() - start_time) * 1000,
                retrieval_strategy=strategy,
                warnings=warnings + ["No active KBs available for retrieval."],
                kb_ids=list(kb_ids or []),
            )

        # --- 2. Drive the real pipeline ------------------------------------
        # Anthropic-style staged retrieval: wide recall → cross-encoder
        # rerank → tight injection. Default to ``max(top_k * 20, 100)``
        # capped at 150, which matches the BAAI bge cross-encoder's
        # comfortable batch size on a single-host setup.
        default_recall = min(max(top_k * 20, 100), 150)
        recall_top_k = recall_top_k or getattr(
            settings, "RAG_GATEWAY_RECALL_DEFAULT", default_recall
        )
        search_type = self._coerce_search_type(strategy)

        try:
            run_result = await self.pipeline.run(
                query=query,
                collection_names=active_kbs,
                top_k=recall_top_k,
                top_n=top_k,
                search_type=search_type,
                user_id=user_id,
                is_admin=is_admin,
            )
            # ``RetrievalPipeline.run`` returns a tuple: (final_results, trace_log)
            if isinstance(run_result, tuple):
                docs, trace_log = run_result
            else:  # pragma: no cover — older signature fallback
                docs, trace_log = run_result, []
        except Exception as exc:  # noqa: BLE001
            logger.exception(f"❌ [RAGGateway] Pipeline failed: {exc}")
            for kb_id in active_kbs:
                self._record_failure(kb_id)
            warnings.append(f"Pipeline error: {exc}")
            return KnowledgeResponse(
                query=query,
                fragments=[],
                citations=[],
                total_found=0,
                processing_time_ms=(time.time() - start_time) * 1000,
                retrieval_strategy=strategy,
                warnings=warnings,
                kb_ids=active_kbs,
            )

        # --- 3. Fragment + citation projection -----------------------------
        fragments, citations = self._project(active_kbs, docs)

        contributing_kbs = {f.kb_id for f in fragments}
        for kb_id in active_kbs:
            if kb_id in contributing_kbs:
                self._record_success(kb_id)
            # NOTE: empty-result is not necessarily a failure, so we do
            # not punish the breaker for KBs that simply had no hits.

        # --- 4. Aggregate stats --------------------------------------------
        confidence = (
            max((f.confidence for f in fragments), default=0.0) if fragments else 0.0
        )
        intent = self._extract_intent_from_trace(trace_log)
        elapsed_ms = (time.time() - start_time) * 1000

        response = KnowledgeResponse(
            query=query,
            fragments=fragments,
            citations=citations,
            total_found=len(fragments),
            processing_time_ms=elapsed_ms,
            retrieval_strategy=strategy,
            query_intent=intent,
            confidence=confidence,
            warnings=warnings,
            kb_ids=active_kbs,
            extensions={"trace": trace_log[-20:]} if trace_log else {},
        )

        if max_context_chars:
            response.context_summary = response.to_prompt_context(
                max_chars=max_context_chars
            )

        return response

    async def health(self, kb_id: str) -> KBStatus:
        """Lightweight per-KB health snapshot (no I/O)."""
        cb = self._circuit_breakers.get(kb_id) or {}
        state = cb.get("state", "CLOSED")
        return KBStatus(
            kb_id=kb_id,
            is_healthy=state != "OPEN",
            score_avg=cb.get("score_avg", 0.0),
            last_failure=str(cb.get("last_fail_time", "")) or None,
            circuit_tripped=state == "OPEN",
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @staticmethod
    def _coerce_search_type(strategy: str) -> str:
        mapping = {
            "hybrid": SearchType.HYBRID,
            "vector": SearchType.VECTOR,
            "bm25": SearchType.BM25,
            # Graph strategy still uses hybrid recall under the hood.
            "graph": SearchType.HYBRID,
        }
        return mapping.get(strategy, SearchType.HYBRID)

    @staticmethod
    def _project(
        active_kbs: List[str],
        docs: List[VectorDocument],
    ) -> Tuple[List[KnowledgeFragment], List[Citation]]:
        """Convert pipeline docs to fragments + dedup citations."""
        if not docs:
            return [], []

        raw_scores = [
            float(getattr(d, "score", (d.metadata or {}).get("score", 0.0)) or 0.0)
            for d in docs
        ]
        confidences = _normalise_scores(raw_scores)

        # Single-KB → assume the active one. Multi-KB → trust metadata.
        default_kb = active_kbs[0] if len(active_kbs) == 1 else None

        fragments: List[KnowledgeFragment] = []
        citations: Dict[str, Citation] = {}
        for idx, (doc, conf) in enumerate(zip(docs, confidences)):
            md = doc.metadata or {}
            kb_id = str(
                md.get("kb_id")
                or md.get("collection_name")
                or default_kb
                or (active_kbs[0] if active_kbs else "")
            )
            citation = _make_citation(kb_id, doc, idx)
            citations.setdefault(citation.citation_id, citation)
            fragments.append(
                KnowledgeFragment(
                    content=doc.page_content,
                    metadata=md,
                    score=raw_scores[idx],
                    confidence=conf,
                    kb_id=kb_id,
                    source_id=citation.source_id,
                    chunk_index=citation.chunk_index or idx,
                    citation=citation,
                )
            )
        return fragments, list(citations.values())

    @staticmethod
    def _extract_intent_from_trace(trace_log: List[str]) -> Optional[str]:
        for entry in trace_log:
            if "intent=" in entry:
                try:
                    return entry.split("intent=", 1)[1].split()[0].rstrip(",;")
                except Exception:  # noqa: BLE001
                    return None
        return None

    # ----- circuit breaker --------------------------------------------------
    def _is_circuit_open(self, kb_id: str) -> bool:
        cb = self._circuit_breakers.get(kb_id)
        if not cb:
            return False
        if cb["state"] == "OPEN":
            if time.time() - cb["last_fail_time"] > self.recovery_timeout:
                logger.info(
                    f"🔄 [RAGGateway] Circuit for {kb_id} entering HALF-OPEN."
                )
                cb["state"] = "HALF-OPEN"
                return False
            return True
        return False

    def _record_failure(self, kb_id: str) -> None:
        cb = self._circuit_breakers.setdefault(
            kb_id,
            {
                "fail_count": 0,
                "last_fail_time": 0,
                "state": "CLOSED",
                "score_avg": 0.0,
            },
        )
        cb["fail_count"] += 1
        cb["last_fail_time"] = time.time()
        if cb["fail_count"] >= self.max_failures:
            cb["state"] = "OPEN"
            logger.critical(
                f"🛑 [RAGGateway] Circuit for {kb_id} TRIPPED to OPEN!"
            )

    def _record_success(self, kb_id: str) -> None:
        cb = self._circuit_breakers.get(kb_id)
        if cb:
            cb["fail_count"] = 0
            if cb["state"] != "CLOSED":
                logger.info(
                    f"✅ [RAGGateway] KB {kb_id} healthy. Circuit CLOSED."
                )
            cb["state"] = "CLOSED"


# ----- module-level singleton accessor ------------------------------------
def get_rag_gateway() -> RAGGateway:
    if RAGGateway._instance is None:
        RAGGateway._instance = RAGGateway()
    return RAGGateway._instance
