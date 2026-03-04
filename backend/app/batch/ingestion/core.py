"""
Core Ingestion Logic — The Plugin System Kernel.

This module defines the abstract base classes for Parsers and the Registry mechanism.
It enables the "Flexible Architecture" where new file types can be supported
by simply adding a new parser class.
"""

import abc
from typing import Any, Dict, Type, List, Optional, TYPE_CHECKING
from pydantic import BaseModel
from loguru import logger
from app.batch.ingestion.protocol import StandardizedResource, ResourceType

if TYPE_CHECKING:
    from app.batch.pipeline import Artifact

class IngestionContext(BaseModel):
    """Context passed around during ingestion."""
    job_id: str
    file_path: str
    kb_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


class BaseIngestionStep(abc.ABC):
    """Base class for a local Python-based pipeline step."""
    
    @abc.abstractmethod
    async def run(self, stage_input: Any) -> 'Artifact':
        pass


class StepRegistry:
    """Registry for local Python-based steps."""
    _steps: Dict[str, Type[BaseIngestionStep]] = {}

    @classmethod
    def register(cls, name: str):
        def wrapper(step_cls: Type[BaseIngestionStep]):
            cls._steps[name] = step_cls
            logger.info(f"🧱 Registered Pipeline Step: {name} -> {step_cls.__name__}")
            return step_cls
        return wrapper

    @classmethod
    def get_step(cls, name: str) -> Optional[BaseIngestionStep]:
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
    async def parse(self, file_path: str, context: Optional[IngestionContext] = None) -> StandardizedResource:
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
    _parsers: List[Type[BaseParser]] = []

    @classmethod
    def register(cls, parser_cls: Type[BaseParser]):
        """Decorator to register a new parser."""
        logger.info(f"🔌 Registered Parser Plugin: {parser_cls.__name__}")
        cls._parsers.append(parser_cls)
        return parser_cls

    @classmethod
    def get_parser(cls, filename: str, content_preview: str = "") -> Optional[BaseParser]:
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

# ============================================================
#  Default / Fallback Parsers
# ============================================================

@ParserRegistry.register
class TextParser(BaseParser):
    """A simple fallback parser for plain text files."""
    
    def can_handle(self, filename: str, content_preview: str = "") -> bool:
        return filename.endswith(".txt") or filename.endswith(".md")

    async def parse(self, file_path: str, context: Optional[IngestionContext] = None) -> StandardizedResource:
        from app.batch.ingestion.protocol import ResourceMetadata, ResourceType, DocumentSection
        import aiofiles
        import os
        
        async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()

        return StandardizedResource(
            meta=ResourceMetadata(
                filename=os.path.basename(file_path),
                file_path=file_path,
                resource_type=ResourceType.OTHER
            ),
            raw_text=content,
            sections=[DocumentSection(title="Full Content", level=1, content=content)]
        )
