import os
import sys
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

BASE_DIR = Path(r"c:\Users\linkage\Desktop\aiproject")
load_dotenv(BASE_DIR / "backend" / ".env")

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "neo4j123")

driver = GraphDatabase.driver(uri, auth=(user, password))

print(f"Connecting to {uri} as {user}...")

def audit():
    try:
        with driver.session() as session:
            # Audit 1: Missing Design for Requirement
            print("--- Audit Round 1: Missing Design for Requirements ---")
            res = session.run("MATCH (r:Requirement) WHERE NOT (r)-[:DEFINES|IMPLEMENTS|STRUCTURES]->(:Design) RETURN r.id as id, r.title as title")
            for r in res:
                print(f"[MISSING DESIGN] REQ: {r['id']} - {r['title']}")

            # Audit 2: Orphaned Designs (No code entities)
            print("\n--- Audit Round 2: Orphaned Designs (No implementation) ---")
            res = session.run("MATCH (d:Design) WHERE NOT (d)-[:IMPLEMENTED_BY|STRUCTURES|OWNS|REFERENCES]->(:CodeEntity) RETURN d.id as id, d.title as title")
            for r in res:
                print(f"[ORPHANED DESIGN] DES: {r['id']} - {r['title']}")

            # Audit 3: Check for GOV-001 Alignment
            print("\n--- Audit Round 3: Governance Compliance (GOV-001) ---")
            res = session.run("MATCH (n:CognitiveAsset) WHERE n.id CONTAINS 'GOV-001' RETURN n.id as id, n.title as title, n.path as path")
            found = False
            for r in res:
                found = True
                print(f"[GOV-001 ALIGNED] Node ID: {r['id']}, Title: {r['title']}")
                print(f"               Path: {r['path']}")
            if not found:
                print("[CRITICAL] GOV-001 (Governance Standard) is NOT indexed or not labeled correctly!")

            # Audit 4: Intelligence Swarm Rebranding Check
            print("\n--- Audit Round 4: Rebranding Consistency (RAG vs Swarm) ---")
            # Scan ALL properties for RAG or rag (case insensitive)
            res = session.run("MATCH (n) WHERE any(prop in keys(n) WHERE toString(n[prop]) =~ '(?i).*RAG.*') RETURN n.id as id, labels(n) as labels LIMIT 5")
            count = 0
            for r in res:
                count += 1
                print(f"[LEGACY RAG LABEL] Node {r['id']} (Labels: {r['labels']}) still contains 'RAG' branding.")
            if count == 0:
                print("[SUCCESS] No legacy 'RAG' branding found in any node properties!")
            else:
                print(f"[NOTE] Found at least {count} legacy instances. Further cleanup may be needed.")

    except Exception as e:
        print(f"Error during audit: {e}")

if __name__ == "__main__":
    audit()
    driver.close()
