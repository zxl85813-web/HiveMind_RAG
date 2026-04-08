import abc

from loguru import logger

from app.core.database import async_session_factory
from app.core.reranker import get_reranker
from app.core.vector_store import get_vector_store

from .protocol import RetrievalContext


class BaseRetrievalStep(abc.ABC):
    @abc.abstractmethod
    async def execute(self, ctx: RetrievalContext):
        """Execute step and update context"""
        pass


class QueryPreProcessingStep(BaseRetrievalStep):
    """
    ARAG: Analyze query, expand intent, normalize text.
    Similar to 'IngestionParser'.
    """

    async def execute(self, ctx: RetrievalContext):
        from pydantic import BaseModel, Field

        from app.core.algorithms.classification import classifier_service

        ctx.expanded_queries = [ctx.query]

        if len(ctx.query) < 5:
            ctx.log("QueryProc", f"Query '{ctx.query}' is short, skipping advanced analysis.")
            return

        class QueryIntentExtraction(BaseModel):
            intent: str = Field(default="fact", description="Must be one of: 'fact', 'comparison', 'summary', 'action'")
            rewritten_query: str = Field(..., description="Rewrite the original query to be more specific, objective, and clear for vector search.")
            hyde_document: str | None = Field(default=None, description="A hypothetical short answer to the query, 1-2 positive sentences (HyDE technique). Keep it concise.")
            keywords: list[str] = Field(default_factory=list, description="Key entities, topics, or exact terms")

        prompt = f"Analyze the user's query: '{ctx.query}'"

        try:
            analysis = await classifier_service.extract_model(
                text=prompt,
                target_model=QueryIntentExtraction,
                instruction="You are an advanced query analyzer for a RAG system. Output in JSON."
            )

            ctx.query_intent = analysis.intent
            ctx.rewritten_query = analysis.rewritten_query
            ctx.hyde_document = analysis.hyde_document
            ctx.keywords = analysis.keywords

            if ctx.rewritten_query and ctx.rewritten_query != ctx.query:
                ctx.expanded_queries.append(ctx.rewritten_query)
            if ctx.hyde_document:
                ctx.expanded_queries.append(ctx.hyde_document)

            ctx.log(
                "QueryProc",
                f"Intent: {ctx.query_intent}, Expanded: {len(ctx.expanded_queries)} "
                f"variations. Keywords: {ctx.keywords}",
            )
        except Exception as e:
            ctx.log("QueryProc", f"Query analysis failed: {e}. Fallback to basic term.")


class HybridRetrievalStep(BaseRetrievalStep):
    """
    Recall Phase (Retrieval): Retrieve candidates from VectorStore.
    Equivalent to 'Ingestion' but reversed (Store -> Memory).
    """

    async def execute(self, ctx: RetrievalContext):
        import asyncio

        store = get_vector_store()

        # Create tasks for all combinations of queries and KBs
        tasks = []
        for q in ctx.expanded_queries:
            for kb_id in ctx.kb_ids:
                tasks.append(store.search(query=q, search_type=ctx.search_type, k=ctx.top_k, collection_name=kb_id))

        if not tasks:
            ctx.candidates = []
            return

        # Execute parallel searches
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            all_docs = []
            for _i, res in enumerate(results):
                if isinstance(res, Exception):
                    ctx.log("Retrieval", f"Parallel task failed: {res}")
                    continue
                all_docs.extend(res)
        except Exception as e:
            ctx.log("Retrieval", f"Parallel retrieval failed: {e}")
            all_docs = []

        # Dedup by content
        unique_docs = {}
        for d in all_docs:
            if d.page_content not in unique_docs:
                unique_docs[d.page_content] = d

        ctx.candidates = list(unique_docs.values())
        ctx.log("Retrieval", f"Found {len(ctx.candidates)} unique candidates from {len(ctx.kb_ids)} KBs (Parallelized)")


