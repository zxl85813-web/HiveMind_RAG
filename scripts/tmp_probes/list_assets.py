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

def list_designs():
    with driver.session() as session:
        print("--- Current Design and Assets ---")
        res = session.run("MATCH (n:CognitiveAsset) RETURN n.id as id, n.title as title, labels(n) as labels")
        for r in res:
            print(f"[{r['labels']}] {r['id']} : {r['title']}")

if __name__ == "__main__":
    list_designs()
    driver.close()
