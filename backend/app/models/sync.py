import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class SyncTask(SQLModel, table=True):
    __tablename__ = "sync_tasks"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    knowledge_base_id: str = Field(foreign_key="knowledge_bases.id", index=True)
    source_type: str = Field(index=True)  # e.g. "github", "notion", "confluence"
    config_json: str = Field(default="{}")  # connection details, repo url, token, etc.
    schedule_cron: str = Field(default="0 0 * * *")  # e.g. every day at midnight

    status: str = Field(default="idle")  # idle, running, error
    last_run_at: datetime | None = Field(default=None)
    next_run_at: datetime | None = Field(default=None)
    last_error: str | None = Field(default=None)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
