"""
Excel Parser Plugin — Handles Design Documents.
"""

from typing import Optional
from app.batch.ingestion.core import BaseParser, ParserRegistry, IngestionContext
from app.batch.ingestion.protocol import StandardizedResource, ResourceMetadata, ResourceType, TableData

@ParserRegistry.register
class ExcelParser(BaseParser):
    """
    Parser for Excel Design Documents.
    """

    def can_handle(self, filename: str, content_preview: str = "") -> bool:
        return filename.lower().endswith(".xlsx") or filename.lower().endswith(".xls")

    async def parse(self, file_path: str, context: Optional[IngestionContext] = None) -> StandardizedResource:
        # TODO: Use pandas / openpyxl
        
        return StandardizedResource(
            meta=ResourceMetadata(
                filename=file_path.split("/")[-1],
                file_path=file_path,
                resource_type=ResourceType.BASIC_DESIGN
            ),
            raw_text="Mock Excel Content",
            tables=[
                TableData(
                    sheet_name="History",
                    table_name="Revision History",
                    headers=["Version", "Date", "Author", "Description"],
                    rows=[
                        {"Version": "1.0", "Date": "2026-01-01", "Author": "Alice", "Description": "Initial create"},
                        {"Version": "1.1", "Date": "2026-02-01", "Author": "Bob", "Description": "Update API"}
                    ]
                )
            ]
        )
