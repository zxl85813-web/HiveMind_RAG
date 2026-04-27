"""
Database models for RAG Evaluation (M2.1E).
Supports RAGAS-compatible metrics tracking.
"""

import uuid
from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel


class EvaluationSet(SQLModel, table=True):
    """A collection of ground truth Q&A pairs for evaluating a Knowledge Base."""

    __tablename__ = "evaluation_sets"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    kb_id: str = Field(foreign_key="knowledge_bases.id", index=True)
    name: str
    description: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    items: list["EvaluationItem"] = Relationship(
        back_populates="eval_set", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    reports: list["EvaluationReport"] = Relationship(back_populates="eval_set")


class EvaluationItem(SQLModel, table=True):
    """A single 'Question -> Ground Truth Answer' pair."""

    __tablename__ = "evaluation_items"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    set_id: str = Field(foreign_key="evaluation_sets.id", index=True)

    question: str
    ground_truth: str
    reference_context: str | None = None
    expected_facts: str = Field(default="[]")  # JSON list of atomic facts
    gold_doc_ids: str = Field(default="[]")    # JSON list of gold standard document IDs
    difficulty: int = Field(default=3)         # 1-5 scale
    category: str = Field(default="general")   # e.g., 'multi-hop', 'summarization', 'factual'

    created_at: datetime = Field(default_factory=datetime.utcnow)

    eval_set: EvaluationSet = Relationship(back_populates="items")


class EvaluationReport(SQLModel, table=True):
    """Results of an evaluation run on a specific EvaluationSet."""

    __tablename__ = "evaluation_reports"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    set_id: str = Field(foreign_key="evaluation_sets.id", index=True)
    kb_id: str | None = Field(default=None, index=True)  # Normalized for easier display

    # RAGAS Metrics (0.0 to 1.0)
    faithfulness: float = Field(default=0.0)
    answer_relevance: float = Field(default=0.0)
    context_precision: float = Field(default=0.0)
    context_recall: float = Field(default=0.0)
    answer_correctness: float = Field(default=0.0)
    semantic_similarity: float = Field(default=0.0)
    instruction_following: float = Field(default=0.0)
    
    # L1 Refined Metrics
    mrr: float = Field(default=0.0)
    hit_rate: float = Field(default=0.0)
    ndcg: float = Field(default=0.0)
    
    total_score: float = Field(default=0.0)
    confidence_score: float = Field(default=1.0) # Stability score across n samples

    # M2.5: Model Arena & Cost Analysis
    model_name: str = Field(default="default-rag-model", index=True)
    latency_ms: float = Field(default=0.0)
    cost: float = Field(default=0.0)
    token_usage: int = Field(default=0)
    judged_by: str = Field(default="gpt-4o") # The model name of the evaluator

    # JSON results for drill-down analysis
    # List of {question, answer, faithfulness_score, explanation}
    details_json: str = Field(default="[]")

    status: str = Field(default="completed")  # pending, running, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)

    eval_set: EvaluationSet = Relationship(back_populates="reports")


class BadCase(SQLModel, table=True):
    """Answers marked as poor quality, used for fine-tuning or prompt fixing."""

    __tablename__ = "bad_cases"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    message_id: str | None = Field(default=None, index=True)  # If it came from a chat message
    report_id: str | None = Field(default=None, index=True)
    question: str
    bad_answer: str
    expected_answer: str | None = None  # Filled in manually by human

    # Metadata
    reason: str | None = None  # Why is it bad? (Hallucination, Outdated, Poor Tone, etc.)
    ai_insight: str | None = None                # SYSTEM guidance for annotator
    context_snapshot: str | None = None          # The context AI used at failure time
    status: str = Field(default="pending")  # pending, reviewed, fixed, added_to_dataset

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
