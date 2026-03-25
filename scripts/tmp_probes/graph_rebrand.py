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

def rebrand():
    with driver.session() as session:
        print("--- Execution Step 1: Property Rebranding (RAG -> Intelligence Swarm) ---")
        # Find all nodes with properties containing "RAG" and replace it
        # Note: Cypher does not have a native "replace in all properties" without APOC.
        # We will target common properties: id, title, name, description, path
        props = ["id", "title", "name", "description", "path"]
        for prop in props:
            print(f"Updating property: {prop}")
            session.run(f"""
                MATCH (n)
                WHERE n.{prop} CONTAINS 'RAG'
                SET n.{prop} = apoc.text.replace(n.{prop}, '(?i)RAG', 'Intelligence Swarm')
            """)
        
        # If APOC is not present, we use a fallback for standard Cypher
        # But for id/title we can use replace() function
        for prop in props:
             session.run(f"""
                MATCH (n)
                WHERE n.{prop} CONTAINS 'RAG'
                SET n.{prop} = replace(n.{prop}, 'RAG', 'Intelligence Swarm')
            """)
             session.run(f"""
                MATCH (n)
                WHERE n.{prop} CONTAINS 'rag'
                SET n.{prop} = replace(n.{prop}, 'rag', 'intelligence_swarm')
            """)

        print("\n--- Execution Step 2: Relabeling (Requirement -> CognitiveAsset) ---")
        # Add the new CognitiveAsset label to Requirements and Designs
        session.run("MATCH (n:Requirement) SET n:CognitiveAsset")
        session.run("MATCH (n:Design) SET n:CognitiveAsset")

        print("\n--- Execution Step 3: Indexing New Governance Assets ---")
        # Create GOV-001
        session.run("""
            MERGE (g:CognitiveAsset {id: 'GOV-001-DEVELOPMENT_GOVERNANCE'})
            SET g.title = 'HiveMind Development Governance (RDD Driven)',
                g.type = 'Governance',
                g.path = 'docs/architecture/GOV-001-DEVELOPMENT_GOVERNANCE.md',
                g.status = 'ACTIVE'
        """)

        # Link REQ-007 (Quality/Gov) to GOV-001
        session.run("""
            MATCH (r:Requirement {id: 'REQ-007'}), (g:CognitiveAsset {id: 'GOV-001-DEVELOPMENT_GOVERNANCE'})
            MERGE (r)-[:DEFINES]->(g)
        """)

        print("\nRebranding and Alignment Complete!")

if __name__ == "__main__":
    rebrand()
    driver.close()