class RerankingStep(BaseRetrievalStep):
    """
    Precision Phase (Ranking): Re-rank candidates using Cross-Encoder.
    This ensures Top N results are highly relevant.
    """

    async def execute(self, ctx: RetrievalContext):
        if not ctx.candidates:
            ctx.final_results = []
            return

        reranker = get_reranker()

        # Rerank
        ranked = await reranker.rerank(query=ctx.query, documents=ctx.candidates, top_n=ctx.top_n)

        # --- Lost in the Middle Optimization (Phase 4) ---
        # Reorder ranked results: [Most relevant, ..., Least relevant] -> [1, 3, 5, ..., 6, 4, 2]
        # This puts high-rank documents at both the beginning and end of the context.
        if len(ranked) > 2:
            left = ranked[::2]
            right = ranked[1::2]
            right.reverse()
            ranked = left + right
            ctx.log("Rerank", "Reordered documents for 'Lost in the Middle' optimization.")

        ctx.final_results = ranked
        ctx.log("Rerank", f"Selected top {len(ranked)} documents")


class ParentChunkExpansionStep(BaseRetrievalStep):
    """
    Parent-Child Chunking Expansion Phase.
    If a retrieved vector document has a 'parent_chunk_id', we fetch the parent chunk
    content from the SQL database and substitute it to provide broader context to the LLM.
    """

    async def execute(self, ctx: RetrievalContext):
        if not ctx.final_results:
            return

        from app.models.knowledge import DocumentChunk

        async with async_session_factory() as session:
            for doc in ctx.final_results:
                parent_id = doc.metadata.get("parent_chunk_id")
                if parent_id:
                    # Fetch parent chunk
                    parent = await session.get(DocumentChunk, parent_id)
                    if not parent or not parent.content:
                        continue

                    # 🔒 Cascading Security Check (TASK-SG-003):
                    # If the parent chunk belongs to a DIFFERENT document, must re-verify ACL.
                    parent_doc_id = parent.document_id
                    original_doc_id = doc.metadata.get("document_id")

                    if parent_doc_id != original_doc_id:
                        # Check cache first
                        allowed = ctx.permission_cache.get(parent_doc_id)
                        if allowed is None:
                            # Fresh check (e.g. if the parent doc wasn't in original candidates)
                            from app.auth.permissions import has_document_permission
                            allowed = await has_document_permission(session, ctx.user_model, parent_doc_id, "read")
                            ctx.permission_cache[parent_doc_id] = allowed

                        if not allowed:
                            ctx.log("ParentExpansion", f"🚨 Blocked Shadow Leak! User {ctx.user_id} tried to expand to doc {parent_doc_id}")
                            continue

                    # Safe to expand
                    original_length = len(doc.page_content)
                    doc.page_content = parent.content
                    ctx.log(
                        "ParentExpansion",
                        f"Expanded chunk '{doc.metadata.get('chunk_id')}' "
                        f"from {original_length} to {len(parent.content)} chars.",
                    )
                    doc.metadata["expanded_from_parent"] = True


