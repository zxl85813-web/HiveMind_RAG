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
            print("--- Labels ---")
            labels = session.run("CALL db.labels()").value()
            for label in labels:
                count = session.run(f"MATCH (n:{label}) RETURN count(n)").single().value()
                print(f"{label}: {count}")

            print("\n--- Relationships ---")
            rels = session.run("CALL db.relationshipTypes()").value()
            for rel in rels:
                count = session.run(f"MATCH ()-[r:{rel}]->() RETURN count(r)").single().value()
                print(f"{rel}: {count}")

            print("\n--- Sample Node IDs and Labels ---")
            nodes = session.run("MATCH (n:ArchNode) RETURN n.id as id, labels(n) as labels LIMIT 10").data()
            for n in nodes:
                print(f"ID: {n['id']}, Labels: {n['labels']}")

            print("\n--- Checking for 'Person' related nodes ---")
            # Some databases might use 'Developer' or 'User'
            for label in labels:
                if any(word in label.lower() for word in ['user', 'person', 'dev', 'author', 'member']):
                    print(f"Found potential person label: {label}")
                    sample = session.run(f"MATCH (n:{label}) RETURN n LIMIT 1").data()
                    print(f"Sample: {sample}")

        driver.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    test_connection()
