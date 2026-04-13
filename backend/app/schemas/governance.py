
from typing import Literal, List, Optional
from pydantic import BaseModel, Field
import time
import uuid

class EscalatedTask(BaseModel):
    """
    Standardized schema for tasks that an Agent cannot resolve 
    and needs to escalate to Human or a higher-tier Governance session.
    """
    task_id: str = Field(default_factory=lambda: f"TASK-GOV-{uuid.uuid4().hex[:8].upper()}")
    priority: Literal["P0", "P1", "P2"] = "P1"
    title: str
    context_stub: str
    suggested_action: str
    trace_id: str
    created_at: str = Field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    status: str = "PENDING"
    affected_nodes: List[str] = []
