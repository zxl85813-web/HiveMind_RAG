"""
Database models for Security and Data Desensitization (M2.2).
"""

import uuid
from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel


class DesensitizationPolicy(SQLModel, table=True):
    """Stores configuration for data redaction rules."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str | None = None
    is_active: bool = Field(default=True)

    # JSON Object mapped settings: {"phone": "mask", "email": "star", "api_key": "delete"}
    # where the keys map to `DetectorRegistry` detector names.
    rules_json: str = Field(default="{}")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class DesensitizationReport(SQLModel, table=True):
    """Top-level record of a redaction run on a particular document."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    document_id: str = Field(foreign_key="documents.id", index=True)

    total_items_found: int = Field(default=0)
    total_items_redacted: int = Field(default=0)

    status: str = Field(default="completed")  # pending, processing, completed, failed
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    items: list["SensitiveItem"] = Relationship(
        back_populates="report", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class SensitiveItem(SQLModel, table=True):
    """Detailed record of each found sensitive data element."""

    id: int | None = Field(default=None, primary_key=True)
    report_id: str = Field(foreign_key="desensitizationreport.id", index=True)

    detector_type: str = Field(index=True)  # E.g. 'phone', 'email'

    # Stored for audit/review, but slightly masked for DB safety
    # e.g., if a user searches for their leaked API key, we should find it,
    # but we maybe don't want to store huge sensitive context literally.
    original_text_preview: str

    redacted_text: str  # What it was turned into (e.g. 138****1234)
    start_index: int  # Character offset start
    end_index: int  # Character offset end

    action_taken: str  # mask, replace, delete, hash, etc.

    report: "DesensitizationReport" = Relationship(back_populates="items")


class DocumentReview(SQLModel, table=True):
    """Data quality audit record."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    reviewer_id: str | None = Field(default=None, foreign_key="users.id", index=True)

    review_type: str = Field(default="auto")  # auto | manual
    status: str = Field(default="pending")  # pending | approved | rejected | needs_revision

    # Auto audit scores (0.0 to 1.0)
    quality_score: float = Field(default=0.0)
    content_length_ok: bool = Field(default=True)
    duplicate_ratio: float = Field(default=0.0)
    garble_ratio: float = Field(default=0.0)
    blank_ratio: float = Field(default=0.0)
    overlap_score: float = Field(default=0.0)  # M2.3.6: Multi-LLM Knowledge Overlap Score

    # Review details
    reviewer_comment: str | None = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class KnowledgeBasePermission(SQLModel, table=True):
    """ACL for KnowledgeBase-level access control."""

    __tablename__ = "kb_permissions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    kb_id: str = Field(foreign_key="knowledge_bases.id", index=True)

    # Target entity
    user_id: str | None = Field(default=None, index=True)
    role_id: str | None = Field(default=None, index=True)
    department_id: str | None = Field(default=None, index=True)

    # Permissions
    can_read: bool = Field(default=True)
    can_write: bool = Field(default=False)
    can_manage: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentPermission(SQLModel, table=True):
    """ACL for document-level access control."""

    __tablename__ = "document_permissions"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    document_id: str = Field(foreign_key="documents.id", index=True)

    # Target entity
    user_id: str | None = Field(default=None, index=True)
    role_id: str | None = Field(default=None, index=True)
    department_id: str | None = Field(default=None, index=True)

    # Permissions
    can_read: bool = Field(default=True)
    can_write: bool = Field(default=False)

    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditLog(SQLModel, table=True):
    """System-wide audit trail for security events."""

    __tablename__ = "audit_logs"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str | None = Field(default=None, index=True)
    action: str = Field(index=True)  # E.g., read_document, delete_kb, update_acl, detect_injection
    resource_type: str  # document, knowledge_base, query
    resource_id: str | None = None

    details: str = Field(default="{}")  # JSON payload
    ip_address: str | None = None

    timestamp: datetime = Field(default_factory=datetime.utcnow)
