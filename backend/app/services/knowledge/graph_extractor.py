# ruff: noqa: E501

import json
from typing import Any

from loguru import logger

from app.core.llm import LLMService


class GraphExtractor:
    """
    LLM-based Entity and Relationship Extractor for GraphRAG.
    """

    def __init__(self):
        self.llm = LLMService()

    async def extract_knowledge_graph(self, text: str, kb_id: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Extracts entities and relationships from text using an LLM.
        Returns: Tuple of (nodes, edges)
        """
        system_prompt = """
You are a top-tier Knowledge Graph Information Extractor.
Your task is to extract entities (nodes) and their relationships (edges) from the given text.

Output MUST be a valid JSON object in the exact following format:
{
    "nodes": [
        {"id": "EntityName_in_CamelCase", "label": "Concept|Person|Organization|Location|Event", "name": "Human Readable Name"}
    ],
    "edges": [
        {"source": "EntityName_1", "target": "EntityName_2", "type": "RELATIONSHIP_IN_CAPS", "description": "Short explanation"}
    ]
}

Rules:
1. Every node must have a unique 'id' (no spaces, preferably CamelCase string).
2. 'label' should be a categorical archetype (e.g., Person, Technology, Paper).
3. 'type' for edges must be ALL CAPS with underscores (e.g., HAS_AUTHOR, DEPENDS_ON).
4. Do not include introductory text. Only return the final JSON.
"""

        try:
            # We use chat_complete in json mode for structural guarantees
            response = await self.llm.chat_complete(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Extract knowledge graph from this text:\n\n{text}"},
                ],
                temperature=0.1,
                json_mode=True,
            )

            cleaned_response = response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]

            data = json.loads(cleaned_response)
            nodes = data.get("nodes", [])
            edges = data.get("edges", [])

            # Namespace isolation: ensure entities are scoped to the given Knowledge Base
            # This implements: "图谱与知识库关联 — 每个 KB 有独立的子图命名空间"
            for node in nodes:
                node["kb_id"] = kb_id

            for edge in edges:
                edge["kb_id"] = kb_id

            return nodes, edges

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM: {response} -> {e}")
            return [], []
        except Exception as e:
            logger.error(f"Failed to extract knowledge graph: {e}")
            return [], []
