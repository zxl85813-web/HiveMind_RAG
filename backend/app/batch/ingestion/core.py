"""
Core Ingestion Logic — The Plugin System Kernel.

This module defines the abstract base classes for Parsers and the Registry mechanism.
It enables the "Flexible Architecture" where new file types can be supported
by simply adding a new parser class.
"""

import abc
from typing import TYPE_CHECKING, Any, ClassVar

from loguru import logger
from pydantic import BaseModel, Field

from app.batch.ingestion.protocol import ResourceType, StandardizedResource

if TYPE_CHECKING:
    from app.batch.pipeline import Artifact


class IngestionContext(BaseModel):
    """Context passed around during ingestion."""

    job_id: str
    file_path: str
    kb_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseIngestionStep(abc.ABC):
    """Base class for a local Python-based pipeline step."""

    @abc.abstractmethod
    async def run(self, stage_input: Any) -> "Artifact":
        pass


class StepRegistry:
    """Registry for local Python-based steps."""

    _steps: ClassVar[dict[str, type[BaseIngestionStep]]] = {}

    @classmethod
    def register(cls, name: str):
        def wrapper(step_cls: type[BaseIngestionStep]):
            cls._steps[name] = step_cls
            logger.info(f"🧱 Registered Pipeline Step: {name} -> {step_cls.__name__}")
            return step_cls

        return wrapper

    @classmethod
    def get_step(cls, name: str) -> BaseIngestionStep | None:
        step_cls = cls._steps.get(name)
        return step_cls() if step_cls else None


class BaseParser(abc.ABC):
    """
    Abstract Base Class for all File Parsers.
    Implement this to support a new file type (e.g. PDF, GoLang, Excel).
    """

    @abc.abstractmethod
    def can_handle(self, filename: str, content_preview: str = "") -> bool:
        """Return True if this parser can handle the given file."""
        pass

    @abc.abstractmethod
    async def parse(self, file_path: str, context: IngestionContext | None = None) -> StandardizedResource:
        """
        Parse the file and return a StandardizedResource.
        Masks the complexity of the underlying format (PDF, Excel, AST).
        """
        pass


class ParserRegistry:
    """
    The Central Registry for Parsers.
    Design Pattern: Registry / Strategy.
    """

    _parsers: ClassVar[list[type[BaseParser]]] = []

    @classmethod
    def register(cls, parser_cls: type[BaseParser]):
        """Decorator to register a new parser."""
        logger.info(f"🔌 Registered Parser Plugin: {parser_cls.__name__}")
        cls._parsers.append(parser_cls)
        return parser_cls

    @classmethod
    def get_parser(cls, filename: str, content_preview: str = "") -> BaseParser | None:
        """
        Find the right parser for the job.
        Iterates through registered parsers and asks if they can handle it.
        """
        # Priority: Last registered gets first dibs (LIFO) allowing overrides
        for parser_cls in reversed(cls._parsers):
            parser = parser_cls()
            if parser.can_handle(filename, content_preview):
                return parser
        return None

    @classmethod
    def get_parser_for_file(cls, file_path: str) -> type[BaseParser] | None:
        """
        Helper for the Swarm Orchestrator.
        Reads the first 4KB of the file to provide a content preview for better sniffing.
        """
        import os

        filename = os.path.basename(file_path)
        content_preview = ""

        # Only sneak a peek at relatively small text files
        try:
            with open(file_path, "rb") as f:
                header = f.read(4096)
                # Try to decode as utf-8, ignore errors
                content_preview = header.decode("utf-8", errors="ignore")
        except Exception:
            pass

        parser = cls.get_parser(filename, content_preview)
        return type(parser) if parser else None


# ============================================================
#  Default / Fallback Parsers
# ============================================================


@ParserRegistry.register
class TextParser(BaseParser):
    """A simple fallback parser for plain text files."""

    def can_handle(self, filename: str, content_preview: str = "") -> bool:
        return filename.endswith(".txt") or filename.endswith(".md")

    async def parse(self, file_path: str, context: IngestionContext | None = None) -> StandardizedResource:
        import os

        import aiofiles

        from app.batch.ingestion.protocol import DocumentSection, ResourceMetadata

        async with aiofiles.open(file_path, encoding="utf-8", errors="ignore") as f:
            content = await f.read()

        return StandardizedResource(
            meta=ResourceMetadata(
                filename=os.path.basename(file_path), file_path=file_path, resource_type=ResourceType.OTHER
            ),
            raw_text=content,
            sections=[DocumentSection(title="Full Content", level=1, content=content)],
        )
