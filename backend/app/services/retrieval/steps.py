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
                    if parent and parent.content:
                        original_length = len(doc.page_content)
                        # Substitute the content
                        doc.page_content = parent.content
                        ctx.log(
                            "ParentExpansion",
                            f"Expanded chunk '{doc.metadata.get('chunk_id')}' "
                            f"from {original_length} to {len(parent.content)} chars.",
                        )
                        # Clear parent_chunk_id so we don't expand again
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

        # 1. Extract entities from the query to know what to lookup in the graph
        # For MVP, we can just do a very simple entity extraction or rely on existing entities.
        # Here we extract entities directly using GraphExtractor
        try:
            from app.services.knowledge.graph_extractor import GraphExtractor

            extractor = GraphExtractor()
            nodes, _ = await extractor.extract_knowledge_graph(ctx.query, "query_context")
            entity_names = [n.get("id") for n in nodes if n.get("id")]

            if not entity_names:
                return

            graph_facts = []
            # 2. Lookup related edges in the graph for each KB
            for kb_id in ctx.kb_ids:
                for entity in entity_names:
                    # Basic neighborhood query
                    cypher = """
                    MATCH (n {id: $entity, kb_id: $kb_id})-[r]-(m)
                    RETURN n.id AS source, type(r) AS rel, m.id AS target, r.description AS desc
                    LIMIT 5
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

            for doc in ctx.candidates:
                doc_id = doc.metadata.get("document_id")
                if not doc_id:
                    allowed_candidates.append(doc)
                    continue

                # Default Deny (ARM-P0-2): Any document retrieved must pass an explicit has_document_permission check.
                # If no records exist in DocumentPermission, has_document_permission returns False.
                is_allowed = await has_document_permission(session, user, doc_id, "read")

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
    Compression Phase: Reduce Token usage by keeping only relevant sentences.
    (M2.1H Advanced Compaction)
    """

    async def execute(self, ctx: RetrievalContext):
        if not ctx.final_results:
            return

        import re

        # Get keywords from QueryPreProcessingStep if available
        keywords = getattr(ctx, "keywords", [])
        if not keywords:
            # Fallback: simple split of the original query
            keywords = [w.strip() for w in re.split(r"[,.\s]+", ctx.query) if len(w.strip()) > 2]

        compressed_results = []
        reduction_total = 0

        for doc in ctx.final_results:
            original_text = doc.page_content
            # Split into sentences (simple rule-based)
            sentences = re.split(r"(?<=[。？！.?!])\s+", original_text)

            # Keep sentences that contain any keyword
            relevant_sentences = []
            for sent in sentences:
                if any(kw.lower() in sent.lower() for kw in keywords):
                    relevant_sentences.append(sent)

            # If nothing was matched, keep the first 2 sentences as fallback
            if not relevant_sentences and len(sentences) > 0:
                relevant_sentences = sentences[:2]

            new_content = " ".join(relevant_sentences)
            reduction_total += len(original_text) - len(new_content)

            doc.page_content = new_content
            doc.metadata["compressed"] = True
            compressed_results.append(doc)

        ctx.final_results = compressed_results
        ctx.log("Compression", f"Reduced context by {reduction_total} chars using keyword extraction.")
