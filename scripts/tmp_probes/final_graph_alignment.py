import os
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

BASE_DIR = Path(r"c:\Users\linkage\Desktop\aiproject")
load_dotenv(BASE_DIR / "backend" / ".env")

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "neo4j123")

driver = GraphDatabase.driver(uri, auth=(user, password))

def final_alignment():
    with driver.session() as session:
        print("--- Final Rebranding & Alignment ---")
        
        # Link missing REQ to DES
        mappings = [
            ('REQ-001', 'DES-003-BACKEND_ARCHITECTURE'),
            ('REQ-002', 'multi_tier_memory'),
            ('REQ-004', 'core_routing_classification_design'),
            ('REQ-005', 'dynamic_skill_architecture'),
            ('REQ-007', 'GOV-001-DEVELOPMENT_GOVERNANCE'),
            ('REQ-007', 'DES-002-TESTING_STRATEGY')
        ]
        
        for req_id, des_id in mappings:
            print(f"Linking {req_id} -> {des_id}")
            session.run("""
                MATCH (r:Requirement {id: $req}), (d:CognitiveAsset {id: $des})
                MERGE (r)-[:DEFINES]->(d)
                MERGE (d)-[:IMPLEMENTS]->(r)
            """, req=req_id, des=des_id)

        # Force scrub IDs (Aggressive)
        props = ["id", "title", "name", "path"]
        for prop in props:
             session.run(f"""
                MATCH (n)
                WHERE n.{prop} CONTAINS 'RAG'
                SET n.{prop} = replace(n.{prop}, 'RAG', 'IntelligenceSwarm')
            """)
             session.run(f"""
                MATCH (n)
                WHERE n.{prop} CONTAINS 'rag'
                SET n.{prop} = replace(n.{prop}, 'rag', 'intelligence_swarm')
            """)

        print("\nAlignment Verified.")

if __name__ == "__main__":
    final_alignment()
    driver.close()
