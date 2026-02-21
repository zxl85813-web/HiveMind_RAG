"""
Resource Ingestion Pipeline — Pure Python Implementation.

This pipeline coordinates the parsing, analysis, and storage of resources.
It uses 'StandardizedResource' as the common data format between stages.
"""

from typing import Any
import json
from loguru import logger

from app.batch.pipeline import PipelineDefinition, StageDefinition, ArtifactType, Artifact
from app.batch.ingestion.protocol import StandardizedResource, ResourceType

# ============================================================
#  Stage Definitions
# ============================================================

def create_ingestion_pipeline() -> PipelineDefinition:
    
    # 1. Classification
    # Decides if it's Excel Design Doc, Java Code, or DDL
    route_stage = StageDefinition(
        name="classify_resource",
        description="Analyze filename and header to determine ResourceType (requirement, code, design, etc).",
        output_artifact_type=ArtifactType.CLASSIFICATION,
        extraction_schema={
            "resource_type": "string (enum: source_code, basic_design, detail_design, db_schema)",
            "confidence": "number"
        }
    )

    # 2. Parsing (Dynamic Plugin Strategy)
    parse_stage = StageDefinition(
        name="parse_content",
        description="Extract structure using registered plugins (MinerU, Excel, Code, etc).",
        required_inputs=["classify_resource"],
        output_artifact_type=ArtifactType.EXTRACTED_DATA,
        # The execution logic will look like: 
        # parser = ParserRegistry.get_parser(filename)
        # resource = await parser.parse(filepath)
    )

    # 3. AI Enrichment (Freestyle)
    # "What business questions can this answer?"
    enrich_stage = StageDefinition(
        name="ai_enrich",
        description="Generate 'Freestyle' tags, business summary, and hypothetical questions.",
        required_inputs=["parse_content"],
        output_artifact_type=ArtifactType.ANALYSIS_RESULT,
        extraction_schema={
            "summary": "string",
            "intent_tags": "list[string]", 
            "hypothetical_questions": "list[string]"
        }
    )

    # 4. Storage
    persist_stage = StageDefinition(
        name="persist_data",
        description="Save StandardizedResource and Enrichments to Neo4j/ES.",
        required_inputs=["parse_content", "ai_enrich"],
        output_artifact_type=ArtifactType.REPORT
    )

    return PipelineDefinition(
        name="ResourceIngestionPipeline",
        description="Python-only pipeline for ingesting software resources",
        stages=[route_stage, parse_stage, enrich_stage, persist_stage]
    )
