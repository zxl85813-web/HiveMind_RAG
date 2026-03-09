"""
RAG Gateway - High-level Microservice Governance for Knowledge Retrieval.
Implements Circuit Breaker, Unified Entry, and Strategy Routing.
"""

import asyncio
import time

from loguru import logger

from app.schemas.knowledge_protocol import KnowledgeFragment, KnowledgeResponse
from app.services.retrieval.pipeline import RetrievalPipeline


class RAGGateway:
    """
    The Single Entry Point for all knowledge retrieval requests.
    Handles multiple Knowledge Bases with fault tolerance.
    """

    _instances = {}
    _circuit_breakers = {}  # kb_id -> {fail_count, last_fail_time, state}

    def __init__(self):
        self.pipeline = RetrievalPipeline()
        self.max_failures = 3
        self.recovery_timeout = 60  # seconds

    async def retrieve(
        self, query: str, kb_ids: list[str], top_k: int = 5, strategy: str = "hybrid"
    ) -> KnowledgeResponse:
        start_time = time.time()
        all_fragments = []
        warnings = []

        # 1. Filter out tripped KBs
        active_kbs = []
        for kb_id in kb_ids:
            if self._is_circuit_open(kb_id):
                warnings.append(f"KB '{kb_id}' is temporarily unavailable (Circuit Breaker OPEN).")
                logger.warning(f"🚨 [RAGGateway] Skipping {kb_id} due to open circuit.")
                continue
            active_kbs.append(kb_id)

        if not active_kbs:
            return KnowledgeResponse(
                query=query,
                fragments=[],
                total_found=0,
                processing_time_ms=(time.time() - start_time) * 1000,
                warnings=warnings + ["No active KBs available for retrieval."],
            )

        # 2. Parallel retrieval from active KBs
        # Note: In a real implementation, we'd use the RetrievalPipeline's internal logic
        tasks = [self._retrieve_from_single_kb(query, kb_id, top_k) for kb_id in active_kbs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(results):
            kb_id = active_kbs[i]
            if isinstance(res, Exception):
                self._record_failure(kb_id)
                warnings.append(f"Retrieval failed for KB '{kb_id}': {res!s}")
                logger.error(f"❌ [RAGGateway] KB {kb_id} failed: {res}")
            else:
                self._record_success(kb_id)
                all_fragments.extend(res)

        # 3. Global Reranking / Post-processing
        # (Simplified for now: just sort by score)
        all_fragments.sort(key=lambda x: x.score, reverse=True)

        return KnowledgeResponse(
            query=query,
            fragments=all_fragments[: top_k * len(active_kbs)],
            total_found=len(all_fragments),
            processing_time_ms=(time.time() - start_time) * 1000,
            retrieval_strategy=strategy,
            warnings=warnings,
        )

    async def _retrieve_from_single_kb(self, query: str, kb_id: str, top_k: int) -> list[KnowledgeFragment]:
        """Wrap the lower-level retrieval service."""
        # This is a simulation or integration with your existing VectorStore/SearchService
        # For now, we simulate success
        await asyncio.sleep(0.05)  # Simulate latency
        return [
            KnowledgeFragment(
                content=f"Sample fragment from {kb_id} for query '{query}'",
                kb_id=kb_id,
                source_id="doc_001",
                chunk_index=0,
                score=0.85,
            )
        ]

    def _is_circuit_open(self, kb_id: str) -> bool:
        cb = self._circuit_breakers.get(kb_id)
        if not cb:
            return False

        if cb["state"] == "OPEN":
            if time.time() - cb["last_fail_time"] > self.recovery_timeout:
                logger.info(f"🔄 [RAGGateway] Circuit for {kb_id} entering HALF-OPEN state.")
                cb["state"] = "HALF-OPEN"
                return False
            return True
        return False

    def _record_failure(self, kb_id: str):
        cb = self._circuit_breakers.setdefault(kb_id, {"fail_count": 0, "last_fail_time": 0, "state": "CLOSED"})
        cb["fail_count"] += 1
        cb["last_fail_time"] = time.time()
        if cb["fail_count"] >= self.max_failures:
            cb["state"] = "OPEN"
            logger.critical(f"🛑 [RAGGateway] Circuit for {kb_id} TRIPPED to OPEN!")

    def _record_success(self, kb_id: str):
        if kb_id in self._circuit_breakers:
            self._circuit_breakers[kb_id]["fail_count"] = 0
            self._circuit_breakers[kb_id]["state"] = "CLOSED"
            logger.info(f"✅ [RAGGateway] KB {kb_id} is healthy. Circuit CLOSED.")
