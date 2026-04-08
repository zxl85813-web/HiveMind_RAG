import os
import re
import json
import ast
import subprocess
import hashlib
from pathlib import Path
from loguru import logger
from neo4j import GraphDatabase
import tree_sitter_typescript as ts_typescript
from tree_sitter import Language, Parser, Query, QueryCursor

# HiveMind Structural Indexer
BASE_DIR = Path(__file__).resolve().parents[4]
if not (BASE_DIR / "backend").exists():
    BASE_DIR = Path(os.getcwd())
    if not (BASE_DIR / "backend").exists():
        BASE_DIR = Path(r"c:\Users\linkage\Desktop\aiproject")

class ArchitectureIndexer:
    def __init__(self, uri, user, password):
        try:
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            logger.info("Connected to Neo4j for Mapping")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def run_query(self, query, params=None):
        if not self.driver: return
        try:
            with self.driver.session() as session:
                return session.run(query, params or {}).data()
        except Exception as e:
            logger.error(f"Neo4j Query Failed: {e}\nQuery: {query[:200]}...")
            return []

    def get_file_hash(self, path):
        """Calculate SHA256 of file content for incremental indexing."""
        try:
            with open(path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception:
            return ""

    def clear_graph(self):
        """Warning: This is a full reset. Usually avoided in Incremental mode."""
        logger.info("Clearing existing architectural mapping (Full Reset)...")
        self.run_query("MATCH (n:ArchNode) DETACH DELETE n")

    def cleanup_deleted_files(self, current_paths):
        """Remove nodes corresponding to files that no longer exist in the workspace."""
        logger.info("Cleaning up orphaned nodes from deleted files...")
        self.run_query("""
        MATCH (f:File) 
        WHERE NOT f.id IN $current_paths 
        OPTIONAL MATCH (f)-[:CONTAINS|DEFINES_COMPONENT|DEFINES_MODEL|SPECIFIES]->(child)
        DETACH DELETE f, child
        """, {"current_paths": current_paths})

    def index_requirements(self):
        req_dir = BASE_DIR / "docs" / "requirements"
        if not req_dir.exists(): return
        
        logger.info("Indexing Requirements...")
        for req_file in req_dir.glob("REQ-*.md"):
            req_id_match = re.match(r"(REQ-\d+)", req_file.stem)
            if not req_id_match: continue
            req_id = req_id_match.group(1)
            
            with open(req_file, encoding="utf-8") as f:
                content = f.read()
                title_match = re.search(r"^#\s+(?:REQ-\d+[:\-\s]+)?(.*)", content, re.MULTILINE)
                title = title_match.group(1).strip() if title_match else req_file.stem
                
                self.run_query("""
                MERGE (r:ArchNode:Requirement {id: $id})
                SET r.title = $title, r.path = $path, r.type = 'Requirement'
                """, {"id": req_id, "title": title, "path": str(req_file.relative_to(BASE_DIR))})

                design_matches = re.findall(r"关联设计[：:\s]+\[?(DES-\d+)\]?", content)
                for des_id in design_matches:
                    self.run_query("""
                    MATCH (r:Requirement {id: $rid}), (d:Design {id: $did})
                    MERGE (d)-[:ADDRESSES]->(r)
                    """, {"rid": req_id, "did": des_id})

    def index_designs(self):
        design_dirs = [BASE_DIR / "docs" / "architecture", BASE_DIR / "docs" / "design"]
        
        logger.info("Indexing Design Documents...")
        for design_dir in design_dirs:
            if not design_dir.exists(): continue
            for design_file in design_dir.glob("*.md"):
                try:
                    with open(design_file, encoding="utf-8") as f:
                        content = f.read()
                        design_id_match = re.search(r"(?:DES|FE-GOV|BE-GOV)-\d+", content)
                        design_id = design_id_match.group(0) if design_id_match else design_file.stem
                
                except Exception as e:
                    logger.warning(f"Failed to read design file {design_file}: {e}")
                    continue

                self.run_query("""
                MERGE (d:ArchNode:Design {id: $id})
                SET d.path = $path, d.type = 'Design', d.title = $title
                """, {"id": design_id, "path": str(design_file.relative_to(BASE_DIR)), "title": design_file.stem})
                
                req_matches = re.findall(r"关联需求[：:\s]+\[?(REQ-\d+)\]?", content)
                for rid in req_matches:
                    self.run_query("""
                    MATCH (d:Design {id: $did}), (r:Requirement {id: $rid})
                    MERGE (d)-[:ADDRESSES]->(r)
                    """, {"did": design_id, "rid": rid})

    def index_all_code_files(self):
        extensions = ["*.py", "*.ts", "*.tsx"]
        scan_dirs = [BASE_DIR / "backend" / "app", BASE_DIR / "frontend" / "src"]
        current_paths = []
        
        logger.info("Starting Incremental File Indexing...")
        
        for root_dir in scan_dirs:
            if not root_dir.exists(): continue
            for ext in extensions:
                for file_path in root_dir.rglob(ext):
                    if any(x in str(file_path) for x in [".agent", "node_modules", ".venv"]):
                        continue
                    
                    rel_path = str(file_path.relative_to(BASE_DIR)).replace("\\", "/")
                    current_paths.append(rel_path)
                    
                    curr_hash = self.get_file_hash(file_path)
                    
                    # Check if indexing needed
                    existing = self.run_query("MATCH (f:File {id: $id}) RETURN f.hash as hash", {"id": rel_path})
                    if existing and existing[0].get("hash") == curr_hash:
                        # Skip but still do light API link check if frontend
                        continue

                    logger.debug(f"Indexing changed file: {rel_path}")
                    
                    commit_info = {"author": "", "date": "", "msg": "", "count": 0}
                    try:
                        res = subprocess.run(["git", "log", "-1", "--format=%an|%cd|%s", "--date=short", "--", str(file_path)], capture_output=True, text=True, encoding="utf-8", errors="ignore", cwd=str(BASE_DIR))
                        if res.stdout.strip():
                            parts = res.stdout.strip().split("|", 2)
                            if len(parts) == 3:
                                commit_info["author"], commit_info["date"], commit_info["msg"] = parts
                        
                        count_res = subprocess.run(["git", "rev-list", "--count", "HEAD", "--", str(file_path)], capture_output=True, text=True, encoding="utf-8", errors="ignore", cwd=str(BASE_DIR))
                        if count_res.stdout.strip():
                            commit_info["count"] = int(count_res.stdout.strip())
                    except Exception: pass

                    self.run_query("""
                    MERGE (f:ArchNode:File {id: $id})
                    SET f.path = $id, f.type = 'File', f.extension = $ext, f.hash = $hash,
                        f.last_author = $author, f.last_commit_date = $date, 
                        f.last_commit_msg = $msg, f.commit_count = $count
                    """, {
                        "id": rel_path, "ext": file_path.suffix[1:], "hash": curr_hash,
                        "author": commit_info["author"], "date": commit_info["date"],
                        "msg": commit_info["msg"], "count": commit_info["count"]
                    })

                    # Update API linkages for frontend
                    if file_path.suffix in [".ts", ".tsx"] and "frontend" in rel_path:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            # Clear old calls
                            self.run_query("MATCH (:File {id: $id})-[r:CALLS_API]->() DELETE r", {"id": rel_path})
                            api_matches = re.findall(r"['\"`](/api/v1/.*?)['\"`]", content)
                            for route in api_matches:
                                base_route = route.split("?")[0].rstrip("/")
                                self.run_query("""
                                MATCH (fe:File {id: $fe_path})
                                MERGE (api:ArchNode:APIEndpoint {id: $route})
                                SET api.path = $route, api.type = 'APIEndpoint'
                                MERGE (fe)-[:CALLS_API]->(api)
                                """, {"fe_path": rel_path, "route": base_route})

        self.cleanup_deleted_files(current_paths)

    def index_typescript_ast(self):
        logger.info("Indexing TS/React AST (Incremental)...")
        TSX_LANGUAGE = Language(ts_typescript.language_tsx())
        parser = Parser(TSX_LANGUAGE)
        
        query_string = """
        (function_declaration name: (identifier) @comp_name) @comp_node
        (variable_declarator name: (identifier) @comp_name 
            value: [ (arrow_function) (function_expression) ]) @comp_node
        (variable_declarator name: (array_pattern (identifier) @state_val (identifier) @state_set)
          value: (call_expression function: (identifier) @hook_name (#eq? @hook_name "useState"))) @state_node
        (call_expression function: (identifier) @store_hook (#match? @store_hook "use.*Store")) @store_node
        (jsx_opening_element name: [(identifier) @jsx_tag (member_expression) @jsx_tag]) @jsx_node
        """
        query = TSX_LANGUAGE.query(query_string)
        
        fe_dir = BASE_DIR / "frontend" / "src"
        if not fe_dir.exists(): return
        
        for ts_file in fe_dir.rglob("*.tsx"):
            if "node_modules" in str(ts_file): continue
            rel_path = str(ts_file.relative_to(BASE_DIR)).replace("\\", "/")
            
            try:
                with open(ts_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                # Cleanup existing entities for THIS file before re-indexing
                self.run_query("MATCH (:File {id: $id})-[:DEFINES_COMPONENT|CONTAINS]->(child) DETACH DELETE child", {"id": rel_path})
                
                tree = parser.parse(bytes(content, "utf8"))
                cursor = QueryCursor()
                captures = cursor.captures(query, tree.root_node)
                
                components = {}
                states = []; stores = []; jsx_tags = []

                for node, tag in captures:
                    if tag == "comp_node":
                        name_node = node.child_by_field_name("name")
                        if name_node:
                            name = name_node.text.decode("utf8")
                            comp_id = f"{rel_path}::{name}"
                            components[node.id] = {"name": name, "id": comp_id}
                            self.run_query("""
                            MATCH (f:File {id: $fid})
                            MERGE (e:ArchNode:UIElement {id: $id})
                            SET e.name = $name, e.type = 'Component', e.path = $fid
                            MERGE (f)-[:DEFINES_COMPONENT]->(e)
                            """, {"id": comp_id, "name": name, "fid": rel_path})
                    elif tag == "state_node":
                        pattern = node.child_by_field_name("name")
                        if pattern and pattern.type == "array_pattern":
                            ids = [c for c in pattern.children if c.type == "identifier"]
                            if ids: states.append({"name": ids[0].text.decode("utf8"), "node": node})
                    elif tag == "store_node":
                        match = re.search(r"(use\w+Store)", node.text.decode("utf8"))
                        if match: stores.append({"name": match.group(1), "node": node})
                    elif tag == "jsx_node":
                        name_node = node.child_by_field_name("name")
                        if name_node:
                            tag_name = name_node.text.decode("utf8")
                            if tag_name[0].isupper() and tag_name not in ["Box", "Stack", "div", "span"]:
                                jsx_tags.append({"name": tag_name, "node": node})

                def find_container(node):
                    curr = node.parent
                    while curr:
                        if curr.id in components: return components[curr.id]
                        curr = curr.parent
                    return None

                for s in states:
                    container = find_container(s["node"])
                    if container:
                        self.run_query("MATCH (e:UIElement {id: $cid}) MERGE (s:ArchNode:UI_State {id: $sid}) SET s.name=$name, s.type='UI_State' MERGE (e)-[:HAS_STATE]->(s)", 
                                       {"cid": container['id'], "sid": f"{container['id']}::state::{s['name']}", "name": s["name"]})

                for st in stores:
                    container = find_container(st["node"])
                    if container:
                        self.run_query("MATCH (e:UIElement {id: $cid}) MERGE (st:ArchNode:UI_Store {id: $stname}) SET st.name=$stname, st.type='UI_Store' MERGE (e)-[:DEPENDS_ON_STORE]->(st)", 
                                       {"cid": container['id'], "stname": st["name"]})

                for jsx in jsx_tags:
                    container = find_container(jsx["node"])
                    if container:
                        self.run_query("MATCH (s:UIElement {id: $sid}) MATCH (t:ArchNode) WHERE t.name = $tname AND (t:File OR t:UIElement) AND t <> s MERGE (s)-[:RENDERS]->(t)", 
                                       {"sid": container['id'], "tname": jsx["name"]})

            except Exception as e:
                logger.warning(f"AST sync failed for {rel_path}: {e}")

    def index_python_ast(self):
        logger.info("Indexing Python AST (Incremental Batch)...")
        backend_dir = BASE_DIR / "backend" / "app"
        
        for py_file in backend_dir.rglob("*.py"):
            if any(x in str(py_file) for x in [".agent", ".venv"]): continue
            rel_path = str(py_file.relative_to(BASE_DIR)).replace("\\", "/")
            
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Cleanup existing entities for THIS file
                self.run_query("MATCH (:File {id: $id})-[:CONTAINS]->(child) DETACH DELETE child", {"id": rel_path})
                
                tree = ast.parse(content)
                all_defs = []; all_calls = []
                
                class PythonVisitor(ast.NodeVisitor):
                    def __init__(self):
                        self.curr_cls = None; self.curr_func = None
                    def visit_ClassDef(self, node):
                        self.curr_cls = node.name
                        all_defs.append({"id": f"{rel_path}::{node.name}", "name": node.name, "type": "Class"})
                        self.generic_visit(node); self.curr_cls = None
                    def visit_FunctionDef(self, node):
                        name = f"{self.curr_cls}.{node.name}" if self.curr_cls else node.name
                        all_defs.append({"id": f"{rel_path}::{name}", "name": name, "type": "Function"})
                        old_f = self.curr_func; self.curr_func = name
                        self.generic_visit(node); self.curr_func = old_f
                    def visit_Call(self, node):
                        if self.curr_func:
                            callee = ""
                            if isinstance(node.func, ast.Name): callee = node.func.id
                            elif isinstance(node.func, ast.Attribute): callee = node.func.attr
                            if callee: all_calls.append({"caller": f"{rel_path}::{self.curr_func}", "callee": callee})

                visitor = PythonVisitor(); visitor.visit(tree)
                
                if all_defs:
                    self.run_query("""
                    UNWIND $batch AS item
                    MATCH (f:File {id: $fid})
                    MERGE (n:ArchNode:CodeEntity {id: item.id})
                    SET n.name = item.name, n.type = item.type
                    MERGE (f)-[:CONTAINS]->(n)
                    """, {"batch": all_defs, "fid": rel_path})
                
                if all_calls:
                    for i in range(0, len(all_calls), 500):
                        self.run_query("""
                        UNWIND $batch AS c
                        MATCH (caller:CodeEntity {id: c.caller})
                        MATCH (callee:CodeEntity {name: c.callee})
                        MERGE (caller)-[:CALLS]->(callee)
                        """, {"batch": all_calls[i:i+500]})
            except Exception: pass

    # Other simpler indexers (database_models, etc) can follow similar "Cleanup then Insert" pattern.
    
    def index_todo_file(self):
        todo_file = BASE_DIR / "TODO.md"
        if not todo_file.exists(): return
        logger.info("Indexing TODO.md tasks...")
        # Clear existing todos to avoid duplication in case of title changes
        self.run_query("MATCH (n:Todo) DETACH DELETE n")
        with open(todo_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("- ["):
                    status = "PENDING"
                    if line[3] in ["x", "✅"]: status = "COMPLETED"
                    elif line[3] == "🟡": status = "IN_PROGRESS"
                    
                    content = line[6:].strip()
                    m = re.match(r"(?:\*\*([^*]+)\*\*|([A-Z0-9_-]+))\s*[—：:]\s*(.*)", content)
                    tid = m.group(1) or m.group(2) if m else "TASK-" + hashlib.md5(content.encode()).hexdigest()[:8]
                    self.run_query("MERGE (t:Todo {id: $id}) SET t.status=$status, t.title=$content", {"id": tid, "status": status, "content": content})

def main():
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / "backend" / ".env")
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j123")
    
    indexer = ArchitectureIndexer(uri, user, password)
    
    # Sequence of indexing (Incremental)
    indexer.index_requirements()
    indexer.index_designs()
    indexer.index_all_code_files()
    indexer.index_typescript_ast()
    indexer.index_python_ast()
    indexer.index_todo_file()
    
    indexer.close()
    logger.success("Incremental Architectural Mapping Complete!")

if __name__ == "__main__":
    main()
