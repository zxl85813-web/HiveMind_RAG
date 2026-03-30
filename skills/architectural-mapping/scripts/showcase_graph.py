import os
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

BASE_DIR = Path(r"c:\Users\linkage\Desktop\aiproject")

def showcase():
    load_dotenv(BASE_DIR / "backend" / ".env")
    uri = os.getenv("NEO4J_URI", "bolt://121.37.20.14:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        # 1. Stats
        print("=== 📊 HiveMind Knowledge Graph Summary ===")
        stats = session.run("MATCH (n:ArchNode) UNWIND labels(n) as lbl WITH lbl, count(n) as cnt WHERE lbl <> 'ArchNode' RETURN lbl, cnt").data()
        for s in stats:
            print(f"- {s['lbl']}: {s['cnt']}")

        # 2. Key Relationships
        print("\n--- 🔗 Core Engineering Relationships ---")
        rels = [
            "DEFINES_CONTRACT", "DEFINES_MODEL", "EXPOSES_API", 
            "USES_CONTRACT", "SPECIFIES", "ADDRESSES", "VERIFIES"
        ]
        for rel in rels:
            count = session.run(f"MATCH ()-[r:{rel}]->() RETURN count(r) as c").single()['c']
            print(f"- {rel}: {count}")

        # 3. Comprehensive Lineage for 'Knowledge'
        print("\n--- 🧬 Architectural Lineage (Knowledge Base) ---")
        lineage = session.run("""
        MATCH (r:Requirement) WHERE r.id CONTAINS 'REQ-013' OR r.title CONTAINS 'Knowledge'
        OPTIONAL MATCH (d:Design)-[:ADDRESSES]->(r)
        OPTIONAL MATCH (d)-[:SPECIFIES]->(f:File)
        OPTIONAL MATCH (f)-[:EXPOSES_API]->(e:APIEndpoint)
        OPTIONAL MATCH (f)-[:DEFINES_MODEL]->(m:DatabaseModel)
        RETURN r.id as req, d.id as des, f.id as file, e.id as api, m.id as model
        LIMIT 15
        """).data()
        
        print("```mermaid")
        print("graph TD")
        nodes_added = set()
        edges_added = set()
        
        def add_node(id, label, style=None):
            if id not in nodes_added:
                safe_id = id.replace(':', '_').replace('/', '_').replace('-', '_').replace('.', '_')
                if style == "file":
                    print(f'  {safe_id}["📄 {id}"]')
                elif style == "api":
                    print(f'  {safe_id}["🌐 {id}"]')
                elif style == "model":
                    print(f'  {safe_id}["🗄️ {id}"]')
                else:
                    print(f'  {safe_id}["{label}: {id}"]')
                nodes_added.add(id)
                return safe_id
            return id.replace(':', '_').replace('/', '_').replace('-', '_').replace('.', '_')

        for l in lineage:
            req_id = add_node(l['req'], "REQ") if l['req'] else None
            des_id = add_node(l['des'], "DES") if l['des'] else None
            file_id = add_node(l['file'], "File", "file") if l['file'] else None
            api_id = add_node(l['api'], "API", "api") if l['api'] else None
            model_id = add_node(l['model'], "Model", "model") if l['model'] else None
            
            if req_id and des_id and (req_id, des_id) not in edges_added:
                print(f"  {des_id} -->|Addresses| {req_id}")
                edges_added.add((req_id, des_id))
            if des_id and file_id and (des_id, file_id) not in edges_added:
                print(f"  {des_id} -->|Specifies| {file_id}")
                edges_added.add((des_id, file_id))
            if file_id and api_id and (file_id, api_id) not in edges_added:
                print(f"  {file_id} -->|Exposes| {api_id}")
                edges_added.add((file_id, api_id))
            if file_id and model_id and (file_id, model_id) not in edges_added:
                print(f"  {file_id} -->|Defines| {model_id}")
                edges_added.add((file_id, model_id))
        print("```")

    driver.close()

if __name__ == "__main__":
    showcase()
