import json
import uuid
from typing import Any, List, Dict, Optional
from loguru import logger

from app.batch.pipeline import Artifact, ArtifactType, StageInput
from app.batch.ingestion.core import BaseIngestionStep, StepRegistry
from app.batch.ingestion.protocol import StandardizedResource, DocumentSection
from app.batch.ingestion.chunking import ChunkingStrategyRegistry
from app.services.security_service import SecurityService
from app.services.audit_service import AuditService
from app.core.database import async_session_factory

@StepRegistry.register("audit_content")
class AuditStep(BaseIngestionStep):
    """
    Automated Quality Review Step using AuditService.
    """
    async def run(self, stage_input: StageInput) -> Artifact:
        parse_artifact = stage_input.get_artifact("parse_content")
        if not parse_artifact:
            return Artifact(artifact_type=ArtifactType.ERROR, data={"error": "Missing parsed data"}, source_stage="audit_content")

        resource_data = parse_artifact.data
        raw_text = resource_data.get("raw_text", "")
        doc_id = stage_input.file_metadata.get("doc_id")
        
        if not doc_id:
            return Artifact(artifact_type=ArtifactType.ERROR, data={"error": "Missing doc_id"}, source_stage="audit_content")

        try:
            async with async_session_factory() as db:
                review = await AuditService.run_audit(db, doc_id, resource_data)
                
                return Artifact(
                    artifact_type=ArtifactType.ANALYSIS_RESULT,
                    data={
                        "score": review.quality_score,
                        "status": review.status,
                        "comment": review.reviewer_comment,
                        "overlap_score": review.overlap_score
                    },
                    text_summary=f"Audit Status: {review.status}, Score: {review.quality_score}",
                    source_stage="audit_content",
                    confidence=1.0
                )
        except Exception as e:
            logger.error(f"Audit Step failed: {e}")
            return Artifact(artifact_type=ArtifactType.ERROR, data={"error": str(e)}, source_stage="audit_content")


@StepRegistry.register("desensitization")
class DesensitizationStep(BaseIngestionStep):
    """
    Applies data redaction based on the security policy.
    """
    async def run(self, stage_input: StageInput) -> Artifact:
        parse_artifact = stage_input.get_artifact("parse_content")
        if not parse_artifact:
            return Artifact(artifact_type=ArtifactType.ERROR, data={"error": "Missing parsed data"}, source_stage="desensitization")

        resource = StandardizedResource(**parse_artifact.data)
        doc_id = stage_input.file_metadata.get("doc_id")
        policy_id = stage_input.pipeline_context.get("policy_id")
        
        try:
            async with async_session_factory() as db:
                # Apply to each section
                all_applied_items = []
                for section in resource.sections:
                    redacted_text, items = await SecurityService.apply_desensitization(
                        section.content, 
                        policy_id=policy_id, 
                        db=db, 
                        doc_id=doc_id
                    )
                    section.content = redacted_text
                    all_applied_items.extend(items)
                    
                # Also apply to raw_text
                redacted_raw, _ = await SecurityService.apply_desensitization(resource.raw_text, policy_id=policy_id, db=db)
                resource.raw_text = redacted_raw

                return Artifact(
                    artifact_type=ArtifactType.EXTRACTED_DATA,
                    data=resource.model_dump(),
                    text_summary=f"Redacted {len(all_applied_items)} sensitive items.",
                    source_stage="desensitization",
                    confidence=1.0
                )
        except Exception as e:
            logger.error(f"Desensitization Step failed: {e}")
            return Artifact(artifact_type=ArtifactType.ERROR, data={"error": str(e)}, source_stage="desensitization")


