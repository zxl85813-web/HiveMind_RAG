from typing import Any
import uuid

from pydantic import BaseModel, Field

from .broker import ContextBroker


class DesignResult(BaseModel):
    headers: list[str]
    rows: list[dict[str, Any]]


class GenerationContext(BaseModel):
    """
    Context for Active Creating & Self-Correction Pipeline.
    Utilizes ContextBroker with VFS (Phase 2).
    """

    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = Field(default="default_user")

    # Input
    task_description: str
    kb_ids: list[str]

    # Persistent Storage (Memory-Safe Direct Access)
    retrieved_content: list[str] = Field(default_factory=list)
    draft_content: DesignResult | None = Field(default=None)

    # Small State
    feedback_log: list[str] = Field(default_factory=list)
    final_artifact_path: str | None = Field(default=None)

    def log(self, step: str, message: str):
        self.feedback_log.append(f"[{step}] {message}")

    def cleanup(self):
        # Phase 2: Clear the entire hierarchical path for the session
        from .broker import broker
        broker.clear(f"viking://sessions/{self.task_id}")
