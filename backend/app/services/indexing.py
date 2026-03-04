"""
Indexing Service — Handles background parsing and vectorization using the Pipeline Engine.

所属模块: services
依赖模块: core.vector_store, batch.ingestion.executor, models.knowledge
注册位置: REGISTRY.md > Services > IndexingService
"""
import json
from sqlmodel import Session, select
from loguru import logger

from app.core.database import engine
from app.models.knowledge import KnowledgeBase, Document, KnowledgeBaseDocumentLink
from app.models.pipeline_config import PipelineConfig
from app.batch.ingestion.executor import IngestionExecutor
from app.batch.ingestion.pipeline import create_ingestion_pipeline
from app.batch.pipeline import ArtifactType

async def index_document_task(kb_id: str, doc_id: str):
    """
    Background task to parse and index a document using the Flexible Pipeline Engine.
    """
    logger.info(f"🚀 [Pipeline] Starting task: Doc {doc_id} -> KB {kb_id}")
    
    with Session(engine) as session:
        # 1. Initialization
        link = session.get(KnowledgeBaseDocumentLink, (kb_id, doc_id))
        if not link:
            logger.error(f"Link not found for KB {kb_id}, Doc {doc_id}")
            return
        
        doc = session.get(Document, doc_id)
        kb = session.get(KnowledgeBase, kb_id)
        if not doc or not kb:
            logger.error(f"Document {doc_id} or KB {kb_id} not found")
            link.status = "failed"
            session.add(link)
            session.commit()
            return

        try:
            # 2. Pipeline Execution (M2.1B Preset Templates)
            pipeline_type = kb.pipeline_type if hasattr(kb, "pipeline_type") else "general"
            pipeline_def = create_ingestion_pipeline(pipeline_type)
            # --- Logging & Monitoring (M2.1B) ---
            from app.batch.monitor import PipelineMonitor
            job_id = await PipelineMonitor.create_job(
                pipeline_name=pipeline_def.name,
                kb_id=kb_id,
                doc_id=doc_id
            )
            monitor = PipelineMonitor(job_id)
            
            executor = IngestionExecutor(pipeline_def)
            executor.on_job_start = monitor.on_job_start
            executor.on_job_end = monitor.on_job_end
            executor.on_stage_start = monitor.on_stage_start
            executor.on_stage_end = monitor.on_stage_end
            
            # Prepare metadata and context
            file_metadata = {
                "filename": doc.filename,
                "file_path": doc.file_path,
                "doc_id": doc_id,
                "kb_id": kb_id
            }
            pipeline_context = {
                "kb_id": kb_id,
                "policy_id": kb.desensitization_policy_id,
                "chunking_strategy": kb.chunking_strategy or "recursive"
            }

            # Run!
            artifacts = await executor.execute(
                raw_content="", # Step 1 (parse_content) will read from file_path
                file_metadata=file_metadata,
                pipeline_context=pipeline_context
            )

            # 3. Finalize Status (with Audit Awareness)
            all_arts = executor.get_all_artifacts()
            final_stage_name = list(all_arts.keys())[-1] if all_arts else None
            final_art = all_arts.get(final_stage_name) if final_stage_name else None
            
            if final_art:
                status = final_art.data.get("status")
                
                if status == "success":
                    link.status = "completed"
                    logger.success(f"✅ Pipeline completed for {doc.filename}")
                elif status == "pending":
                    link.status = "pending_review"
                    link.error_message = final_art.data.get("comment") or "Pending manual quality audit."
                    logger.warning(f"🟡 Doc {doc_id} requires manual review: {link.error_message}")
                elif status == "rejected":
                    link.status = "rejected"
                    link.error_message = final_art.data.get("comment") or "Rejected by automated quality audit."
                    logger.error(f"🔴 Doc {doc_id} rejected: {link.error_message}")
                elif final_art.artifact_type == ArtifactType.ERROR:
                    link.status = "failed"
                    link.error_message = final_art.data.get("error", "Unknown error")
                else:
                    # Fallback for unexpected success-like states
                    link.status = "completed"
            else:
                link.status = "failed"
                link.error_message = "Pipeline failed to produce any artifacts"

            session.add(link)
            session.commit()

            # 4. Optional: GraphRAG Post-processing (Triggered separately or as a stage)
            # For now, we keep it simple. If 'vectorize' finished, we are largely done.
            # Graph extraction could be a stage in create_ingestion_pipeline.

        except Exception as e:
            logger.exception(f"💥 Critical Pipeline Error during Doc {doc_id} indexing")
            link.status = "failed"
            link.error_message = str(e)
            session.add(link)
            session.commit()
