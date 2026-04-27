"""
[RULE-B001]: Swarm Retrieval Node.
Extracted from swarm.py.
"""

import uuid
from loguru import logger
from app.agents.schemas import SwarmState
from app.services.swarm_observability import record_swarm_span
from app.models.observability import TraceStatus

async def retrieval_node(orchestrator, state: SwarmState) -> dict:
    """
    Retrieval node — fetches context from Radar/Graph/Vector tiers.
    """
    if state.get("context_data"):
        logger.info("🔍 Retrieval node: Context already exists (Speculative Hit). Skipping.")
        return {"status_update": "⚡ 已应用预取检索结果"}

    query = str(state.get("original_query", ""))
    context_str = ""
    kb_ids = state.get("kb_ids", [])
    retrieval_trace = []
    retrieved_docs = []

    try:
        from app.services.retrieval.pipeline import get_retrieval_service
        if not orchestrator._retriever:
            orchestrator._retriever = get_retrieval_service()

        if not kb_ids:
            from app.services.retrieval.routing import KnowledgeBaseSelector
            selector = KnowledgeBaseSelector()
            selected_kbs = await selector.select_kbs(query)
            kb_ids = [kb.id for kb in selected_kbs]

        if kb_ids:
            from app.core.database import async_session_factory
            from app.models.chat import User
            from app.models.knowledge import KnowledgeBase
            from app.services.knowledge.kb_service import KnowledgeService

            collection_names = []
            async with async_session_factory() as db_session:
                user_id = state.get("user_id")
                accessible_kbs = None
                if user_id:
                    user = await db_session.get(User, user_id)
                    if user:
                        svc = KnowledgeService(db_session)
                        accessible_kbs = await svc.get_user_accessible_kbs(user)

                for kid in kb_ids:
                    if accessible_kbs is not None and kid not in accessible_kbs:
                        continue
                    kb = await db_session.get(KnowledgeBase, kid)
                    if kb and kb.vector_collection:
                        collection_names.append(kb.vector_collection)

            if collection_names:
                docs, trace_logs = await orchestrator._retriever.run(
                    query=query,
                    collection_names=collection_names,
                    top_k=5,
                    top_n=3,
                    variant=state.get("retrieval_variant", "default"),
                    auth_context=state.get("auth_context"),
                )
                retrieval_trace = trace_logs
                retrieved_docs = [d.dict() for d in docs]

                if docs:
                    context_str += "--- DEEP CONTEXT (RAG) ---\n"
                    for i, d in enumerate(docs):
                        fname = d.metadata.get("file_name", "Unknown File")
                        pg = d.metadata.get("page", "?")
                        context_str += f"[{i + 1}] {fname} (p.{pg}):\n{d.page_content}\n\n"
    except Exception as e:
        logger.warning(f"Retrieval work failed: {e}")

    node_id = f"retrieval_{uuid.uuid4().hex[:6]}"
    
    # --- 🔒 RECORD TRACE SPAN ---
    trace_id = state.get("swarm_trace_id")
    if trace_id:
        import asyncio
        asyncio.create_task(record_swarm_span(
            trace_id=trace_id,
            agent_name="retrieval",
            instruction=f"Retrieve context for: {query[:50]}",
            output=f"Found {len(retrieved_docs)} documents.",
            latency_ms=0.0, # TODO: Track latency
            status=TraceStatus.SUCCESS,
            details={
                "retrieved_doc_ids": [d.get("id") or d.get("metadata", {}).get("doc_id") for d in retrieved_docs],
                "retrieval_trace": retrieval_trace
            }
        ))

    return {
        "context_data": context_str,
        "last_node_id": node_id,
        "retrieval_trace": retrieval_trace,
        "retrieved_docs": retrieved_docs,
    }
