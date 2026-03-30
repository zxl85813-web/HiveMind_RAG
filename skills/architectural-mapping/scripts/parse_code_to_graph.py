import os
import ast
import re
from pathlib import Path
from loguru import logger
from neo4j import GraphDatabase
from dotenv import load_dotenv

# HiveMind AST Code-to-Graph Parser
BASE_DIR = Path(r"c:\Users\linkage\Desktop\aiproject")
BACKEND_APP = BASE_DIR / "backend" / "app"

class CodeGraphParser:
    def __init__(self, uri, user, password):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info("Connected to Neo4j for Code Analysis")
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

    def parse_schemas(self):
        schema_dir = BACKEND_APP / "schemas"
        if not schema_dir.exists(): return
        
        logger.info("Parsing Pydantic Schemas...")
        for schema_file in schema_dir.glob("*.py"):
            relative_path = str(schema_file.relative_to(BASE_DIR)).replace("\\", "/")
            with open(schema_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
                
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        # Simple heuristic: inherits from SQLModel or BaseModel
                        bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
                        if any(b in ["SQLModel", "BaseModel"] for b in bases):
                            class_name = node.name
                            self.run_query("""
                            MERGE (c:ArchNode:DataContract {id: $id})
                            SET c.name = $id, c.path = $path, c.type = 'DataContract'
                            WITH c
                            MATCH (f:ArchNode:File {id: $path})
                            MERGE (f)-[:DEFINES_CONTRACT]->(c)
                            """, {"id": class_name, "path": relative_path})

    def parse_models(self):
        model_dir = BACKEND_APP / "models"
        if not model_dir.exists(): return
        
        logger.info("Parsing Database Models...")
        for model_file in model_dir.glob("*.py"):
            relative_path = str(model_file.relative_to(BASE_DIR)).replace("\\", "/")
            with open(model_file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())
                
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        # Check for SQLModel and table=True
                        is_table = any(isinstance(k, ast.keyword) and k.arg == "table" and 
                                      isinstance(k.value, ast.Constant) and k.value.value is True 
                                      for k in node.keywords)
                        
                        if is_table:
                            model_name = node.name
                            self.run_query("""
                            MERGE (m:ArchNode:DatabaseModel {id: $id})
                            SET m.name = $id, m.path = $path, m.type = 'DatabaseModel'
                            WITH m
                            MATCH (f:ArchNode:File {id: $path})
                            MERGE (f)-[:DEFINES_MODEL]->(m)
                            """, {"id": model_name, "path": relative_path})

    def parse_api_routes(self):
        api_dir = BACKEND_APP / "api" / "routes"
        if not api_dir.exists(): return
        
        logger.info("Parsing API Endpoints...")
        for route_file in api_dir.glob("*.py"):
            relative_path = str(route_file.relative_to(BASE_DIR)).replace("\\", "/")
            with open(route_file, "r", encoding="utf-8") as f:
                content = f.read()
                tree = ast.parse(content)
                
                for node in tree.body:
                    if isinstance(node, ast.AsyncFunctionDef) or isinstance(node, ast.FunctionDef):
                        for decorator in node.decorator_list:
                            # Look for @router.get/post/put/delete
                            if (isinstance(decorator, ast.Call) and 
                                isinstance(decorator.func, ast.Attribute) and 
                                decorator.func.attr in ["get", "post", "put", "delete", "patch"] and
                                isinstance(decorator.func.value, ast.Name) and 
                                decorator.func.value.id == "router"):
                                
                                method = decorator.func.attr.upper()
                                url_path = "unknown"
                                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                                    url_path = decorator.args[0].value
                                
                                endpoint_id = f"{method}:{url_path}"
                                self.run_query("""
                                MERGE (e:ArchNode:APIEndpoint {id: $id})
                                SET e.name = $id, e.method = $method, e.url = $url, e.path = $path, e.type = 'APIEndpoint'
                                WITH e
                                MATCH (f:ArchNode:File {id: $path})
                                MERGE (f)-[:EXPOSES_API]->(e)
                                """, {"id": endpoint_id, "method": method, "url": url_path, "path": relative_path})
                                
                                # Trace DataContracts used in params
                                for arg in node.args.args:
                                    if arg.annotation and isinstance(arg.annotation, ast.Name):
                                        contract_name = arg.annotation.id
                                        # Link to DataContract if it exists
                                        self.run_query("""
                                        MATCH (e:APIEndpoint {id: $eid}), (c:DataContract {id: $cid})
                                        MERGE (e)-[:USES_CONTRACT]->(c)
                                        """, {"eid": endpoint_id, "cid": contract_name})

def main():
    load_dotenv(BASE_DIR / "backend" / ".env")
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j123")
    
    parser = CodeGraphParser(uri, user, password)
    # First, make sure File nodes exist from index_architecture.py
    # Then parse the internals
    parser.parse_schemas()
    parser.parse_models()
    parser.parse_api_routes()
    parser.close()
    logger.success("AST Code-to-Graph Parsing Complete!")

if __name__ == "__main__":
    main()
