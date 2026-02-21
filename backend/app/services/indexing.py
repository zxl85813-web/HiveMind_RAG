"""
Indexing Service — Handles background parsing and vectorization.

所属模块: services
依赖模块: core.vector_store, batch.ingestion.core, models.knowledge
注册位置: REGISTRY.md > Services > IndexingService
"""
import asyncio
from sqlmodel import Session, select
from loguru import logger

from app.core.database import engine
from app.core.vector_store import get_vector_store, VectorDocument
from app.models.knowledge import KnowledgeBase, Document, KnowledgeBaseDocumentLink
from app.batch.ingestion.core import ParserRegistry

# Ensure plugins are registered
import app.batch.plugins.mineru_parser
import app.batch.plugins.excel_parser
import app.batch.plugins.image_parser


async def index_document_task(kb_id: str, doc_id: str):
    """
    Background task to parse and index a document into the Knowledge Base.
    """
    logger.info(f"🚀 Starting indexing task for Doc {doc_id} -> KB {kb_id}")
    
    with Session(engine) as session:
        # Get Link
        link = session.get(KnowledgeBaseDocumentLink, (kb_id, doc_id))
        if not link:
            logger.error(f"Link not found for {kb_id}, {doc_id}")
            return
        
        # Update Status -> Indexing
        link.status = "indexing"
        session.add(link)
        session.commit()
        
        try:
            # Load Doc
            doc = session.get(Document, doc_id)
            if not doc:
                raise ValueError(f"Document {doc_id} not found")

            # Load KB (for collection name)
            kb = session.get(KnowledgeBase, kb_id)
            if not kb:
                raise ValueError(f"KB {kb_id} not found")
            
            collection_name = kb.vector_collection

            # 1. Select Parser
            # Check file extension or mime type
            parser = ParserRegistry.get_parser(doc.filename)
            if not parser:
                # Use fallback text parser if available, or error
                # ParserRegistry default mechanism should handle it?
                # Usually get_parser returns None if no match.
                # We can try to import TextParser explicitly if needed.
                from app.batch.ingestion.core import TextParser
                parser = TextParser()
                # Or raise error if strict
                # raise ValueError(f"No parser found for {doc.filename}")
            
            logger.info(f"Selected Parser: {parser.__class__.__name__}")

            # 2. Parse Content
            # Read from storage path. MVP: Local file system.
            # Production: download from S3 to temp file.
            file_path = doc.storage_path
            
            resource = await parser.parse(file_path)
            
            # 3. Chunk and Vectorize
            vector_docs = []
            
            # Process Full Text Sections
            # TODO: Use LangChain RecursiveCharacterTextSplitter for better chunks
            for section in resource.sections:
                # Simple split for MVP
                # Assuming section.content is a string
                # Breaking into 500 char chunks roughly
                text = section.content
                chunks = [text[i:i+800] for i in range(0, len(text), 800)]
                
                for i, chunk in enumerate(chunks):
                    vector_docs.append(VectorDocument(
                        page_content=chunk,
                        metadata={
                            "source": doc.filename,
                            "type": "text",
                            "section": section.title,
                            "chunk_index": i,
                            "kb_id": kb_id,
                            "doc_id": doc_id
                        }
                    ))
            
            # Process Images (Multimodal)
            for img in resource.images:
                # Combine caption and OCR text for semantic search
                content = f"Image Caption: {img.caption}\nOCR Text: {img.ocr_text}"
                if img.image_path:
                    vector_docs.append(VectorDocument(
                        page_content=content,
                        metadata={
                            "source": doc.filename,
                            "type": "image",
                            "image_path": img.image_path,
                            "kb_id": kb_id,
                            "doc_id": doc_id
                        }
                    ))
                    
                    # [Multimodal] Extract Graph from Image (Flowchart/Schema)
                    # This runs Kimi Analysis + Neo4j Import
                    try:
                        from app.skills.graph_extraction.service import extract_graph_from_image
                        logger.info(f"🕸️ Extracting Graph from image: {img.image_path}")
                        # We use the KB's vector collection name as the context ID for graph isolation if needed
                        await extract_graph_from_image(img.image_path, context_id=collection_name)
                    except Exception as e:
                        logger.warning(f"Graph extraction failed: {e}")
            
            logger.info(f"Generated {len(vector_docs)} vector chunks")

            # 3.5 Calculate Embeddings
            # Inject Embedding Service
            from app.core.embeddings import get_embedding_service
            embedder = get_embedding_service()
            
            logger.info("Computing embeddings...")
            texts = [d.page_content for d in vector_docs]
            # TODO: Batch this if list is huge
            embeddings = embedder.embed_documents(texts)
            
            for i, d in enumerate(vector_docs):
                d.embedding = embeddings[i]

            # 4. Store in Vector DB
            store = get_vector_store()
            await store.add_documents(vector_docs, collection_name=collection_name)
            
            # 5. Update Status -> Indexed
            link.status = "indexed"
            # Update Document status too? Or Doc status is global?
            # Doc status is global parsing status.
            doc.status = "parsed"
            session.add(doc)
            session.add(link)
            session.commit()
            
            logger.info(f"✅ Indexing complete for {doc.filename}")
            
        except Exception as e:
            logger.error(f"❌ Indexing failed: {e}")
            link.status = "failed"
            link.error_message = str(e)
            session.add(link)
            session.commit()