class GraphRetrievalStep(BaseRetrievalStep):
    """
    Graph Traversal Phase: Retrieve connected nodes from Neo4j to enrich context.
    """

    async def execute(self, ctx: RetrievalContext):
        from app.core.graph_store import get_graph_store

        store = get_graph_store()

        if not store.driver:
            return

        # 1. Evaluate Semantic Route to determine whether graph lookup is needed
        try:
            from app.core.algorithms.routing import Route, semantic_router

            graph_route = Route(
                name="graph",
                utterances=[
                    "Who is connected to whom?",
                    "What is the relationship between X and Y?",
                    "Show me all the people involved in the project.",
                    "Explain the structure of the organization.",
                    "What events occurred with this person?"
                ]
            )

            vector_route = Route(
                name="vector",
                utterances=[
                    "What is the content of the policy?",
                    "Summarize the document.",
                    "How do I install the software?",
                    "Explain the concept of this term.",
                    "Give me the facts from the report."
                ]
            )

            decision = await semantic_router.route(ctx.query, [graph_route, vector_route], threshold=0.1)
            ctx.log("GraphRetrieval", f"Semantic Router decision: {decision.target_node} ({decision.confidence:.2f})")

            if decision.target_node != "graph":
                ctx.log("GraphRetrieval", "Skipped graph traversal due to low semantic match.")
                return
        except Exception as e:
            ctx.log("GraphRetrieval", f"Warning: semantic routing failed, proceeding to extraction: {e}")

        # 2. Extract entities from the query to know what to lookup in the graph
        # For MVP, we extract entities directly using GraphExtractor
        try:
            from app.services.knowledge.graph_extractor import GraphExtractor

            extractor = GraphExtractor()
            nodes, _ = await extractor.extract_knowledge_graph(ctx.query, "query_context")
            entity_names = [n.get("id") for n in nodes if n.get("id")]

            if not entity_names:
                return

            graph_facts = []
            # 3. Lookup related edges in the graph for each KB
            for kb_id in ctx.kb_ids:
                for entity in entity_names:
                    # Basic neighborhood query
                    cypher = """
                    MATCH (n {kb_id: $kb_id})-[r]-(m)
                    WHERE n.id CONTAINS $entity OR n.name CONTAINS $entity
                    RETURN n.id AS source, type(r) AS rel, m.id AS target, getattr(r, 'description', '') AS desc
                    LIMIT 20
                    """
                    results = store.query(cypher, {"entity": entity, "kb_id": kb_id})
                    for row in results:
                        desc = row.get("desc", "") or ""
                        fact = f"Graph Fact: {row['source']} -> {row['rel']} -> {row['target']} ({desc})"
                        graph_facts.append(fact)

            if graph_facts:
                # Remove duplicates
                graph_facts = list(set(graph_facts))
                # Create a mock VectorDocument to hold graph context
                from app.core.vector_store import VectorDocument

                graph_doc = VectorDocument(
                    page_content="[Knowledge Graph Context]\n" + "\n".join(graph_facts),
                    metadata={"source": "GraphRAG", "type": "graph", "entities": entity_names},
                )
                # Ensure context has candidates initialized
                if not hasattr(ctx, "candidates") or ctx.candidates is None:
                    ctx.candidates = []
                # Prepend graph context so it has high priority in hybrid retrieval
                ctx.candidates.insert(0, graph_doc)
                ctx.graph_facts.extend(graph_facts)
                ctx.log("GraphRetrieval", f"Injected {len(graph_facts)} graph facts for entities: {entity_names}")
        except Exception as e:
            ctx.log("GraphRetrieval", f"Graph retrieval failed: {e}")


class AclFilterStep(BaseRetrievalStep):
    """
    ACL Phase: Check document permissions against the current user before returning them.
    (M2.2 Security & Data Desensitization)
    """

    async def execute(self, ctx: RetrievalContext):
        if not ctx.candidates:
            return

        # If user is admin or script, bypass ACL checks
        if ctx.is_admin or not ctx.user_id:
            ctx.log("ACL", "Bypassing ACL due to admin or system context.")
            return

        from app.auth.permissions import has_document_permission
        from app.models.chat import User

        allowed_candidates = []
        rejected = 0
        async with async_session_factory() as session:
            # Load user for Role/Dept checks
            user = await session.get(User, ctx.user_id)
            if not user:
                ctx.log("ACL", f"User {ctx.user_id} not found, rejecting all candidates.")
                ctx.candidates = []
                return

            # Cache the user model for subsequent steps (e.g. expansion)
            ctx.user_model = user

            for doc in ctx.candidates:
                doc_id = doc.metadata.get("document_id")
                if not doc_id:
                    allowed_candidates.append(doc)
                    continue

                # Default Deny (ARM-P0-2): Any document retrieved must pass an explicit has_document_permission check.
                # If no records exist in DocumentPermission, has_document_permission returns False.
                is_allowed = await has_document_permission(session, user, doc_id, "read")
                # Cache decision for expansion step
                ctx.permission_cache[doc_id] = is_allowed

                if is_allowed:
                    allowed_candidates.append(doc)
                else:
                    # Audit Logging (ARM-P0-3)
                    logger.warning(
                        f"🔒 [Audit] Access DENIED | User: {ctx.user_id} | Doc: {doc_id} | Reason: doc_acl_denied"
                    )
                    ctx.log("ACL", f"Document {doc_id} filtered out (Reason: doc_acl_denied)")
                    rejected += 1

        ctx.candidates = allowed_candidates
        ctx.log(
            "ACL",
            f"Filtered out {rejected} documents for user {user.username} "
            f"(Role: {user.role}, Dept: {user.department_id})",
        )


