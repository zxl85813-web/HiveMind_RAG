import argparse
import os
import sys
import json
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent

def extract_path(req_id: str = None, query: str = None):
    load_dotenv(BASE_DIR / "backend" / ".env")
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j123")

    report = {"nodes": [], "edges": []}

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        session = driver.session()
        
        # We find paths from Requirement -> Design -> File -> API/DataContract/UIElement
        # Or if query is given, we do a fuzzy search on ArchNode names
        
        if req_id:
            # Cypher for REQ -> DES -> File -> Everything else related
            cypher = """
            MATCH path = (r:Requirement)-[*1..4]-(target:ArchNode)
            WHERE r.id CONTAINS $val
              AND type(relationships(path)[0]) IN ['ADDRESSES', 'SPECIFIES', 'CALLS_API', 'USES_CONTRACT', 'CONTRACT_MIRRORS', 'RECOGNIZES', 'IMPLEMENTS_CONTRACT', 'DEPENDS_ON_STORE']
            RETURN nodes(path) as nodes, relationships(path) as rels
            LIMIT 500
            """
            val = req_id
        else:
            cypher = """
            MATCH path = (root:ArchNode)-[*1..3]-(target:ArchNode)
            WHERE toLower(root.name) CONTAINS toLower($val) OR toLower(root.id) CONTAINS toLower($val)
            RETURN nodes(path) as nodes, relationships(path) as rels
            LIMIT 500
            """
            val = query

        res = session.run(cypher, {"val": val})
        
        seen_nodes = set()
        seen_rels = set()
        
        for record in res:
            nodes = record["nodes"]
            rels = record["rels"]
            
            for n in nodes:
                nid = n.get("id")
                if nid not in seen_nodes:
                    node_data = {
                        "id": nid, 
                        "labels": list(n.labels), 
                        "name": n.get("name", nid)
                    }
                    if n.get("path"):
                        node_data["path"] = n.get("path")
                    if n.get("url"):
                        node_data["url"] = n.get("url")
                    report["nodes"].append(node_data)
                    seen_nodes.add(nid)
                    
            for r in rels:
                # Relationship representation
                rid = r.id
                if rid not in seen_rels:
                    start_node = r.start_node.get("id")
                    end_node = r.end_node.get("id")
                    rel_type = r.type
                    report["edges"].append(f"({start_node}) -[{rel_type}]-> ({end_node})")
                    seen_rels.add(rid)

        driver.close()
        
        # Organize the output somewhat logically for the LLM context
        print("=== 🌟 GRAPH E2E BUSINESS PATH EXTRACT ===")
        print(f"Target: {req_id or query}\n")
        
        by_label = {}
        for n in report["nodes"]:
            primary = n["labels"][0] if n["labels"] else "Unknown"
            by_label.setdefault(primary, []).append(n)
            
        print("--- 📦 ASSETS DISCOVERED ---")
        for lbl, items in by_label.items():
            print(f"- {lbl}:")
            # Items could be dicts now instead of just strings
            unique_items = []
            seen = set()
            for obj in items:
                display = obj["name"]
                if "path" in obj: display += f" (File: {obj['path']})"
                if "url" in obj: display += f" (Route: {obj['url']})"
                if display not in seen:
                    unique_items.append(display)
                    seen.add(display)
            
            for item in sorted(unique_items)[:20]: # limit terminal flooding
                print(f"  * {item}")
            if len(unique_items) > 20: 
                print(f"  * ...and {len(unique_items)-20} more.")
                
        print("\n--- 🔗 RELATIONAL PATHWAYS (TOP 50) ---")
        for idx, edge in enumerate(report["edges"][:50]):
            print(edge)
            
        if len(report["edges"]) > 50:
            print(f"...and {len(report['edges'])-50} more edges (Truncated).")
        
    except Exception as e:
        print(f"Error querying Neo4j: {e}", file=sys.stderr)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract E2E path from Graph")
    parser.add_argument("--req", help="Requirement ID (e.g. REQ-013)")
    parser.add_argument("--query", help="Fuzzy search text for root node")
    
    args = parser.parse_args()
    if not args.req and not args.query:
        print("Please provide --req or --query", file=sys.stderr)
        sys.exit(1)
        
    extract_path(req_id=args.req, query=args.query)