@StepRegistry.register("chunk_content")
class ChunkingStep(BaseIngestionStep):
    """
    Splits the resource into chunks and SAVES them to the DB.
    """
    async def run(self, stage_input: StageInput) -> Artifact:
        data_artifact = stage_input.get_artifact("desensitization") or stage_input.get_artifact("parse_content")
        
        if not data_artifact:
            return Artifact(artifact_type=ArtifactType.ERROR, data={"error": "No data to chunk"}, source_stage="chunk_content")

        resource = StandardizedResource(**data_artifact.data)
        doc_id = stage_input.file_metadata.get("doc_id")
        
        strategy_name = stage_input.pipeline_context.get("chunking_strategy", "recursive")
        strategy = ChunkingStrategyRegistry.get_strategy(strategy_name)
        
        chunks = strategy.chunk(doc_id=doc_id, resource=resource)
        
        # Save chunks to DB (Synchronously for now as chunking.py uses sync session)
        from app.core.database import engine
        from sqlmodel import Session
        with Session(engine) as session:
            for c in chunks:
                session.add(c)
            session.commit()
            # Refresh chunks to get IDs if needed? They already have UUIDs.

        chunk_dicts = [c.model_dump() for c in chunks]
        
        return Artifact(
            artifact_type=ArtifactType.EXTRACTED_DATA,
            data={"chunks": chunk_dicts, "strategy": strategy_name},
            text_summary=f"Created {len(chunks)} chunks using {strategy_name} strategy.",
            source_stage="chunk_content",
            confidence=1.0
        )


@StepRegistry.register("situation_enrichment")
class SituationEnrichmentStep(BaseIngestionStep):
    """
    Contextual Retrieval — Situates each chunk within the overall document.
    Requirement: 2.1H Agent 架构增强 (Anthropic 文档启示)
    """
    async def run(self, stage_input: StageInput) -> Artifact:
        chunk_artifact = stage_input.get_artifact("chunk_content")
        parse_artifact = stage_input.get_artifact("desensitization") or stage_input.get_artifact("parse_content")
        
        if not chunk_artifact or not parse_artifact:
            return Artifact(
                artifact_type=ArtifactType.ERROR, 
                data={"error": "Missing chunks or raw content for enrichment"}, 
                source_stage="situation_enrichment"
            )

        chunks = chunk_artifact.data.get("chunks", [])
        raw_text = parse_artifact.data.get("raw_text", "")
        
        if not chunks or not raw_text:
            return Artifact(
                artifact_type=ArtifactType.REPORT, 
                data={"status": "skipped", "reason": "Empty chunks or raw text"}, 
                source_stage="situation_enrichment"
            )

        from app.core.llm import get_llm_service
        llm = get_llm_service()
        
        enriched_chunks = []
        logger.info(f"🧠 [Situation Enrichment] Processing {len(chunks)} chunks...")

        # Prompt template from Anthropic's Contextual Retrieval blog
        PROMPT_TEMPLATE = """
<document>
{document}
</document>
Here is the chunk we want to situate within the whole document
<chunk>
{chunk}
</chunk>
Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else.
"""

        import asyncio
        
        async def enrich_chunk(chunk_dict: Dict[str, Any]) -> Dict[str, Any]:
            chunk_text = chunk_dict.get("content", "")
            if not chunk_text:
                return chunk_dict
            
            # Use Prompt Caching (Anthropic Pattern)
            # We cache the large document part.
            prompt_messages = [
                {
                    "role": "user", 
                    "content": [
                        {
                            "type": "text",
                            "text": f"<document>\n{raw_text[:50000]}\n</document>",
                            "cache_control": {"type": "ephemeral"}
                        },
                        {
                            "type": "text",
                            "text": f"Here is the chunk we want to situate within the whole document\n<chunk>\n{chunk_text}\n</chunk>\nPlease give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."
                        }
                    ]
                }
            ]
            
            # Prepare extra headers for Anthropic Caching Beta
            extra_headers = {"anthropic-beta": "prompt-caching-2024-07-31"}
            
            try:
                context = await llm.chat_complete(
                    prompt_messages, 
                    temperature=0.0,
                    extra_headers=extra_headers
                )
            except Exception as e:
                # Fallback to simple prompt if structured content fails
                logger.warning(f"Structured prompt failed, falling back: {e}")
                simple_prompt = PROMPT_TEMPLATE.format(document=raw_text[:50000], chunk=chunk_text)
                context = await llm.chat_complete([
                    {"role": "user", "content": simple_prompt}
                ], temperature=0.0)
            
            # Prepend context to content
            enriched_content = f"{context.strip()}\n\n{chunk_text}"
            
            new_chunk = chunk_dict.copy()
            new_chunk["content"] = enriched_content
            # Keep track of original content in metadata just in case
            meta = json.loads(new_chunk.get("metadata_json", "{}"))
            meta["original_content"] = chunk_text
            meta["situational_context"] = context.strip()
            new_chunk["metadata_json"] = json.dumps(meta)
            
            return new_chunk

        # For production, we should use a semaphore to limit concurrency
        semaphore = asyncio.Semaphore(5)
        
        async def sem_enrich(chunk_dict):
            async with semaphore:
                return await enrich_chunk(chunk_dict)

        tasks = [sem_enrich(c) for c in chunks]
        enriched_chunks = await asyncio.gather(*tasks)

        return Artifact(
            artifact_type=ArtifactType.EXTRACTED_DATA,
            data={"chunks": enriched_chunks, "strategy": chunk_artifact.data.get("strategy")},
            text_summary=f"Enriched {len(enriched_chunks)} chunks with situational context.",
            source_stage="situation_enrichment",
            confidence=1.0
        )