class PromptInjectionFilterStep(BaseRetrievalStep):
    """
    Security Phase: Prevent context injection attacks.
    Scan chunks for malicious instructions like 'Ignore previous instructions'.
    """

    async def execute(self, ctx: RetrievalContext):
        if not ctx.final_results:
            return

        clean_results = []
        suspicious = 0
        malicious_patterns = [
            "ignore previous instructions",
            "system prompt",
            "you are now",
            "forget everything",
            "do not follow",
        ]

        for doc in ctx.final_results:
            content = doc.page_content.lower()
            if any(p in content for p in malicious_patterns):
                suspicious += 1
            else:
                clean_results.append(doc)

        ctx.final_results = clean_results


class ContextualCompressionStep(BaseRetrievalStep):
    """
    Compression Phase: Reduce Token usage by keeping only relevant sentences
    and trimming based on contextual budgets (M2.1H Advanced Compaction).
    """

    async def execute(self, ctx: RetrievalContext):
        if not ctx.final_results:
            return

        import re
        from app.core.config import settings

        # --- ARAG-002: Dynamic Context Budgeting ---
        # Calculate allowed characters based on budget ratios (assuming ~4 chars per token)
        total_window = settings.CONTEXT_WINDOW_LIMIT
        rag_ratio = settings.BUDGET_RAG_RATIO # Usually 0.45
        max_rag_chars = int(total_window * rag_ratio * 4) 
        
        ctx.log("Compression", f"Target RAG Budget: {int(total_window * rag_ratio)} tokens (~{max_rag_chars} chars)")

        # Get keywords from QueryPreProcessingStep if available
        keywords = set(getattr(ctx, "keywords", []))
        if not keywords:
            keywords = {w.strip().lower() for w in re.split(r"[,.\s]+", ctx.query) if len(w.strip()) > 2}

        compressed_results = []
        current_total_chars = 0
        reduction_total = 0

        # Process results in order of relevance (Rerank priority)
        for i, doc in enumerate(ctx.final_results):
            original_text = doc.page_content
            
            # 💡 Tiered Preservation Policy:
            # - Top 3 results: Preserve more carefully
            # - Others: Aggressive keyword filtering
            is_top_tier = i < 3
            
            # Split into sentences
            sentences = re.split(r"(?<=[。？！.?!])\s+", original_text)
            relevant_sentences = []
            
            for sent in sentences:
                sent_lower = sent.lower()
                # Score sentence based on keyword density
                msg_score = sum(1 for kw in keywords if kw in sent_lower)
                
                if msg_score > 0 or (is_top_tier and len(relevant_sentences) < 2):
                    relevant_sentences.append(sent)

            # If nothing matched even for top tier, fallback to snippet
            if not relevant_sentences and sentences:
                relevant_sentences = sentences[:2]

            new_content = " ".join(relevant_sentences)
            
            # Check if adding this doc exceeds the RAG budget
            if current_total_chars + len(new_content) > max_rag_chars:
                if i < 5: # Force include at least top 5 even if slightly over
                    new_content = new_content[:2000] + "... [TRUNCATED]"
                else:
                    ctx.log("Compression", f"✂️ Budget Exceeded. Dropping remaining {len(ctx.final_results) - i} lower-rank docs.")
                    break

            reduction_total += len(original_text) - len(new_content)
            current_total_chars += len(new_content)
            
            doc.page_content = new_content
            doc.metadata["compressed"] = True
            compressed_results.append(doc)

        ctx.final_results = compressed_results
        ctx.log("Compression", f"Final context: {len(compressed_results)} docs, {current_total_chars} chars. (Saved {reduction_total} chars)")

