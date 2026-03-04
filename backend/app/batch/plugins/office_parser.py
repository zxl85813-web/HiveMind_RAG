"""
Office Parser Plugin — Handles PDF, DOCX using standard python libraries.
"""

from typing import Optional, List
import os
import fitz  # PyMuPDF
from docx import Document as DocxDocument
from app.batch.ingestion.core import BaseParser, ParserRegistry, IngestionContext
from app.batch.ingestion.protocol import StandardizedResource, ResourceMetadata, ResourceType, DocumentSection
from loguru import logger

@ParserRegistry.register
class OfficeParser(BaseParser):
    """
    Parser for PDF and DOCX files.
    """

    def can_handle(self, filename: str, content_preview: str = "") -> bool:
        ext = filename.lower().split('.')[-1]
        return ext in ['pdf', 'docx']

    async def parse(self, file_path: str, context: Optional[IngestionContext] = None) -> StandardizedResource:
        ext = file_path.lower().split('.')[-1]
        sections = []
        raw_text = ""

        try:
            if ext == 'pdf':
                logger.info(f"Parsing PDF: {file_path}")
                doc = fitz.open(file_path)
                for i, page in enumerate(doc):
                    text = page.get_text()
                    raw_text += text + "\n"
                    sections.append(DocumentSection(
                        title=f"Page {i+1}",
                        level=1,
                        content=text
                    ))
                doc.close()
            elif ext == 'docx':
                logger.info(f"Parsing DOCX: {file_path}")
                doc = DocxDocument(file_path)
                full_text = []
                for para in doc.paragraphs:
                    full_text.append(para.text)
                text = "\n".join(full_text)
                raw_text = text
                sections.append(DocumentSection(
                    title="Full Content",
                    level=1,
                    content=text
                ))
        except Exception as e:
            logger.error(f"Failed to parse office file {file_path}: {e}")
            raise e

        return StandardizedResource(
            meta=ResourceMetadata(
                filename=os.path.basename(file_path),
                file_path=file_path,
                resource_type=ResourceType.OTHER
            ),
            raw_text=raw_text,
            sections=sections
        )
