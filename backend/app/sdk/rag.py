"""
HiveMindRAG — the public facade for the RAG platform capability.

Wraps :class:`app.services.rag_gateway.RAGGateway` so external callers can do::

    from app.sdk import HiveMindRAG
    rag = HiveMindRAG()
    result = await rag.retrieve("query", kb_ids=["kb_1", "kb_2"], top_k=5)
    for fragment in result.fragments:
        print(fragment.score, fragment.content)

Why a facade?
-------------
* Stable import path — internal refactors of ``app.services`` won't break
  external consumers.
* One place to add cross-cutting concerns (auth, telemetry, rate limit) when
  this evolves into a real published SDK.
* Mirrors the FastAPI surface so a future generated REST/HTTP client can be
  swapped in transparently.
"""

from __future__ import annotations

from typing import Sequence

from app.schemas.knowledge_protocol import KnowledgeResponse
from app.services.rag_gateway import RAGGateway

# Re-export under a name that reads naturally at the SDK boundary.
RAGRetrievalResult = KnowledgeResponse


class HiveMindRAG:
    """High-level entry point for knowledge retrieval."""

    def __init__(self, gateway: RAGGateway | None = None) -> None:
        # Allow injection for testing; default to a fresh gateway instance.
        self._gateway = gateway or RAGGateway()

    async def retrieve(
        self,
        query: str,
        kb_ids: Sequence[str],
        *,
        top_k: int = 5,
        strategy: str = "hybrid",
    ) -> RAGRetrievalResult:
        """Retrieve relevant fragments from one or more knowledge bases.

        Parameters
        ----------
        query:
            Natural-language question or search phrase.
        kb_ids:
            Identifiers of the knowledge bases to search. Each KB is queried
            in parallel; failing KBs are isolated by the gateway's circuit
            breaker and reported via ``result.warnings``.
        top_k:
            Maximum fragments to keep per KB before global re-ranking.
        strategy:
            Retrieval strategy hint forwarded to the underlying pipeline
            (``"hybrid"`` / ``"vector"`` / ``"keyword"``).

        Returns
        -------
        :class:`RAGRetrievalResult`
            A :class:`~app.schemas.knowledge_protocol.KnowledgeResponse`
            containing fragments, timings, strategy used, and warnings.
        """
        return await self._gateway.retrieve(
            query=query,
            kb_ids=list(kb_ids),
            top_k=top_k,
            strategy=strategy,
        )

    @property
    def gateway(self) -> RAGGateway:
        """Escape hatch for advanced callers that need the raw gateway."""
        return self._gateway