@StepRegistry.register("vectorize")
class VectorizeStep(BaseIngestionStep):
    """
    Saves chunks to the Vector Database.
    """
    async def run(self, stage_input: StageInput) -> Artifact:
        chunk_artifact = stage_input.get_artifact("situation_enrichment") or stage_input.get_artifact("chunk_content")
        if not chunk_artifact:
            return Artifact(artifact_type=ArtifactType.ERROR, data={"error": "No chunks found"}, source_stage="vectorize")

        chunk_dicts = chunk_artifact.data.get("chunks", [])
        kb_id = stage_input.pipeline_context.get("kb_id")
        doc_id = stage_input.file_metadata.get("doc_id")
        
        if not kb_id:
            return Artifact(artifact_type=ArtifactType.ERROR, data={"error": "Missing kb_id"}, source_stage="vectorize")

        from app.core.vector_store import get_vector_store, VectorDocument
        from app.core.embeddings import get_embedding_service
        from app.models.knowledge import KnowledgeBase
        from app.core.database import engine
        from sqlmodel import Session

        # 1. Fetch KB for collection name
        with Session(engine) as session:
            kb = session.get(KnowledgeBase, kb_id)
            if not kb:
                return Artifact(artifact_type=ArtifactType.ERROR, data={"error": "KB not found"}, source_stage="vectorize")
            collection_name = kb.vector_collection
            
        # 2. Prepare VectorDocuments
        vector_docs = []
        for c_dict in chunk_dicts:
            meta = json.loads(c_dict.get("metadata_json", "{}"))
            if meta.get("is_parent") is True:
                continue
                
            meta.update({
                "chunk_id": c_dict.get("id"),
                "kb_id": kb_id,
                "doc_id": doc_id,
                "parent_chunk_id": c_dict.get("parent_chunk_id")
            })
            
            vector_docs.append(VectorDocument(
                page_content=c_dict.get("content", ""),
                metadata=meta
            ))

        if not vector_docs:
            return Artifact(artifact_type=ArtifactType.REPORT, data={"status": "skipped", "reason": "No vectorizable chunks"}, source_stage="vectorize")

        # 3. Embed & Store
        try:
            embedder = get_embedding_service()
            texts = [d.page_content for d in vector_docs]
            embeddings = embedder.embed_documents(texts)
            
            for i, d in enumerate(vector_docs):
                d.embedding = embeddings[i]
                
            store = get_vector_store()
            await store.add_documents(vector_docs, collection_name=collection_name)

            return Artifact(
                artifact_type=ArtifactType.REPORT,
                data={"status": "success", "count": len(vector_docs), "collection": collection_name},
                text_summary=f"Stored {len(vector_docs)} vectors in {collection_name}.",
                source_stage="vectorize",
                confidence=1.0
            )
        except Exception as e:
            logger.error(f"Vectorization Step failed: {e}")
            return Artifact(artifact_type=ArtifactType.ERROR, data={"error": str(e)}, source_stage="vectorize")
