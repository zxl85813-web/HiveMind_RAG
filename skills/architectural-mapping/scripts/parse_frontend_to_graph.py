import os
from pathlib import Path
from loguru import logger
from neo4j import GraphDatabase
from dotenv import load_dotenv

import tree_sitter_typescript as ts_typescript
from tree_sitter import Language, Parser, Query, QueryCursor

BASE_DIR = Path(r"c:\Users\linkage\Desktop\aiproject")

TSX_LANGUAGE = Language(ts_typescript.language_tsx())
parser = Parser(TSX_LANGUAGE)

query_string = """
(function_declaration
  name: (identifier) @component_name)

(variable_declarator
  name: (array_pattern 
    (identifier) @state_name
    (identifier) @setter_name)
  value: (call_expression
    function: (identifier) @hook_name
    (#eq? @hook_name "useState")))

(jsx_opening_element
  name: [
    (identifier) @tag_name
    (member_expression) @tag_name
  ])
"""
tsx_query = Query(TSX_LANGUAGE, query_string)

class FrontendCodeGraphParser:
    def __init__(self, uri, user, password):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info("Connected to Neo4j for Frontend Code Analysis")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def run_query(self, query, params=None):
        if not self.driver: return
        with self.driver.session() as session:
            session.run(query, params or {})

    def parse_frontend(self):
        src_dir = BASE_DIR / "frontend" / "src"
        if not src_dir.exists(): return
        
        logger.info("Parsing Frontend Components via Tree-Sitter...")
        cursor = QueryCursor(tsx_query)
        for tsx_file in src_dir.rglob("*.tsx"):
            relative_path = str(tsx_file.relative_to(BASE_DIR)).replace("\\", "/")
            try:
                with open(tsx_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                tree = parser.parse(bytes(content, "utf8"))
                captures = cursor.captures(tree.root_node)
                
                components = [node.text.decode("utf8") for node in captures.get("component_name", [])]
                states = [node.text.decode("utf8") for node in captures.get("state_name", [])]
                tags = {node.text.decode("utf8") for node in captures.get("tag_name", [])}
                
                for comp in components:
                    self.run_query("""
                    MERGE (c:ArchNode:UIElement {id: $id})
                    SET c.name = $id, c.type = 'UIElement'
                    WITH c
                    MATCH (f:ArchNode:File {id: $path})
                    MERGE (f)-[:DEFINES_COMPONENT]->(c)
                    """, {"id": comp, "path": relative_path})
                    
                    for state in states:
                        self.run_query("""
                        MATCH (c:UIElement {id: $cid})
                        MERGE (s:ArchNode:UI_State {id: $sid})
                        SET s.name = $sname, s.type = 'UI_State'
                        MERGE (c)-[:HAS_STATE]->(s)
                        """, {"cid": comp, "sid": f"{comp}_state_{state}", "sname": state})
                        
                    for tag in tags:
                        if tag and tag[0].isupper():
                            self.run_query("""
                            MATCH (c:UIElement {id: $cid})
                            MERGE (sub:ArchNode:UIElement {id: $sub_id})
                            SET sub.name = $sub_id, sub.type = 'UIElement'
                            MERGE (c)-[:RENDERS]->(sub)
                            """, {"cid": comp, "sub_id": tag})
            except Exception as e:
                logger.warning(f"Error parsing {relative_path}: {e}")

def main():
    load_dotenv(BASE_DIR / "backend" / ".env")
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j123")
    
    parser_job = FrontendCodeGraphParser(uri, user, password)
    parser_job.parse_frontend()
    parser_job.close()
    logger.success("Frontend AST to Graph Parsing Complete!")

if __name__ == "__main__":
    main()
