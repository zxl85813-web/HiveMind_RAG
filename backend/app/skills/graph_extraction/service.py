"""
Graph Extraction Service — Multimodal to Graph.
"""

import json
import re
from typing import Any

from app.core.graph_store import get_graph_store
from app.core.llm import get_multimodal_service
from app.core.vector_store import VectorDocument, get_vector_store


async def extract_graph_from_image(image_url: str, context_id: str = "default") -> dict[str, Any]:
    """
    Analyze image, extract graph structure, store in Neo4j and ES.
    """
    mm = get_multimodal_service()

    prompt = """
    You are a Process Analyst.
    Analyze this flowchart/diagram image carefully.

    Task:
    1. Identification: Identify all nodes (steps, decisions, start/end) and relationships (arrows).
    2. Extraction: Return a structured JSON object.
    3. Summary: Provide a comprehensive textual summary of the process flow.

    Output Format (JSON only):
    {
      "summary": "The process starts at X, checks for condition Y...",
      "nodes": [
        {"id": "unique_id_1", "label": "NodeType", "description": "Text in box"}
      ],
      "edges": [
        {"source": "unique_id_1", "target": "unique_id_2", "type": "NEXT_STEP", "label": "Yes/No"}
      ]
    }
    """

    print(f"👁️ Analyzing Diagram: {image_url} ...")
    raw_response = await mm.analyze_image(image_url, prompt)

    # Clean JSON
    json_str = raw_response
    if "```json" in json_str:
        match = re.search(r"```json(.*?)```", json_str, re.DOTALL)
        if match:
            json_str = match.group(1).strip()
    elif "```" in json_str:
        match = re.search(r"```(.*?)```", json_str, re.DOTALL)
        if match:
            json_str = match.group(1).strip()

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        print(f"❌ Failed to parse JSON from MM response: {raw_response[:100]}...")
        return {"error": "Invalid JSON from LLM"}

    nodes = data.get("nodes", [])
    edges = data.get("edges", [])
    summary = data.get("summary", "")

    # 1. Store in Knowledge Graph (Neo4j)
    graph = get_graph_store()
    if graph:
        print(f"🕸️ Importing {len(nodes)} nodes and {len(edges)} edges to Neo4j...")
        graph.import_subgraph(nodes, edges)
    else:
        print("⚠️ Graph Store not available, skipping Neo4j import.")

    # 2. Store in Vector Database (ES)
    if summary:
        store = get_vector_store()
        doc = VectorDocument(
            page_content=f"Process Diagram Logic: {summary}",
            metadata={"source": image_url, "type": "chart_extraction", "node_count": len(nodes)},
        )
        await store.add_documents([doc], collection_name=context_id)
        print(f"📝 Indexed summary to Vector Store ({context_id}).")

    return data
