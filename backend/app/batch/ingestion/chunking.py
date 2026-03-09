"""
Document Chunking Strategies — Handles text splitting for vector search.

Supports basic recursive splitting, parent-child chunking, and table-aware chunking.
"""

import abc
import json
import uuid
from typing import ClassVar

from langchain_text_splitters import MarkdownTextSplitter, RecursiveCharacterTextSplitter
from loguru import logger

from app.batch.ingestion.protocol import StandardizedResource
from app.models.knowledge import DocumentChunk


class BaseChunkingStrategy(abc.ABC):
    """Abstract Base Class for all Chunking Strategies."""

    @abc.abstractmethod
    def chunk(self, doc_id: str, resource: StandardizedResource) -> list[DocumentChunk]:
        """
        Split a parsed resource into semantic chunks.
        Should return a list of DocumentChunk (unsaved to DB, or saved if necessary).
        """
        pass


class ChunkingStrategyRegistry:
    """Registry for chunking strategies."""

    _strategies: ClassVar[dict[str, type[BaseChunkingStrategy]]] = {}

    @classmethod
    def register(cls, name: str):
        """Decorator to register a new strategy feature name."""

        def wrapper(strategy_cls: type[BaseChunkingStrategy]):
            logger.info(f"🧩 Registered Chunking Strategy: {name}")
            cls._strategies[name] = strategy_cls
            return strategy_cls

        return wrapper

    @classmethod
    def get_strategy(cls, name: str, **kwargs) -> BaseChunkingStrategy:
        """Find and instantiate the right strategy."""
        strategy_cls = cls._strategies.get(name)
        if not strategy_cls:
            logger.warning(f"Chunking strategy '{name}' not found. Falling back to 'recursive'.")
            strategy_cls = cls._strategies.get("recursive") or RecursiveChunkingStrategy

        return strategy_cls(**kwargs)


# ============================================================
#  Strategies
# ============================================================


@ChunkingStrategyRegistry.register("recursive")
class RecursiveChunkingStrategy(BaseChunkingStrategy):
    """
    Splits text recursively by character limits cleanly preserving paragraphs/sentences.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap, separators=["\n\n", "\n", " ", ""]
        )

    def chunk(self, doc_id: str, resource: StandardizedResource) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        chunk_idx = 0

        for section in resource.sections:
            if not section.content.strip():
                continue

            # If the text is markdown, it's sometimes better to use MarkdownTextSplitter,
            # but RecursiveCharacterTextSplitter is a safer generic default.
            texts = self.splitter.split_text(section.content)

            for text in texts:
                metadata = {"source": resource.meta.filename, "section_title": section.title, "level": section.level}

                chunks.append(
                    DocumentChunk(
                        id=str(uuid.uuid4()),
                        document_id=doc_id,
                        chunk_index=chunk_idx,
                        content=text,
                        metadata_json=json.dumps(metadata, ensure_ascii=False),
                    )
                )
                chunk_idx += 1

        return chunks


@ChunkingStrategyRegistry.register("parent_child")
class ParentChildChunkingStrategy(BaseChunkingStrategy):
    """
    Creates large parent chunks (e.g., 1000 chars) for complete context,
    and small child chunks (e.g., 200 chars) for precise retrieval indexing.
    """

    def __init__(self, parent_size: int = 1000, child_size: int = 200, overlap: int = 50):
        self.parent_splitter = RecursiveCharacterTextSplitter(chunk_size=parent_size, chunk_overlap=overlap)
        self.child_splitter = RecursiveCharacterTextSplitter(chunk_size=child_size, chunk_overlap=overlap)

    def chunk(self, doc_id: str, resource: StandardizedResource) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        chunk_idx = 0

        for section in resource.sections:
            if not section.content.strip():
                continue

            # Split into parent chunks
            parent_texts = self.parent_splitter.split_text(section.content)

            for p_text in parent_texts:
                metadata = {"source": resource.meta.filename, "section_title": section.title, "is_parent": True}

                parent_chunk = DocumentChunk(
                    id=str(uuid.uuid4()),
                    document_id=doc_id,
                    chunk_index=chunk_idx,
                    content=p_text,
                    metadata_json=json.dumps(metadata, ensure_ascii=False),
                )
                chunks.append(parent_chunk)
                chunk_idx += 1

                # Split parent into child chunks
                child_texts = self.child_splitter.split_text(p_text)
                for c_text in child_texts:
                    c_metadata = {"source": resource.meta.filename, "section_title": section.title, "is_parent": False}
                    child_chunk = DocumentChunk(
                        id=str(uuid.uuid4()),
                        document_id=doc_id,
                        chunk_index=chunk_idx,
                        content=c_text,
                        parent_chunk_id=parent_chunk.id,
                        metadata_json=json.dumps(c_metadata, ensure_ascii=False),
                    )
                    chunks.append(child_chunk)
                    chunk_idx += 1

        return chunks


@ChunkingStrategyRegistry.register("table_aware")
class TableAwareChunkingStrategy(BaseChunkingStrategy):
    """
    Detects markdown tables and prevents splitting them in the middle of rows.
    Uses MarkdownTextSplitter which respects tables to some extent.
    """

    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 100):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = MarkdownTextSplitter(chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap)

    def chunk(self, doc_id: str, resource: StandardizedResource) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        chunk_idx = 0

        for section in resource.sections:
            if not section.content.strip():
                continue

            texts = self.splitter.split_text(section.content)

            for text in texts:
                metadata = {
                    "source": resource.meta.filename,
                    "section_title": section.title,
                }

                chunks.append(
                    DocumentChunk(
                        id=str(uuid.uuid4()),
                        document_id=doc_id,
                        chunk_index=chunk_idx,
                        content=text,
                        metadata_json=json.dumps(metadata, ensure_ascii=False),
                    )
                )
                chunk_idx += 1

        return chunks
