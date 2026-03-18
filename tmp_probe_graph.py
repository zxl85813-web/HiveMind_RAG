import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(r"c:\Users\linkage\Desktop\aiproject")
load_dotenv(BASE_DIR / "backend" / ".env")
uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "neo4j123")

def test_connection():
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            # Get Labels
            labels = session.run("CALL db.labels()").value()
            # Get Relationship Types
            rels = session.run("CALL db.relationshipTypes()").value()
            # Get node count per label
            node_counts = {}
            for label in labels:
                count = session.run(f"MATCH (n:{label}) RETURN count(n)").single().value()
                node_counts[label] = count
            
            print(f"Labels: {labels}")
            print(f"Rels: {rels}")
            print(f"Node Counts: {node_counts}")
            
            # Look for nodes that might represent people
            person_nodes = session.run("MATCH (n) WHERE any(l IN labels(n) WHERE l =~ '(?i).*(User|Person|Dev|Actor|Human|Member).*') RETURN n LIMIT 5").data()
            print(f"Potential 'Person' nodes: {person_nodes}")

        driver.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_connection()
