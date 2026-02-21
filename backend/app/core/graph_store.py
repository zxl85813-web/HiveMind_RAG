"""
Graph Store Interface — Neo4j Integration.
"""
from app.core.config import settings
from typing import List, Dict, Any, Optional
from loguru import logger

try:
    from neo4j import GraphDatabase
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False

class Neo4jStore:
    def __init__(self):
        if not NEO4J_AVAILABLE:
            print("⚠️ Neo4j driver not installed.")
            self.driver = None
            return

        uri = settings.NEO4J_URI
        user = settings.NEO4J_USER
        password = settings.NEO4J_PASSWORD
        
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info(f"Initialized Neo4j Driver at {uri}")
        except Exception as e:
            logger.warning(f"Neo4j Init Failed: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def query(self, cypher: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        if not self.driver:
            return []
            
        try:
            with self.driver.session() as session:
                result = session.run(cypher, parameters or {})
                return [record.data() for record in result]
        except Exception as e:
            print(f"Neo4j Query Error: {e}")
            return []

    def add_triples(self, triples: List[tuple]):
        """
        Add (Subject, Predicate, Object) triples.
        """
        if not self.driver: return
        
        # Batch processing would be better
        for subj, pred, obj in triples:
            # Simple assumption: Labels are 'Entity'
            query = """
            MERGE (a:Entity {name: $subj})
            MERGE (b:Entity {name: $obj})
            MERGE (a)-[r:RELATION {type: $pred}]->(b)
            """
            self.query(query, {"subj": subj, "pred": pred, "obj": obj})

    def import_subgraph(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        """
        Batch import nodes and edges from multimodal extraction.
        nodes: list of dict(id, label, **props)
        edges: list of dict(source, target, type, **props)
        """
        if not self.driver: return

        with self.driver.session() as session:
            # 1. Nodes
            for node in nodes:
                lbl = node.get('label', 'Entity')
                nid = node.get('id')
                if not nid: continue
                
                # Remove special keys from props
                props = {k: v for k, v in node.items() if k not in ['id', 'label']}
                props['id'] = nid
                
                # Safe interpolation for Label (Cypher param doesn't support Label)
                # Validating label is alphanumeric to prevent injection
                safe_lbl = "".join(x for x in lbl if x.isalnum() or x == "_")
                if not safe_lbl: safe_lbl = "Entity"
                
                session.run(
                    f"MERGE (n:`{safe_lbl}` {{id: $id}}) SET n += $props",
                    {"id": nid, "props": props}
                )

            # 2. Edges
            for edge in edges:
                src = edge.get('source')
                tgt = edge.get('target')
                rel = edge.get('type', 'RELATED')
                if not src or not tgt: continue

                safe_rel = "".join(x for x in rel if x.isalnum() or x == "_") or "RELATED"
                props = {k: v for k, v in edge.items() if k not in ['source', 'target', 'type']}

                session.run(
                    f"""
                    MATCH (a {{id: $src}}), (b {{id: $tgt}})
                    MERGE (a)-[r:`{safe_rel}`]->(b)
                    SET r += $props
                    """,
                    {"src": src, "tgt": tgt, "props": props}
                )

_graph_store = None
def get_graph_store():
    global _graph_store
    if not _graph_store:
        _graph_store = Neo4jStore()
    return _graph_store
