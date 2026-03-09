"""
Agentic Parser Plugin (V3 Architecture).

Integrates the Native LangGraph Swarm into the existing Parser Registry.
This allows the "Swarm" to be treated as just another Parser plugin,
keeping backwards compatibility while enabling sophisticated multi-agent extraction.
"""

from typing import Optional
from loguru import logger
from app.batch.ingestion.core import BaseParser, ParserRegistry, IngestionContext
from app.batch.ingestion.protocol import StandardizedResource, ResourceMetadata, ResourceType, DocumentSection
from app.services.ingestion.swarm.orchestrator import IngestionOrchestrator

@ParserRegistry.register
class AgenticParser(BaseParser):
    """
    High-Intelligence Parser that uses a LangGraph Swarm to extract content.
    Targeted at complex files (Design documents, Code projects, Mixed-media PDFs).
    """

    def can_handle(self, filename: str, content_preview: str = "") -> bool:
        # The AgenticParser attempts to handle anything that is complex or marked
        # In a real scenario, we might only trigger this for specific extensions 
        # or when a 'high_quality' flag is set in the context.
        complex_extensions = {".pdf", ".docx", ".xlsx", ".pptx", ".py", ".js", ".ts", ".c", ".cpp"}
        ext = "".join([f".{p}" for p in filename.split(".")[-1:]]).lower()
        return ext in complex_extensions

    async def parse(self, file_path: str, context: Optional[IngestionContext] = None) -> StandardizedResource:
        """
        Invokes the IngestionOrchestrator (Swarm) to perform intelligent extraction.
        """
        trace_id = context.job_id if context else "internal_swarm_job"
        kb_id = context.kb_id if context else "default_kb"
        
        logger.info(f"🧠 [AgenticParser] Spawning Ingestion Swarm for: {file_path}")
        
        orchestrator = IngestionOrchestrator(trace_id=trace_id, kb_id=kb_id)
        
        # Execute the LangGraph workflow
        swarm_result = await orchestrator.run(file_path)
        
        # Map Swarm results back to the StandardizedResource protocol
        sections = [
            DocumentSection(
                title=s.get("title", "Section"),
                level=s.get("level", 1),
                content=s.get("content", "")
            ) for s in swarm_result.get("sections", [])
        ]
        
        if not sections and swarm_result.get("raw_text"):
            sections.append(DocumentSection(title="Extracted Content", level=1, content=swarm_result["raw_text"]))

        return StandardizedResource(
            meta=ResourceMetadata(
                filename=file_path.split("/")[-1],
                file_path=file_path,
                resource_type=ResourceType.OTHER
            ),
            raw_text=swarm_result.get("raw_text", ""),
            sections=sections,
            # Swarm might also produce tables/images if agents are equipped with OCR tools
            tables=[],
            images=[]
        )
