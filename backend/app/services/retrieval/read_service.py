"""
Retrieval Read Service (Phase 5 / TASK-SG-002).

Read-only retrieval entry for split topology mode.
"""

from __future__ import annotations

from typing import cast

from app.core.vector_store import SearchType
from app.core.vector_store import VectorDocument
from app.schemas.knowledge_protocol import KnowledgeFragment
from app.services.retrieval.pipeline import RetrievalPipeline


class RetrievalReadService:
    """A focused read path wrapper over RetrievalPipeline."""

    def __init__(self):
        self.pipeline = RetrievalPipeline()

    async def retrieve_from_kb(
        self,
        *,
        query: str,
        kb_id: str,
        top_k: int,
        search_type: str = SearchType.HYBRID,
        user_id: str | None = None,
    ) -> list[KnowledgeFragment]:
        run_result = await self.pipeline.run(
            query=query,
            collection_names=[kb_id],
            top_k=max(top_k, 20),
            top_n=top_k,
            search_type=search_type,
            user_id=user_id,
            is_admin=False,
            variant="default",
        )
        docs: list[VectorDocument]
        if isinstance(run_result, tuple):
            docs = cast(list[VectorDocument], run_result[0])
        else:
            docs = cast(list[VectorDocument], run_result)

        fragments: list[KnowledgeFragment] = []
        for idx, doc in enumerate(docs[:top_k]):
            metadata = doc.metadata or {}
            fragments.append(
                KnowledgeFragment(
                    content=doc.page_content,
                    metadata=metadata,
                    score=float(getattr(doc, "score", 0.0) or 0.0),
                    kb_id=kb_id,
                    source_id=str(metadata.get("doc_id") or metadata.get("source_id") or f"doc_{idx}"),
                    chunk_index=int(metadata.get("chunk_index", idx) or idx),
                )
            )
        return fragments


_read_service = RetrievalReadService()


def get_retrieval_read_service() -> RetrievalReadService:
    return _read_service
