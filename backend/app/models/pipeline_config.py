import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class PipelineConfig(SQLModel, table=True):
    __tablename__ = "pipeline_configs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True)
    description: str = ""
    pipeline_type: str = Field(default="ingestion", index=True)  # ingestion | retrieval
    is_default: bool = Field(default=False)

    # Store XYFlow JSON directly { "nodes": [], "edges": [] }
    flow_data_json: str = Field(default='{"nodes":[], "edges":[]}')

    # Precompiled execution sequence to save parse time
    execution_sequence_json: str = Field(default="[]")

    owner_id: str | None = Field(foreign_key="users.id", index=True, default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
