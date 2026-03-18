import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from pathlib import Path
import json

BASE_DIR = Path(r"c:\Users\linkage\Desktop\aiproject")
load_dotenv(BASE_DIR / "backend" / ".env")
uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USER", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "neo4j123")

def get_demo_data():
    driver = GraphDatabase.driver(uri, auth=(user, password))
    with driver.session() as session:
        # 1. Person -> Requirement (Authors)
        q1 = """
        MATCH (p:Person)-[:AUTHORED]->(r:Requirement)
        RETURN p.name as person, collect(r.id) as requirements
        """
        res1 = session.run(q1).data()
        
        # 2. Person -> Design -> File (Developers)
        q2 = """
        MATCH (p:Person)-[:CONTRIBUTED_TO]->(d:Design)-[:SPECIFIES]->(f:File)
        RETURN p.name as person, d.id as design, collect(f.id) as files
        """
        res2 = session.run(q2).data()
        
        # 3. Overall stats
        q3 = """
        MATCH (n:ArchNode)
        RETURN labels(n)[1] as type, count(n) as count
        """
        res3 = session.run(q3).data()

        demo_data = {
            "author_map": res1,
            "dev_map": res2,
            "node_stats": res3
        }
        print(json.dumps(demo_data, indent=2, ensure_ascii=False))

    driver.close()

if __name__ == '__main__':
    get_demo_data()