class TruthAlignmentStep(BaseRetrievalStep):
    """
    Governance Phase: Align Graph facts with Vector chunks to ensure consistency.
    (GOV-001 Truth Alignment — M2.3.1)

    When conflicts are detected:
    - Conflicting graph facts are pruned from ctx.graph_facts.
    - GraphRAG candidate blocks are removed from ctx.candidates to prevent
      contaminating the reranker with disputed content.
    - ctx.alignment_report is populated so the final Prompt Engine can surface
      the governance warning to the LLM.
    """

    async def execute(self, ctx: RetrievalContext):
        if not ctx.graph_facts or not ctx.candidates:
            return

        from app.core.algorithms.alignment import truth_alignment_service

        vector_contents = [d.page_content for d in ctx.candidates if d.metadata.get("source") != "GraphRAG"]
        if not vector_contents:
            return

        try:
            decision = await truth_alignment_service.align(ctx.graph_facts, vector_contents)

            if not decision.is_consistent:
                # ── GOV-001 Action 1: prune conflicting graph facts ──────────
                if decision.conflicting_entities:
                    original_count = len(ctx.graph_facts)
                    ctx.graph_facts = [
                        f for f in ctx.graph_facts
                        if not any(ent.lower() in f.lower() for ent in decision.conflicting_entities)
                    ]
                    pruned = original_count - len(ctx.graph_facts)
                    if pruned:
                        ctx.log("Alignment", f"Pruned {pruned} conflicting graph facts (entities: {decision.conflicting_entities})")

                # ── GOV-001 Action 2: remove GraphRAG candidate blocks ───────
                pre_count = len(ctx.candidates)
                ctx.candidates = [d for d in ctx.candidates if d.metadata.get("source") != "GraphRAG"]
                removed_docs = pre_count - len(ctx.candidates)
                if removed_docs:
                    ctx.log("Alignment", f"Removed {removed_docs} GraphRAG candidate block(s) due to conflict.")

                # ── GOV-001 Action 3: structured report for LLM context ──────
                entities_str = ", ".join(decision.conflicting_entities) or "unspecified"
                ctx.alignment_report = (
                    f"[Truth Alignment — {decision.severity.upper()} CONFLICT]\n"
                    f"{decision.summary}\n"
                    f"Conflicting entities: {entities_str}\n"
                    f"Note: Conflicting graph facts have been removed from context."
                )
                ctx.log("Alignment", f"🚨 CONFLICT DETECTED ({decision.severity}): {len(decision.conflicts)} issues.")
            else:
                ctx.alignment_report = None
                ctx.log("Alignment", "✅ Facts aligned (Graph vs Vector).")

            if decision.reinforcements:
                ctx.log("Alignment", f"Strong reinforcement: {len(decision.reinforcements)} facts confirmed by both.")
        except Exception as e:
            ctx.log("Alignment", f"Alignment failed: {e}")


