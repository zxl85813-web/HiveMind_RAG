import uuid
from datetime import datetime
from sqlmodel import Field, SQLModel
from typing import Optional, Dict, Any

class PipelineJob(SQLModel, table=True):
    """
    Main entry for a single pipeline execution run.
    """
    __tablename__ = "pipeline_jobs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    pipeline_name: str = Field(index=True)
    pipeline_type: str = "ingestion" # ingestion | retrieval
    
    # Associated resources
    kb_id: Optional[str] = Field(index=True, default=None)
    doc_id: Optional[str] = Field(index=True, default=None)
    user_id: Optional[str] = Field(index=True, default=None)
    
    status: str = "pending" # pending | running | completed | failed
    total_stages: int = 0
    completed_stages: int = 0
    total_token_cost: int = 0
    
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    
    error_summary: Optional[str] = None

class PipelineStageLog(SQLModel, table=True):
    """
    Detailed logs for each stage within a pipeline job.
    """
    __tablename__ = "pipeline_stage_logs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    job_id: str = Field(foreign_key="pipeline_jobs.id", index=True)
    
    stage_name: str = Field(index=True)
    status: str = "pending" # running | completed | failed
    
    # Execution metrics
    start_time: datetime = Field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: int = 0
    token_cost: int = 0
    confidence: float = 1.0
    
    # Data snapshots
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    artifact_data_json: Optional[str] = None # Full result as JSON string
    
    error_message: Optional[str] = None
