import os
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

BASE_DIR = Path(r"c:\Users\linkage\Desktop\aiproject")

def showcase_frontend():
    load_dotenv(BASE_DIR / "backend" / ".env")
    uri = os.getenv("NEO4J_URI", "bolt://121.37.20.14:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")

    driver = GraphDatabase.driver(uri, auth=(user, password))
    
    with driver.session() as session:
        print("=== HiveMind Frontend Architecture (AST-Based) ===")
        
        # 1. Component Hierarchy & Dependencies
        lineage = session.run("""
        MATCH (f:File)-[:DEFINES_COMPONENT]->(c:UIElement)
        OPTIONAL MATCH (c)-[:HAS_STATE]->(s:UI_State)
        OPTIONAL MATCH (c)-[:DEPENDS_ON_STORE]->(st:UI_Store)
        OPTIONAL MATCH (c)-[:RENDERS]->(sub:UIElement)
        RETURN f.id as file, c.name as component, s.name as state, st.name as store, sub.name as sub_comp
        LIMIT 30
        """).data()
        
        print("```mermaid")
        print("graph TD")
        nodes = set()
        edges = set()
        
        def safe(s):
            return s.replace(':', '_').replace('/', '_').replace('-', '_').replace('.', '_').replace(' ', '_')

        for l in lineage:
            fid = safe(l['file'])
            cname = safe(l['component'])
            sname = safe(l['state']) if l['state'] else None
            stname = safe(l['store']) if l['store'] else None
            subname = safe(l['sub_comp']) if l['sub_comp'] else None
            
            if fid not in nodes:
                print(f'  {fid}["File: {l["file"]}"]')
                nodes.add(fid)
            
            comp_node = f"{fid}_{cname}"
            if comp_node not in nodes:
                print(f'  {comp_node}["Comp: {l["component"]}"]')
                nodes.add(comp_node)
            
            if (fid, comp_node) not in edges:
                print(f"  {fid} -->|Defines| {comp_node}")
                edges.add((fid, comp_node))
            
            if sname:
                state_node = f"{comp_node}_state_{sname}"
                if state_node not in nodes:
                    print(f'  {state_node}["state: {l["state"]}"]')
                    nodes.add(state_node)
                if (comp_node, state_node) not in edges:
                    print(f"  {comp_node} -->|HasState| {state_node}")
                    edges.add((comp_node, state_node))
            
            if stname:
                store_node = f"store_{stname}"
                if store_node not in nodes:
                    print(f'  {store_node}["Store: {l["store"]}"]')
                    nodes.add(store_node)
                if (comp_node, store_node) not in edges:
                    print(f"  {comp_node} -->|DependsOn| {store_node}")
                    edges.add((comp_node, store_node))
            
            if subname:
                # Fuzzy rendering link (sub_comp might be from another file)
                sub_node = f"comp_{subname}" 
                # We simplify the subnode ID since we don't know the exact file it belongs to in this query
                if sub_node not in nodes:
                    print(f'  {sub_node}["Comp: {l["sub_comp"]}"]')
                    nodes.add(sub_node)
                if (comp_node, sub_node) not in edges:
                    print(f"  {comp_node} -->|Renders| {sub_node}")
                    edges.add((comp_node, sub_node))
        
        print("```")

    driver.close()

if __name__ == "__main__":
    showcase_frontend()
