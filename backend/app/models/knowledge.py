"""
Database models for Knowledge Base management.
"""

import uuid
from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

from .tags import DocumentTagLink, Tag


class KnowledgeBaseDocumentLink(SQLModel, table=True):
    __tablename__ = "knowledge_base_documents"

    knowledge_base_id: str = Field(foreign_key="knowledge_bases.id", primary_key=True)
    document_id: str = Field(foreign_key="documents.id", primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "pending"  # pending | indexing | indexed | failed
    error_message: str | None = None


class KnowledgeBase(SQLModel, table=True):
    __tablename__ = "knowledge_bases"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(index=True)
    description: str = ""
    owner_id: str = Field(foreign_key="users.id", index=True)
    embedding_model: str = "text-embedding-3-small"
    vector_collection: str  # Name of the collection in vector store
    is_public: bool = Field(default=False)
    chunking_strategy: str = Field(default="recursive")
    pipeline_type: str = Field(default="general")  # general | technical | legal | table
    version: int = Field(default=1)  # Versioning support
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    documents: list["Document"] = Relationship(back_populates="knowledge_bases", link_model=KnowledgeBaseDocumentLink)


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    # owner_id: str = Field(foreign_key="users.id", index=True) # TODO: Add owner for global ownership
    filename: str
    file_type: str  # pdf | docx | txt | md | xlsx
    file_size: int  # bytes
    storage_path: str  # S3 key 或本地路径
    file_path: str | None = Field(default=None)  # 与 storage_path 同义，供索引管道使用
    folder_path: str | None = Field(default=None, index=True)  # 原始文件夹路径，用于还原目录树
    content_hash: str | None = Field(index=True)  # Content hash for deduplication
    chunk_count: int = 0
    status: str = "pending"  # Global parsing status: pending | processing | parsed | failed
    error_message: str | None = None
    
    # === Freshness & Lifecycle (TASK-GOV-003) ===
    expiry_date: datetime | None = Field(default=None, index=True)
    last_reviewed_at: datetime | None = Field(default_factory=datetime.utcnow)
    next_review_at: datetime | None = Field(default=None, index=True)
    
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})

    knowledge_bases: list[KnowledgeBase] = Relationship(
        back_populates="documents", link_model=KnowledgeBaseDocumentLink
    )
    chunks: list["DocumentChunk"] = Relationship(back_populates="document")
    tags: list[Tag] = Relationship(back_populates="documents", link_model=DocumentTagLink, sa_relationship_kwargs={"overlaps": "tag_links,tag,document"})
    tag_links: list[DocumentTagLink] = Relationship(back_populates="document", sa_relationship_kwargs={"overlaps": "tags,tag,document"})


class DocumentChunk(SQLModel, table=True):
    __tablename__ = "document_chunks"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    document_id: str = Field(foreign_key="documents.id", index=True)
    chunk_index: int = Field(default=0)
    content: str
    metadata_json: str = Field(default="{}")  # Will store JSON string for MVP
    parent_chunk_id: str | None = Field(default=None, foreign_key="document_chunks.id", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    document: Document = Relationship(back_populates="chunks")
