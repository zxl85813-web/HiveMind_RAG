"""
Database models for Fine-tuning Data Management (M2.1E Refinement).
Stores high-quality QA pairs derived from human feedback or corrected bad cases.
"""

import uuid
from datetime import datetime

from sqlmodel import Field, SQLModel


class FineTuningItem(SQLModel, table=True):
    """
    Data pair for LLM fine-tuning.
    Can be used to export datasets for SFT (Supervised Fine-tuning).
    """

    __tablename__ = "finetuning_items"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    kb_id: str | None = Field(default=None, index=True)  # Optional source KB

    instruction: str  # The question/prompt
    input_context: str | None = None  # The RAG context provided (optional)
    output: str  # The target (correct) answer

    source_type: str = Field(default="manual")  # manual, evaluation_correction, user_feedback
    source_id: str | None = None  # ID of the evaluation report item or message

    status: str = Field(default="pending_review")  # pending_review, verified, exported
    created_at: datetime = Field(default_factory=datetime.utcnow)
