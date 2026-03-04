"""
Pydantic Schemas for Knowledge Base management.
"""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel

class KnowledgeBaseCreate(SQLModel):
    name: str
    description: str = ""
    embedding_model: str = "text-embedding-3-small"
    vector_collection: str = "default_collection" # User can specify or auto-gen
    is_public: bool = False
    chunking_strategy: str = "recursive"

class KnowledgeBaseUpdate(SQLModel):
    name: str | None = None
    description: str | None = None
    is_public: bool | None = None

class DocumentCreate(SQLModel):
    filename: str
    file_type: str
    file_size: int
    storage_path: str
    content_hash: str | None = None

class DocumentResponse(DocumentCreate):
    id: str
    created_at: datetime
    status: str
    error_message: str | None = None
