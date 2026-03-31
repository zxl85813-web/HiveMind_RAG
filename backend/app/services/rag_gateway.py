"""
RAG Gateway - High-level Microservice Governance for Knowledge Retrieval.
Implements Circuit Breaker, Unified Entry, and Strategy Routing.
"""

import asyncio
import time
from typing import ClassVar

from loguru import logger

from app.schemas.knowledge_protocol import KnowledgeFragment, KnowledgeResponse
from app.services.dependency_circuit_breaker import breaker_manager
from app.services.observability_service import fire_and_forget_trace
from app.services.retrieval.read_service import get_retrieval_read_service
from app.services.retrieval.pipeline import RetrievalPipeline
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
        # Use the real RetrievalReadService to ensure fact fidelity and ACL.
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
                # Ensure we handle list of KnowledgeFragment
                all_fragments.extend(res)

        # 3. Global Reranking / Post-processing
        # (Simplified for now: just sort by score)
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
            step_traces=warnings,
            is_error=bool(warnings),
        )

        return KnowledgeResponse(
            query=query,
            fragments=final_fragments,
            total_found=len(all_fragments),
            processing_time_ms=(time.time() - start_time) * 1000,
            retrieval_strategy=strategy,
            warnings=warnings,
        )

    async def retrieve_for_development(
        self,
        query: str,
        kb_ids: list[str],
        top_k: int = 5,
        strategy: str = "hybrid",
        include_graph: bool = True,
    ) -> KnowledgeResponse:
        """
        Development-oriented retrieval interface for Agent workflows.
        Aggregates vector retrieval and Hybrid GraphRAG contextual hints into one response.
        """
        start_time = time.time()
        warnings: list[str] = []
        merged_fragments: list[KnowledgeFragment] = []
        vector_sources = []

        if kb_ids:
            vector_part = await self.retrieve(query=query, kb_ids=kb_ids, top_k=top_k, strategy=strategy)
            merged_fragments.extend(vector_part.fragments)
            warnings.extend(vector_part.warnings)
            
            # Extract filenames/paths from vector chunks to guide Graph traversal
            for frag in vector_part.fragments:
                src = frag.metadata.get("source") or frag.metadata.get("filename") or frag.source_id
                if src:
                    # Clean up path to get just the filename
                    basename = src.split("/")[-1].split("\\")[-1]
                    vector_sources.append(basename)
        else:
            warnings.append("No kb_ids provided; vector retrieval skipped.")

        if include_graph:
            try:
                from app.core.graph_store import get_graph_store

                store = get_graph_store()
                if store.driver:
                    # Hybrid GraphRAG: Find nodes matching the query OR the vector matches, and expand 1 hop.
                    cypher = """
                    WITH $query AS q, $sources AS sources
                    
                    MATCH (n)
                    WHERE toLower(coalesce(n.name, n.id, n.path, "")) CONTAINS toLower(q)
                       OR coalesce(n.name, n.id, "") IN sources
                       OR split(coalesce(n.path, ""), "/")[-1] IN sources
                       OR split(coalesce(n.path, ""), "\\\\")[-1] IN sources
                    
                    MATCH (n)-[r]-(m)
                    WHERE type(r) IN ['MAPPED_TO_CODE', 'DEFINES', 'DEPENDS_ON', 'EXPOSES_API', 
                                      'DEFINES_MODEL', 'USES_CONTRACT', 'ADDRESSES', 'VERIFIES', 'DEFINES_CONTRACT']
                    
                    RETURN DISTINCT 
                           coalesce(n.name, n.id, n.path, "") AS source,
                           type(r) AS relation,
                           coalesce(m.name, m.id, m.path, "") AS target,
                           labels(n)[0] AS sourceLabel,
                           labels(m)[0] AS targetLabel
                    LIMIT $limit
                    """
                    records = await breaker_manager.execute(
                        "neo4j",
                        lambda: asyncio.to_thread(store.query, cypher, {"query": query, "sources": vector_sources, "limit": top_k * 3}),
                    )
                    
                    for idx, rec in enumerate(records):
                        src = rec.get("source") or "unknown"
                        rel = rec.get("relation") or "RELATED"
                        tgt = rec.get("target") or "unknown"
                        src_label = rec.get("sourceLabel") or "Node"
                        tgt_label = rec.get("targetLabel") or "Node"
                        
                        merged_fragments.append(
                            KnowledgeFragment(
                                content=f"[GraphRAG Context] {src_label}({src}) -[{rel}]-> {tgt_label}({tgt})",
                                metadata={"source": "neo4j_hybrid_graphrag", "kind": "graph_hint"},
                                score=0.95,  # High score to prioritize architecture hints
                                kb_id="graph",
                                source_id=f"graph:{src}->{tgt}",
                                chunk_index=0,
                            )
                        )
                else:
                    warnings.append("Neo4j graph store is not available.")
            except Exception as e:
                logger.warning(f"[RAGGateway] Graph retrieval failed: {e}")
                warnings.append(f"Graph retrieval failed: {e!s}")

        merged_fragments.sort(key=lambda x: x.score, reverse=True)
        # Cap the max items returned
        max_items = max(top_k + (len(records) if 'records' in locals() else 0), top_k)

        return KnowledgeResponse(
            query=query,
            fragments=merged_fragments[:max_items],
            total_found=len(merged_fragments),
            processing_time_ms=(time.time() - start_time) * 1000,
            retrieval_strategy="hybrid-graphrag",
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