class RRFHybridStep(BaseRetrievalStep):
    """
    2.1H Contextual BM25 Integration — Explicit BM25 + Vector with RRF Fusion.

    Runs BM25 (keyword) and Vector (semantic) searches as separate passes, then
    combines results using Reciprocal Rank Fusion (RRF) for maximum Recall@N.

    This replaces the single-pass HybridRetrievalStep for the high-precision path.
    RRF formula: score(d) = Σ 1/(k + rank_i) where k=60 (standard).
    """

    def __init__(self, rrf_k: int = 60) -> None:
        self.rrf_k = rrf_k

    async def execute(self, ctx: RetrievalContext) -> None:
        import asyncio

        from app.core.vector_store import SearchType, get_vector_store

        store = get_vector_store()
        queries = ctx.expanded_queries or [ctx.query]
        k = self.rrf_k

        # Build parallel tasks: BM25 and Vector per (query, kb) combination
        bm25_tasks = [
            store.search(q, SearchType.BM25, ctx.top_k, kb)
            for q in queries
            for kb in ctx.kb_ids
        ]
        vector_tasks = [
            store.search(q, SearchType.VECTOR, ctx.top_k, kb)
            for q in queries
            for kb in ctx.kb_ids
        ]

        all_tasks = bm25_tasks + vector_tasks
        all_results = await asyncio.gather(*all_tasks, return_exceptions=True)

        bm25_lists = all_results[: len(bm25_tasks)]
        vector_lists = all_results[len(bm25_tasks) :]

        # --- RRF Fusion ---
        rrf_scores: dict[str, float] = {}
        doc_index: dict[str, object] = {}

        for result_list in (bm25_lists, vector_lists):
            for maybe_docs in result_list:
                if isinstance(maybe_docs, Exception):
                    ctx.log("RRFHybrid", f"Partial retrieval error: {maybe_docs}")
                    continue
                for rank, doc in enumerate(maybe_docs):
                    key = doc.page_content[:120]   # dedup key (first 120 chars)
                    doc_index[key] = doc
                    rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (k + rank + 1)

        # Sort by descending RRF score and trim to top_k
        sorted_keys = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)
        ctx.candidates = [doc_index[kk] for kk in sorted_keys[: ctx.top_k]]

        ctx.log(
            "RRFHybrid",
            f"BM25+Vector RRF fusion: {len(sorted_keys)} unique docs → top {len(ctx.candidates)} candidates.",
        )


class SearchSubagentsStep(BaseRetrievalStep):
    """
    2.1H Search Subagents — Parallel sub-query retrieval.

    When the QueryPreProcessingStep produces decomposed sub-queries (ctx.sub_queries),
    this step launches a mini-retrieval per sub-query in parallel and merges the results
    into ctx.candidates before the reranker.

    This handles large, high-ambiguity knowledge searches where a single query would
    miss diverse relevant chunks.
    """

    async def execute(self, ctx: RetrievalContext) -> None:
        import asyncio

        from app.core.vector_store import SearchType, get_vector_store

        sub_queries = getattr(ctx, "sub_queries", [])
        if not sub_queries or len(sub_queries) <= 1:
            # Nothing to parallelize; HybridRetrievalStep / RRFHybridStep covers this
            return

        store = get_vector_store()
        per_sub_k = max(5, ctx.top_k // max(len(sub_queries), 1))

        tasks = [
            store.search(q, SearchType.HYBRID, per_sub_k, kb)
            for q in sub_queries[:6]   # cap at 6 sub-agents to avoid runaway parallelism
            for kb in ctx.kb_ids
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        existing = {d.page_content for d in ctx.candidates}
        added = 0
        for maybe_docs in results:
            if isinstance(maybe_docs, Exception):
                ctx.log("SearchSubagents", f"Sub-agent partial error: {maybe_docs}")
                continue
            for doc in maybe_docs:
                if doc.page_content not in existing:
                    ctx.candidates.append(doc)
                    existing.add(doc.page_content)
                    added += 1

        ctx.log(
            "SearchSubagents",
            f"Parallel sub-query retrieval: {len(sub_queries)} sub-agents added {added} unique docs.",
        )
