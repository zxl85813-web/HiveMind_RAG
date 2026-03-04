"""
Integration Test for Resource Ingestion Pipeline.
Simulates a full pipeline run with the custom IngestionExecutor.
"""

import pytest
import asyncio
from app.batch.ingestion.pipeline import create_ingestion_pipeline
from app.batch.ingestion.executor import IngestionExecutor
from app.batch.ingestion.core import ParserRegistry
from app.batch.plugins.mineru_parser import MinerUParser
from app.batch.plugins.excel_parser import ExcelParser

@pytest.mark.asyncio
async def test_resource_ingestion_flow():
    # 1. Pipeline Definition
    pipeline_def = create_ingestion_pipeline()
    assert len(pipeline_def.stages) == 5

    # 2. Mock Data
    mock_pdf_path = "/tmp/fake_paper.pdf"
    file_meta = {"filename": "fake_paper.pdf", "file_path": mock_pdf_path}

    # 3. Create Custom Executor
    # This will hook into the MinerUParser because of the .pdf extension
    executor = IngestionExecutor(pipeline_def)

    # 4. Execute
    print("\n--- Starting Pipeline Execution ---")
    artifacts = await executor.execute(
        raw_content="",  # Not needed, plugin reads file
        file_metadata=file_meta
    )
    
    # 5. Verify Results
    print("\n--- Pipeline Results ---")
    for stage, artifact in artifacts.items():
        print(f"[{stage}] Type: {artifact.artifact_type} | Conf: {artifact.confidence}")
    
    # Check if Parser was hooked correctly
    parse_artifact = artifacts.get("parse_content")
    assert parse_artifact is not None
    assert parse_artifact.confidence == 1.0
    # MinerU parser mock returns "Abstract" section
    sections = parse_artifact.data.get("sections", [])
    assert len(sections) > 0
    assert sections[0]["title"] == "Abstract"

if __name__ == "__main__":
    asyncio.run(test_resource_ingestion_flow())
