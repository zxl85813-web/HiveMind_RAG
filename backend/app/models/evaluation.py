"""
Database models for RAG Evaluation (M2.1E).
Supports RAGAS-compatible metrics tracking.
"""
import uuid
from datetime import datetime
from typing import Optional, List, Dict
from sqlmodel import SQLModel, Field, Relationship

class EvaluationSet(SQLModel, table=True):
    """A collection of ground truth Q&A pairs for evaluating a Knowledge Base."""
    __tablename__ = "evaluation_sets"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    kb_id: str = Field(foreign_key="knowledge_bases.id", index=True)
    name: str
    description: Optional[str] = None
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    items: List["EvaluationItem"] = Relationship(back_populates="eval_set", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    reports: List["EvaluationReport"] = Relationship(back_populates="eval_set")


class EvaluationItem(SQLModel, table=True):
    """A single 'Question -> Ground Truth Answer' pair."""
    __tablename__ = "evaluation_items"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    set_id: str = Field(foreign_key="evaluation_sets.id", index=True)
    
    question: str
    ground_truth: str
    reference_context: Optional[str] = None # The original chunk used to generate this
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    eval_set: EvaluationSet = Relationship(back_populates="items")


class EvaluationReport(SQLModel, table=True):
    """Results of an evaluation run on a specific EvaluationSet."""
    __tablename__ = "evaluation_reports"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    set_id: str = Field(foreign_key="evaluation_sets.id", index=True)
    kb_id: Optional[str] = Field(default=None, index=True) # Normalized for easier display
    
    # RAGAS Metrics (0.0 to 1.0)
    faithfulness: float = Field(default=0.0) 
    answer_relevance: float = Field(default=0.0)
    context_precision: float = Field(default=0.0)
    context_recall: float = Field(default=0.0)
    total_score: float = Field(default=0.0)
    
    # M2.5: Model Arena & Cost Analysis
    model_name: str = Field(default="default-rag-model", index=True)
    latency_ms: float = Field(default=0.0) 
    cost: float = Field(default=0.0) 
    token_usage: int = Field(default=0)
    
    # JSON results for drill-down analysis
    # List of {question, answer, faithfulness_score, explanation}
    details_json: str = Field(default="[]")
    
    status: str = Field(default="completed") # pending, running, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    eval_set: EvaluationSet = Relationship(back_populates="reports")


class BadCase(SQLModel, table=True):
    """Answers marked as poor quality (e.g. from user thumbs-down or low eval scores), used for fine-tuning or prompt fixing."""
    __tablename__ = "bad_cases"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    message_id: Optional[str] = Field(default=None, index=True) # If it came from a chat message
    question: str
    bad_answer: str
    expected_answer: Optional[str] = None # Filled in manually by human
    
    # Metadata
    reason: Optional[str] = None # Why is it bad? (Hallucination, Outdated, Poor Tone, etc.)
    status: str = Field(default="pending") # pending, reviewed, fixed, added_to_dataset
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
