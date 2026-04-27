import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from loguru import logger

def run_drift_audit():
    load_dotenv('backend/.env')
    uri = os.getenv('NEO4J_URI')
    user = os.getenv('NEO4J_USER')
    password = os.getenv('NEO4J_PASSWORD')
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # 🛸 Audit 1: Files with NO Requirement mapping
        logger.info("Audit 1: Checking for Files with NO Requirement mapping...")
        query_unlinked = """
        MATCH (f:File) 
        WHERE NOT (f)<-[:IMPLEMENTED_BY]-(:Requirement)
          AND NOT (f)<-[:IMPLEMENTED_BY]-(:Design)
          AND NOT f.id CONTAINS ".agent"
          AND NOT f.id CONTAINS "tests/"
          AND NOT f.id CONTAINS "scripts/"
          AND NOT f.id CONTAINS "docs/"
          AND NOT f.id CONTAINS ".venv"
        RETURN f.id as path, f.last_author as author, f.last_commit_date as date
        ORDER BY path
        """
        res = session.run(query_unlinked)
        unlinked = list(res)
        
        # 🛸 Audit 2: Persons with NO Commit association (Ghosts)
        query_ghosts = "MATCH (p:Person) WHERE NOT (p)-[:COMMITTED]->() RETURN p.name as name"
        ghosts = list(session.run(query_ghosts))
        
        print("\n" + "="*60)
        print(" [SHIELD]  HIVE-MIND ARCHITECTURE DRIFT REPORT")
        print("="*60)
        
        if not unlinked:
            print("OK: All core code files are linked to Requirements/Designs.")
        else:
            print(f"WARN: Found {len(unlinked)} unlinked core files (Architectural Drift):")
            for r in unlinked:
                print(f"  - {r['path']} [Author: {r['author']}, Date: {r['date']}]")
        
        if ghosts:
            print(f"\n[GHOST] Found {len(ghosts)} Person nodes with no commit history:")
            for g in ghosts:
                print(f"  - {g['name']}")
                
        print("="*60)
        print("HINT: Add '# REQ-XXX' or '# Linked Design: [DES-XXX]' to these files.")

if __name__ == "__main__":
    run_drift_audit()
