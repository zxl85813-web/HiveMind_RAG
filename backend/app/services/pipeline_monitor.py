"""
Pipeline Monitoring Service — Handles execution tracing and debug logging.
"""
import json
from datetime import datetime
from typing import Any, Dict
from loguru import logger
from sqlmodel import Session

from app.core.database import engine
from app.models.pipeline_log import PipelineJob, PipelineStageLog
from app.batch.pipeline import Artifact, ArtifactType, StageInput

class PipelineMonitor:
    """
    Observer class that hooks into PipelineExecutor to persist traces.
    """
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.start_time = datetime.utcnow()

    @staticmethod
    async def create_job(
        pipeline_name: str, 
        pipeline_type: str = "ingestion",
        kb_id: str = None, 
        doc_id: str = None,
        user_id: str = None
    ) -> str:
        """Initialize a new job record in DB."""
        with Session(engine) as session:
            job = PipelineJob(
                pipeline_name=pipeline_name,
                pipeline_type=pipeline_type,
                kb_id=kb_id,
                doc_id=doc_id,
                user_id=user_id,
                status="running"
            )
            session.add(job)
            session.commit()
            session.refresh(job)
            return job.id

    async def on_job_start(self, data: Dict[str, Any]):
        """Triggered when the pipeline starts."""
        with Session(engine) as session:
            job = session.get(PipelineJob, self.job_id)
            if job:
                job.status = "running"
                job.total_stages = data.get("total_stages", 0)
                session.add(job)
                session.commit()

    async def on_stage_start(self, stage_name: str, stage_input: StageInput):
        """Triggered when a stage starts."""
        with Session(engine) as session:
            log = PipelineStageLog(
                job_id=self.job_id,
                stage_name=stage_name,
                status="running",
                input_summary=stage_input.build_context_summary(max_chars=500)
            )
            session.add(log)
            session.commit()

    async def on_stage_end(self, stage_name: str, artifact: Artifact, duration_ms: int):
        """Triggered when a stage completes."""
        with Session(engine) as session:
            # Find the running log for this stage
            from sqlmodel import select
            statement = select(PipelineStageLog).where(
                PipelineStageLog.job_id == self.job_id,
                PipelineStageLog.stage_name == stage_name,
                PipelineStageLog.status == "running"
            )
            log = session.exec(statement).first()
            
            if not log:
                # Fallback: create a new one if not found (shouldn't happen)
                log = PipelineStageLog(job_id=self.job_id, stage_name=stage_name)
            
            log.status = "completed" if artifact.artifact_type != ArtifactType.ERROR else "failed"
            log.end_time = datetime.utcnow()
            log.duration_ms = duration_ms
            log.confidence = artifact.confidence
            log.token_cost = artifact.token_cost
            log.output_summary = artifact.text_summary[:500]
            log.artifact_data_json = json.dumps(artifact.data, ensure_ascii=False)
            
            if artifact.artifact_type == ArtifactType.ERROR:
                log.error_message = artifact.data.get("error", "Unknown error")
            
            session.add(log)
            
            # Update Job progress
            job = session.get(PipelineJob, self.job_id)
            if job:
                job.completed_stages += 1
                job.total_token_cost += artifact.token_cost
                session.add(job)
                
            session.commit()

    async def on_job_end(self, artifacts: Dict[str, Artifact]):
        """Triggered when the whole pipeline finishes."""
        with Session(engine) as session:
            job = session.get(PipelineJob, self.job_id)
            if job:
                # Check if any stage failed
                has_error = any(a.artifact_type == ArtifactType.ERROR for a in artifacts.values())
                job.status = "failed" if has_error else "completed"
                job.end_time = datetime.utcnow()
                
                if has_error:
                    error_arts = [name for name, a in artifacts.items() if a.artifact_type == ArtifactType.ERROR]
                    job.error_summary = f"Errors in stages: {', '.join(error_arts)}"
                
                session.add(job)
                session.commit()
            
            logger.info(f"📊 Pipeline Job {self.job_id} monitor finished. Status: {job.status if job else 'N/A'}")
