import os
import argparse
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

BASE_DIR = Path(r"c:\Users\linkage\Desktop\aiproject")

def query_paths(req_id=None, file_path=None):
    load_dotenv(BASE_DIR / "backend" / ".env")
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j123")
    
    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    if req_id:
        query = """
        MATCH (r:Requirement {id: $val})
        OPTIONAL MATCH (d:Design)-[:ADDRESSES]->(r)
        OPTIONAL MATCH (s:Skill)-[:ADDRESSES]->(r)
        OPTIONAL MATCH (d)-[:IMPLEMENTED_BY]->(f:File)
        RETURN r.id as origin, collect(DISTINCT d.id) as designs, collect(DISTINCT f.path) as files, collect(DISTINCT s.id) as skills
        """
    elif file_path:
        query = """
        MATCH (f:File {path: $val})
        OPTIONAL MATCH (s:Skill)-[:USES_FILE]->(f)
        OPTIONAL MATCH (d:Design)-[:IMPLEMENTED_BY]->(f)
        OPTIONAL MATCH (d)-[:ADDRESSES]->(r:Requirement)
        RETURN f.path as origin, collect(DISTINCT s.id) as used_by_skills, collect(DISTINCT d.id) as defined_in_designs, collect(DISTINCT r.id) as fulfills_requirements
        """
    else:
        query = "MATCH (n:ArchNode) RETURN n.id as id, labels(n) as labels LIMIT 50"

    with driver.session() as session:
        result = session.run(query, {"val": req_id or file_path})
        data = [record.data() for record in result]
        
    driver.close()
    return data

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--req", help="Requirement ID to lookup")
    parser.add_argument("--file", help="File path for impact analysis")
    args = parser.parse_args()
    
    results = query_paths(req_id=args.req, file_path=args.file)
    import json
    print(json.dumps(results, indent=2, ensure_ascii=False))
