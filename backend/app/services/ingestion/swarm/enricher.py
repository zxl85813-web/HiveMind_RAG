"""
Ingestion Enricher Agent — perform semantic compilation on extracted text.
Extracts timelines, versions, tags, and pulses.
"""

import json
from typing import Any, Dict

from loguru import logger
from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.llm_router import LLMRouter, ModelTier


class IngestionEnricher:
    """
    Expert agent for semantic document enrichment.
    """

    def __init__(self, llm: Any = None):
        self.router = LLMRouter()
        self.llm = llm or self.router.get_model(ModelTier.MEDIUM)

    async def enrich(self, text: str, file_path: str, kb_id: str) -> Dict[str, Any]:
        """
        Extract semantic metadata from the raw text.
        """
        logger.info(f"🧬 [Enricher] Processing semantic metadata for {file_path}...")
        
        # 1. Truncate text for enrichment if too long (safety)
        # Ingestion usually handles full docs, but for enrichment snippets are often enough
        # or we send the full text to a long-context model.
        content_snippet = text[:15000] # Standard 15k limit for meta-extraction

        system_prompt = """
You are the HiveMind Meta-Enrichment Agent.
Your goal is to perform "Semantic Compilation" on the provided document text to enhance RAG retrieval.

Extract the following in JSON format:
1. temporal_entities: A list of objects with { "date": "...", "description": "..." } for important milestones/deadlines mentioned.
2. version_chain: If the document mentions versioning (e.g. v1.2, updated on...), provide { "current_version": "...", "previous_version_hint": "..." }.
3. semantic_tags: A list of 3-5 technical or conceptual tags (e.g. "Security", "FastAPI", "Migration Plan").
4. pulse_summary: A single-line, high-density summary (max 100 characters) for graph visualization.

Output MUST be valid JSON.
"""

        user_prompt = f"""
File Path: {file_path}
KB ID: {kb_id}

Document Content:
{content_snippet}

JSON Output:
"""

        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ])
            
            content = response.content
            # Basic JSON extraction
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            
            data = json.loads(content)
            logger.info("✅ [Enricher] Semantic metadata extracted successfully.")
            return data

        except Exception as e:
            logger.error(f"❌ [Enricher] Enrichment failed: {e}")
            return {
                "temporal_entities": [],
                "version_chain": None,
                "semantic_tags": ["ingestion-error"],
                "pulse_summary": "Extracted text summary unavailable due to processing error."
            }
