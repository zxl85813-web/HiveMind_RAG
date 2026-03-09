"""
Swarm Assembler Service (V3 Architecture).

Restores the functional chunking and vectorization logic that was previously
housed in the linear IngestionExecutor stages.
"""

from typing import List, Dict, Any, Optional
from loguru import logger
import json
from sqlmodel import Session, select
from app.core.database import engine
from app.models.knowledge import KnowledgeBase, Chunk
from app.batch.ingestion.chunking import ChunkingStrategyRegistry
from app.core.vector_store import get_vector_store, VectorDocument
from app.core.embeddings import get_embedding_service

class SwarmAssembler:
    """
    Handles the 'Honey-Making' phase: turning raw text into searchable knowledge.
    """

    @staticmethod
    async def process_and_vectorize(
        kb_id: str, 
        doc_id: str, 
        raw_text: str, 
        sections: List[Dict[str, Any]],
        chunking_strategy: str = "recursive"
    ) -> Dict[str, Any]:
        """
        Consolidated logic for chunking and vectorization.
        """
        logger.info(f"🧩 [Assembler] Processing Doc {doc_id} for KB {kb_id}")
        
        # 1. Chunking
        strategy = ChunkingStrategyRegistry.get_strategy(chunking_strategy)
        # Note: We need a mock StandardizedResource to reuse the chunking strategy
        from app.batch.ingestion.protocol import StandardizedResource, ResourceMetadata, ResourceType, DocumentSection
        
        resource = StandardizedResource(
            meta=ResourceMetadata(filename=doc_id, file_path=doc_id, resource_type=ResourceType.OTHER),
            raw_text=raw_text,
            sections=[DocumentSection(**s) for s in sections],
            tables=[],
            images=[]
        )
        
        chunks = strategy.chunk(doc_id=doc_id, resource=resource)
        
        # 2. Persist Chunks to SQL
        with Session(engine) as session:
            for c in chunks:
                session.add(c)
            session.commit()
            
        # 3. Vectorization
        try:
            with Session(engine) as session:
                kb = session.get(KnowledgeBase, kb_id)
                if not kb:
                    raise Exception(f"KB {kb_id} not found")
                collection_name = kb.vector_collection

            embedder = get_embedding_service()
            vector_docs = []
            
            for c in chunks:
                # Basic metadata for vector store
                meta = {
                    "chunk_id": c.id,
                    "kb_id": kb_id,
                    "doc_id": doc_id
                }
                vector_docs.append(VectorDocument(
                    page_content=c.content,
                    metadata=meta
                ))

            if vector_docs:
                texts = [d.page_content for d in vector_docs]
                embeddings = embedder.embed_documents(texts)
                for i, d in enumerate(vector_docs):
                    d.embedding = embeddings[i]
                
                store = get_vector_store()
                await store.add_documents(vector_docs, collection_name=collection_name)
                
            logger.success(f"✅ [Assembler] Successfully vectorized {len(vector_docs)} chunks for Doc {doc_id}")
            return {"chunks_created": len(chunks), "status": "vectorized"}

        except Exception as e:
            logger.error(f"❌ [Assembler] Vectorization failed: {e}")
            raise e
