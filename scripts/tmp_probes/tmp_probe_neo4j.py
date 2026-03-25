import os
import re
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

BASE_DIR = Path(r"c:\Users\linkage\Desktop\aiproject")
load_dotenv(BASE_DIR / "backend" / ".env")

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "neo4j123")

driver = GraphDatabase.driver(uri, auth=(user, password))

def probe():
    with driver.session() as session:
        print("--- Node Counts ---")
        res = session.run("MATCH (n:ArchNode) RETURN labels(n) as labels, count(n) as count")
        for r in res:
            print(f"{r['labels']}: {r['count']}")
        
        print("\n--- Todo Sample ---")
        res = session.run("MATCH (t:Todo) RETURN t.id, t.title, t.status LIMIT 5")
        for r in res:
            print(f"ID: {r['t.id']}, Title: {r['t.title']}, Status: {r['t.status']}")

        print("\n--- Person Sample ---")
        res = session.run("MATCH (p:Person) RETURN p.id, p.name LIMIT 5")
        for r in res:
            print(f"ID: {r['p.id']}, Name: {r['p.name']}")

probe()
driver.close()
