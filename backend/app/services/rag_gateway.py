"""
RAG Gateway - High-level Microservice Governance for Knowledge Retrieval.
Implements Circuit Breaker, Unified Entry, and Strategy Routing.
"""

import asyncio
import time
from typing import ClassVar

from app.core.logging import get_trace_logger

logger = get_trace_logger("services.rag_gateway")

from app.schemas.knowledge_protocol import KnowledgeFragment, KnowledgeResponse
from app.services.dependency_circuit_breaker import breaker_manager
from app.services.observability_service import fire_and_forget_trace
from app.services.retrieval.pipeline import RetrievalPipeline
from app.services.retrieval.read_service import get_retrieval_read_service
from app.services.service_governance import choose_topology_path


class RAGGateway:
    """
    The Single Entry Point for all knowledge retrieval requests.
    Handles multiple Knowledge Bases with fault tolerance.
    """

    _instances: ClassVar[dict[str, "RAGGateway"]] = {}
    _circuit_breakers: ClassVar[dict[str, dict[str, float | int | str]]] = (
        {}
    )  # kb_id -> {fail_count, last_fail_time, state}

    def __init__(self):
        self.pipeline = RetrievalPipeline()
        self.read_service = get_retrieval_read_service()
        self.max_failures = 3
        self.recovery_timeout = 60  # seconds

    async def retrieve(
        self,
        query: str,
        kb_ids: list[str],
        top_k: int = 5,
        strategy: str = "hybrid",
        user_id: str | None = None,
    ) -> KnowledgeResponse:
        start_time = time.time()
        all_fragments = []
        warnings = []

        # Phase 5 / TASK-SG-001:
        # Decide whether this request should use split path (gray rollout) or stay monolith.
        topo = choose_topology_path(user_id=user_id, query=query)
        logger.debug(
            "[ServiceGovernance] mode={} path={} gray={}%, strategy={}",
            topo.mode,
            topo.path,
            topo.gray_percent,
            strategy,
        )

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
                warnings=[*warnings, "No active KBs available for retrieval."],
            )

        # 2. Parallel retrieval from active KBs
        all_step_traces = []
        tasks = [
            breaker_manager.execute(
                "es",
                lambda kb_id=kb_id: self.read_service.retrieve_from_kb(
                    query=query,
                    kb_id=kb_id,
                    top_k=top_k,
                    search_type=strategy,
                    user_id=user_id,
                ),
            )
            for kb_id in active_kbs
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, res in enumerate(results):
            kb_id = active_kbs[i]
            if isinstance(res, Exception):
                self._record_failure(kb_id)
                warnings.append(f"Retrieval failed for KB '{kb_id}': {res!s}")
                logger.error(f"❌ [RAGGateway] KB {kb_id} failed: {res}")
            else:
                self._record_success(kb_id)
                # handle (fragments, trace_log) tuple
                fragments, trace_log = res
                all_fragments.extend(fragments)
                all_step_traces.extend(trace_log)

        # 3. Global Reranking / Post-processing
        all_fragments.sort(key=lambda x: x.score, reverse=True)
        final_fragments = all_fragments[: top_k * len(active_kbs)]

        # 4. Fire-and-forget observability trace
        retrieved_doc_ids = list({f.source_id for f in final_fragments})
        fire_and_forget_trace(
            query=query,
            kb_ids=kb_ids,
            retrieval_strategy=strategy,
            total_found=len(all_fragments),
            returned_count=len(final_fragments),
            latency_ms=(time.time() - start_time) * 1000,
            retrieved_doc_ids=retrieved_doc_ids,
            step_traces=list(set(all_step_traces)) if all_step_traces else warnings,
            is_error=bool(warnings),
        )

        return KnowledgeResponse(
            query=query,
            fragments=final_fragments,
            total_found=len(all_fragments),
            processing_time_ms=(time.time() - start_time) * 1000,
            retrieval_strategy=strategy,
            warnings=warnings,
            step_traces=all_step_traces
        )

    async def prefetch(
        self,
        query: str,
        kb_ids: list[str],
        user_id: str | None = None
    ) -> None:
        """
        [M5.2.1] Speculative Prefetch: Triggered by Intent Scaffolding.
        Warms up caches and embedding services.
        Results are stored in the transient intent cache.
        """
        logger.info(f"🛰️ [Prefetch] Initiating pre-warmup for query: '{query[:30]}...'")
        
        # Fire-and-forget background retrieval
        try:
            # For now, we perform a standard retrieve
            result = await self.retrieve(query=query, kb_ids=kb_ids, top_k=5, user_id=user_id)
            
            # 🛰️ [M5.2.1] Link to IntentCache
            from app.services.cache_service import CacheService
            CacheService.set_intent_cache(
                session_id=user_id or "default",
                data={
                   "context_data": "\n\n".join([f.content for f in result.fragments]),
                   "retrieved_docs": [f.dict() for f in result.fragments],
                   "retrieval_trace": result.step_traces
                }
            )
            logger.debug(f"🛰️ [Prefetch] Warmup complete. Results cached in IntentCache.")
        except Exception as e:
            logger.warning(f"Prefetch failed (silent): {e}")

    async def retrieve_for_development(
        self,
        query: str,
        kb_ids: list[str],
        top_k: int = 5,
        strategy: str = "hybrid",
        include_graph: bool = True,
        user_id: str | None = None,
    ) -> KnowledgeResponse:
        """
        [M5.3.1] Refined Development Retrieval Gateway.
        Unified interface utilizing the RetrievalPipeline with specific variant.
        """
        start_time = time.time()
        
        # Use the pipeline!
        variant = "default" if include_graph else "ab_no_graph"
        
        # 🧪 [Audit]: Injected trace context for development flows
        logger.info(f"🛰️ [RAGGateway] Development retrieval for '{query[:20]}...' (graph={include_graph})")
        
        fragments, trace_log = await self.pipeline.run(
            query=query,
            collection_names=kb_ids,
            top_k=top_k * 2, # Recall more for expansion
            top_n=top_k,
            search_type=strategy,
            user_id=user_id,
            variant=variant
        )
        
        latency = (time.time() - start_time) * 1000
        
        return KnowledgeResponse(
            query=query,
            fragments=fragments,
            total_found=len(fragments),
            processing_time_ms=latency,
            retrieval_strategy=f"pipeline-{variant}",
            step_traces=trace_log
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
