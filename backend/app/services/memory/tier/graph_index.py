import json
from typing import List, Dict, Any
from loguru import logger
from app.core.graph_store import get_graph_store
from app.core.llm import get_llm_service

class GraphIndex:
    """
    Tier-2 Memory: The Graph Overview Layer.
    Extracts structured entities and relationships from text using an LLM
    and stores them in Neo4j for semantic neighbor retrieval.
    """
    def __init__(self):
        self.store = get_graph_store()
        
    async def extract_and_store(self, doc_id: str, content: str) -> None:
        """
        Asynchronously extract graph structures (nodes/edges) from text and inject them into Neo4j.
        """
        # If Neo4j isn't available, fail silently
        if not self.store or not getattr(self.store, 'driver', None):
            return

        llm = get_llm_service()
        prompt = f"""
        Analyze the following text and extract important entities and their relationships.
        Return ONLY valid JSON matching this schema:
        {{
            "nodes": [
                {{"id": "EntityName", "label": "Concept/Person/Technology", "name": "EntityName"}}
            ],
            "edges": [
                {{"source": "Entity1", "target": "Entity2", "type": "VERB_RELATION", "description": "how they relate"}}
            ]
        }}
        
        Text to analyze:
        {content}
        """

        try:
            resp_text = await llm.chat_complete([{"role": "user", "content": prompt}], json_mode=True)
            data = json.loads(resp_text)
            
            nodes = data.get("nodes", [])
            edges = data.get("edges", [])
            
            if nodes or edges:
                self.store.import_subgraph(nodes, edges)
                logger.info(f"🕸️ Tier-2 (Graph) Indexed {len(nodes)} nodes, {len(edges)} edges for {doc_id}.")
        except Exception as e:
            logger.warning(f"Failed to extract/store graph for {doc_id}: {e}")

    def get_neighborhood(self, entity_names: List[str], depth: int = 1) -> List[str]:
        """
        Query Neo4j for the immediate graph neighborhood around the specified entities (tags).
        """
        if not self.store or not getattr(self.store, 'driver', None):
            return []
            
        if not entity_names:
            return []
            
        # Clean entities for cypher passing
        safe_entities = [str(x).strip() for x in entity_names if x.strip()]
        if not safe_entities: return []

        # Find any relationships where the source OR target name is in our entity list
        # We look up by 'name' or 'id' property based on label Entity or generic
        cypher = """
        MATCH (a)-[r]-(b)
        WHERE a.name IN $entities OR a.id IN $entities
        RETURN a.id AS source, type(r) AS rel, b.id AS target, r.description AS descr
        LIMIT 10
        """
        
        try:
            results = self.store.query(cypher, {"entities": safe_entities})
            
            neighborhood_str = []
            for item in results:
                src = item.get("source", "Unknown")
                rel = item.get("rel", "RELATED")
                tgt = item.get("target", "Unknown")
                desc = item.get("descr", "")
                
                info = f"({src}) -[{rel}]-> ({tgt})"
                if desc:
                    info += f"  /* {desc} */"
                neighborhood_str.append(info)
                
            return neighborhood_str
        except Exception as e:
            logger.warning(f"Graph neighborhood query failed: {e}")
            return []

graph_index = GraphIndex()
