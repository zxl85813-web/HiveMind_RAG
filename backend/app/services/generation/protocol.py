from typing import Any

from pydantic import BaseModel, Field


class DesignResult(BaseModel):
    headers: list[str]
    rows: list[dict[str, Any]]


class GenerationContext(BaseModel):
    """
    Context for Active Creating & Self-Correction Pipeline.
    """

    # Input
    task_description: str
    kb_ids: list[str]

    # State
    retrieved_content: list[str] = Field(default_factory=list)
    draft_content: DesignResult | None = None
    feedback_log: list[str] = Field(default_factory=list)

    # Output
    final_artifact_path: str | None = None

    def log(self, step: str, message: str):
        # print(f"[{step}] {message}")
        self.feedback_log.append(f"[{step}] {message}")
