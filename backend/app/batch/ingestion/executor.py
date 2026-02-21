"""
Ingestion Executor — The engine that drives the Flexible Pipeline.

This class extends the standard PipelineExecutor but adds "Code Hooks".
It intercepts specific stage names (like 'parse_content') and routes them 
to the Plugin Registry instead of a generic LLM call.
"""

from typing import Any, Dict
from loguru import logger

from app.batch.pipeline import PipelineExecutor, StageDefinition, Artifact, ArtifactType, StageInput
from app.batch.ingestion.core import ParserRegistry, IngestionContext
from app.batch.ingestion.protocol import StandardizedResource

# Import all plugins so they register themselves
import app.batch.plugins.mineru_parser
import app.batch.plugins.excel_parser
import app.batch.plugins.image_parser

class IngestionExecutor(PipelineExecutor):
    """
    Specialized Executor for the Resource Ingestion Pipeline.
    """

    async def _execute_stage(
        self,
        stage_def: StageDefinition,
        stage_input: StageInput,
    ) -> Artifact:
        """
        Override the default execution to inject local code logic.
        """
        logger.info(f"⚙️ IngestionExecutor running stage: {stage_def.name}")

        # --- Hook 1: Parse Content (The Plugin System) ---
        if stage_def.name == "parse_content":
            return await self._execute_parsing(stage_input)
        
        # --- Hook 2: AI Enrich (The Swarm) ---
        # For now we use the default LLM behavior, but we could add custom pre-processing here.
        
        # Default behavior (LLM Call)
        return await super()._execute_stage(stage_def, stage_input)

    async def _execute_parsing(self, stage_input: StageInput) -> Artifact:
        """
        Find the right plugin and run it.
        """
        filename = stage_input.file_metadata.get("filename", "unknown")
        file_path = stage_input.file_metadata.get("file_path", "")
        
        # 1. Select Plugin
        parser = ParserRegistry.get_parser(filename)
        if not parser:
            logger.warning(f"⚠️ No plugin found for {filename}, using fallback.")
            # fallback logic or error
            return Artifact(
                artifact_type=ArtifactType.ERROR,
                data={"error": f"No parser for {filename}"},
                source_stage="parse_content",
                confidence=0.0
            )

        # 2. Execute Plugin
        logger.info(f"🔌 Using Plugin: {parser.__class__.__name__} for {filename}")
        try:
            resource: StandardizedResource = await parser.parse(file_path)
            
            # 3. Wrap result
            return Artifact(
                artifact_type=ArtifactType.EXTRACTED_DATA,
                data=resource.dict(), # Convert Pydantic to dict
                text_summary=f"Parsed {len(resource.sections)} sections, {len(resource.tables)} tables.",
                source_stage="parse_content",
                confidence=1.0
            )
        except Exception as e:
            logger.error(f"❌ Plugin {parser.__class__.__name__} failed: {e}")
            return Artifact(
                artifact_type=ArtifactType.ERROR,
                data={"error": str(e)},
                source_stage="parse_content",
                confidence=0.0
            )
