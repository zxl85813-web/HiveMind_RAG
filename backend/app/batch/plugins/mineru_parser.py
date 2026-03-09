"""
MinerU Parser Plugin — Handles PDF/Image parsing using MinerU.
"""

from app.batch.ingestion.core import BaseParser, IngestionContext, ParserRegistry
from app.batch.ingestion.protocol import (
    DocumentSection,
    ResourceMetadata,
    ResourceType,
    StandardizedResource,
    TableData,
)


@ParserRegistry.register
class MinerUParser(BaseParser):
    """
    Parser for PDF and Complex Documents using MinerU.
    """

    def can_handle(self, filename: str, content_preview: str = "") -> bool:
        return filename.lower().endswith(".pdf") or filename.lower().endswith(".pptx")

    async def parse(self, file_path: str, context: IngestionContext | None = None) -> StandardizedResource:
        # TODO: Integrate actual MinerU SDK here.
        # For now, we mock the output structure MinerU would provide.
        mock_content = "Mocked content from MinerU for " + file_path

        return StandardizedResource(
            meta=ResourceMetadata(
                filename=file_path.split("/")[-1],
                file_path=file_path,
                resource_type=ResourceType.OTHER,
                # Type might be refined later by Classifier
            ),
            raw_text=mock_content,
            sections=[
                DocumentSection(title="Abstract", level=1, content="This is an abstract..."),
                DocumentSection(title="Introduction", level=1, content="In this paper..."),
            ],
            tables=[
                TableData(
                    table_name="Table 1", headers=["Metric", "Value"], rows=[{"Metric": "Accuracy", "Value": "99%"}]
                )
            ],
        )
