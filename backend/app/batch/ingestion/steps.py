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


@StepRegistry.register("vectorize")
class VectorizeStep(BaseIngestionStep):
    """
    Saves chunks to the Vector Database.
    """
    async def run(self, stage_input: StageInput) -> Artifact:
        chunk_artifact = stage_input.get_artifact("chunk_content")
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
