"""
Swarm Assembler Service (V3 Architecture).

Restores the functional chunking and vectorization logic that was previously
housed in the linear IngestionExecutor stages.
"""

from typing import Any

from loguru import logger

from app.batch.ingestion.chunking import ChunkingStrategyRegistry
from app.core.database import async_session_factory
from app.core.embeddings import get_embedding_service
from app.core.vector_store import VectorDocument, get_vector_store
from app.models.knowledge import KnowledgeBase


class SwarmAssembler:
    """
    Handles the 'Honey-Making' phase: turning raw text into searchable knowledge.
    """

    @staticmethod
    async def process_and_vectorize(
        kb_id: str,
        doc_id: str,
        raw_text: str,
        sections: list[dict[str, Any]],
        chunking_strategy: str = "recursive",
        code_structure: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        Consolidated logic for chunking and vectorization.
        """
        logger.info(f"🧩 [Assembler] Processing Doc {doc_id} for KB {kb_id}")

        # 1. Chunking
        strategy = ChunkingStrategyRegistry.get_strategy(chunking_strategy)
        # Note: We need a mock StandardizedResource to reuse the chunking strategy
        from app.batch.ingestion.protocol import DocumentSection, ResourceMetadata, ResourceType, StandardizedResource

        resource = StandardizedResource(
            meta=ResourceMetadata(filename=doc_id, file_path=doc_id, resource_type=ResourceType.OTHER),
            raw_text=raw_text,
            sections=[DocumentSection(**s) for s in sections],
            tables=[],
            images=[],
        )

        chunks = strategy.chunk(doc_id=doc_id, resource=resource)

        # 2. Persist Chunks to SQL
        async with async_session_factory() as session:
            for c in chunks:
                session.add(c)
            await session.commit()

        # 3. Vectorization
        try:
            async with async_session_factory() as session:
                kb = await session.get(KnowledgeBase, kb_id)
                if not kb:
                    raise Exception(f"KB {kb_id} not found")
                collection_name = kb.vector_collection

            embedder = get_embedding_service()
            vector_docs = []

            for c in chunks:
                # Basic metadata for vector store
                meta = {"chunk_id": c.id, "kb_id": kb_id, "doc_id": doc_id}
                vector_docs.append(VectorDocument(page_content=c.content, metadata=meta))

            if vector_docs:
                texts = [d.page_content for d in vector_docs]
                embeddings = embedder.embed_documents(texts)
                for i, d in enumerate(vector_docs):
                    d.embedding = embeddings[i]

                store = get_vector_store()
                await store.add_documents(vector_docs, collection_name=collection_name)

            # 4. Code Vault Indexing (M7.2)
            if code_structure:
                from app.services.memory.tier.graph_index import graph_index
                await graph_index.index_code_structure(doc_id, code_structure)

            logger.success(f"✅ [Assembler] Successfully vectorized {len(vector_docs)} chunks and indexed structures for Doc {doc_id}")
            return {"chunks_created": len(chunks), "status": "vectorized", "has_code_structure": code_structure is not None}

        except Exception as e:
            logger.error(f"❌ [Assembler] Vectorization failed: {e}")
            raise e
