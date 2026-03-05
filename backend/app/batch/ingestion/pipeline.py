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

# ============================================================
#  Pipeline Factory — Preset Templates
# ============================================================

class PipelineFactory:
    """
    Factory for various ingestion pipeline types.
    Requirement: REQ-008-rag-pipeline-quality
    """

    @staticmethod
    def create_general_pipeline() -> PipelineDefinition:
        """
        Standard flow for regular documents.
        Flow: Parse -> Audit -> Security -> Chunk -> Vectorize
        """
        stages = [
            StageDefinition(name="parse_content", description="Standard text extraction."),
            StageDefinition(name="audit_content", description="Quality check.", required_inputs=["parse_content"]),
            StageDefinition(name="desensitization", description="Security redaction.", required_inputs=["parse_content"]),
            StageDefinition(name="chunk_content", description="Recursive chunking.", required_inputs=["desensitization"]),
            StageDefinition(name="situation_enrichment", description="Add situational context.", required_inputs=["chunk_content", "desensitization"]),
            StageDefinition(name="vectorize", description="Vector indexing.", required_inputs=["situation_enrichment"])
        ]
        return PipelineDefinition(
            name="GeneralDocumentationPipeline",
            description="Best for most documents (PDF, Word, TXT). Includes full auditing, security, and Contextual Retrieval.",
            stages=stages
        )

    @staticmethod
    def create_technical_pipeline() -> PipelineDefinition:
        """
        Optimized for code and technical manuals.
        Flow: Similar to general but with technical-specific chunking hints in context.
        """
        stages = [
            StageDefinition(name="parse_content", description="Extract code & text."),
            # Audit often fails for pure code if not configured, or we can skip it for tech-only.
            StageDefinition(name="desensitization", description="Keep code secrets safe.", required_inputs=["parse_content"]),
            StageDefinition(name="chunk_content", description="Code-aware chunking.", required_inputs=["desensitization"]),
            StageDefinition(name="situation_enrichment", description="Add technical context.", required_inputs=["chunk_content", "desensitization"]),
            StageDefinition(name="vectorize", description="Store vectors.", required_inputs=["situation_enrichment"])
        ]
        return PipelineDefinition(
            name="TechnicalDocumentationPipeline",
            description="Optimized for Markdown with code blocks and technical manuals. Includes Contextual Retrieval.",
            stages=stages
        )

    @staticmethod
    def create_legal_pipeline() -> PipelineDefinition:
        """
        High accuracy and security for legal documents.
        Flow: Parse -> Audit (Mandatory) -> Security (Deep) -> Chunk -> Vectorize
        """
        stages = [
            StageDefinition(name="parse_content", description="High-precision layout extraction."),
            StageDefinition(name="audit_content", description="Compliance & Quality Audit.", required_inputs=["parse_content"]),
            StageDefinition(name="desensitization", description="Deep PII/BSI scrubbing.", required_inputs=["audit_content"]),
            StageDefinition(name="chunk_content", description="Logical section chunking.", required_inputs=["desensitization"]),
            StageDefinition(name="situation_enrichment", description="Legal context enrichment.", required_inputs=["chunk_content", "desensitization"]),
            StageDefinition(name="vectorize", description="Final storage.", required_inputs=["situation_enrichment"])
        ]
        return PipelineDefinition(
            name="LegalCompliancePipeline",
            description="Strict adherence to security, quality, and Contextual Retrieval standards for sensitive contracts.",
            stages=stages
        )

    @staticmethod
    def create_table_pipeline() -> PipelineDefinition:
        """
        Structured data extraction.
        """
        stages = [
            StageDefinition(name="parse_content", description="Table & Grid extraction."),
            StageDefinition(name="chunk_content", description="Table-aware chunking.", required_inputs=["parse_content"]),
            StageDefinition(name="situation_enrichment", description="Table context enrichment.", required_inputs=["chunk_content", "parse_content"]),
            StageDefinition(name="vectorize", description="Store table vectors.", required_inputs=["situation_enrichment"])
        ]
        return PipelineDefinition(
            name="StructuredDataPipeline",
            description="Ideal for Excel and CSV. Enhanced with Contextual Retrieval.",
            stages=stages
        )

def create_ingestion_pipeline(pipeline_type: str = "general") -> PipelineDefinition:
    """Entry point for getting a pipeline by type."""
    factories = {
        "general": PipelineFactory.create_general_pipeline,
        "technical": PipelineFactory.create_technical_pipeline,
        "legal": PipelineFactory.create_legal_pipeline,
        "table": PipelineFactory.create_table_pipeline
    }
    factory_fn = factories.get(pipeline_type, PipelineFactory.create_general_pipeline)
    return factory_fn()
