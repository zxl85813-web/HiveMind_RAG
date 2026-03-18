import os
import re
import json
import ast
import subprocess
from pathlib import Path
from loguru import logger
from neo4j import GraphDatabase

# HiveMind Structural Indexer
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
        with self.driver.session() as session:
            session.run(query, params or {})

    def clear_graph(self):
        logger.info("Clearing existing architectural mapping...")
        self.run_query("MATCH (n:ArchNode) DETACH DELETE n")

    def index_requirements(self):
        req_dir = BASE_DIR / "docs" / "requirements"
        if not req_dir.exists(): return
        
        logger.info("Indexing Requirements...")
        for req_file in req_dir.glob("REQ-*.md"):
            req_id = req_file.stem.split("-")[0] + "-" + req_file.stem.split("-")[1]
            with open(req_file, encoding="utf-8") as f:
                content = f.read()
                title_match = re.search(r"# (REQ-.*?): (.*)", content)
                title = title_match.group(2) if title_match else req_file.stem
                
                self.run_query("""
                MERGE (r:ArchNode:Requirement {id: $id})
                SET r.title = $title, r.path = $path, r.type = 'Requirement'
                """, {"id": req_id, "title": title, "path": str(req_file.relative_to(BASE_DIR))})

                # Extract Personnel from Change Log table
                person_matches = re.finditer(r"\| \d{4}-\d{2}-\d{2} \| .*? \| (.*?) \|", content)
                for pm in person_matches:
                    person_name = pm.group(1).strip()
                    if person_name and person_name != "Personnel" and person_name != "人员":
                        self.run_query("""
                        MERGE (p:ArchNode:Person {id: $name})
                        SET p.name = $name, p.type = 'Person'
                        WITH p
                        MATCH (r:Requirement {id: $rid})
                        MERGE (p)-[:AUTHORED]->(r)
                        """, {"name": person_name, "rid": req_id})


    def index_designs(self):
        design_dir = BASE_DIR / "docs" / "architecture"
        if not design_dir.exists(): return
        
        logger.info("Indexing Design Documents...")
        for design_file in design_dir.glob("*.md"):
            # Try to find DES-NNN or other identifier in the content or filename
            with open(design_file, encoding="utf-8") as f:
                content = f.read()
                
                design_id_match = re.search(r"(?:DES|FE-GOV|BE-GOV)-\d+", content)
                design_id = design_id_match.group(0) if design_id_match else design_file.stem
                
                # Link to Requirement
                req_match = re.search(r"REQ-\d+", content)
                req_id = req_match.group(0) if req_match else None
                
                self.run_query("""
                MERGE (d:ArchNode:Design {id: $id})
                SET d.path = $path, d.type = 'Design', d.title = $title
                """, {"id": design_id, "path": str(design_file.relative_to(BASE_DIR)), "title": design_file.stem})
                
                if req_id:
                    self.run_query("""
                    MATCH (d:Design {id: $did}), (r:Requirement {id: $rid})
                    MERGE (d)-[:ADDRESSES]->(r)
                    """, {"did": design_id, "rid": req_id})
                
                # Extract Personnel from Change Log table
                person_matches = re.finditer(r"\| \d{4}-\d{2}-\d{2} \| .*? \| (.*?) \|", content)
                for pm in person_matches:
                    person_name = pm.group(1).strip()
                    if person_name and person_name != "Personnel" and person_name != "人员" and person_name != "Person":
                        self.run_query("""
                        MERGE (p:ArchNode:Person {id: $name})
                        SET p.name = $name, p.type = 'Person'
                        WITH p
                        MATCH (d:Design {id: $did})
                        MERGE (p)-[:CONTRIBUTED_TO]->(d)
                        """, {"name": person_name, "did": design_id})

                # Link to implementation files mentioned in the design
                file_matches = re.findall(r"`(.*?/.*?\.(?:py|js|ts|tsx))`", content)
                for file_path in file_matches:
                    self.run_query("""
                    MATCH (d:Design {id: $did})
                    MERGE (f:ArchNode:File {id: $path})
                    SET f.path = $path, f.type = 'File'
                    MERGE (d)-[:SPECIFIES]->(f)
                    """, {"did": design_id, "path": file_path})


    def index_skills(self):
        registry_file = BASE_DIR / "REGISTRY.md"
        if not registry_file.exists(): return
        
        logger.info("Indexing Skills from Registry...")
        with open(registry_file, encoding="utf-8") as f:
            content = f.read()
            # Parse Skill Table
            skill_section = re.search(r"## \d+\. Agent \+ Skill \+ Workflow 注册表(.*?)###", content, re.DOTALL)
            if skill_section:
                table_lines = skill_section.group(1).strip().split("\n")
                for line in table_lines:
                    if "|" in line and "`" in line:
                        match = re.search(r"\| `(.*?)` \| (.*?) \| `(.*?)` \|", line)
                        if match:
                            name, desc, path = match.groups()
                            self.run_query("""
                            MERGE (s:ArchNode:Skill {id: $id})
                            SET s.name = $id, s.description = $desc, s.path = $path, s.type = 'Skill'
                            """, {"id": name, "desc": desc, "path": path})

    def link_files_to_skills(self):
        # 1. Scan skills directory for scripts
        skills_root = BASE_DIR / "skills"
        if skills_root.exists():
            for skill_dir in skills_root.iterdir():
                if not skill_dir.is_dir(): continue
                skill_name = skill_dir.name
                scripts_dir = skill_dir / "scripts"
                if scripts_dir.exists():
                    for script in scripts_dir.glob("*.py"):
                        self.run_query("""
                        MATCH (s:Skill {id: $sid})
                        MERGE (f:ArchNode:File {id: $path})
                        SET f.path = $path, f.type = 'File'
                        MERGE (s)-[:USES_FILE]->(f)
                        """, {"sid": skill_name, "path": str(script.relative_to(BASE_DIR)).replace("\\", "/")})
        
        # 2. Manual mapping for core scripts registered in REGISTRY
        # This is a fallback/additional check
        scripts_root = BASE_DIR / "backend" / "app" / "scripts"
        if scripts_root.exists():
            for script in scripts_root.glob("*.py"):
                # Guess skill from filename (e.g. github_collab -> github-collaboration)
                if "github_collab" in script.name:
                    self.run_query("""
                    MATCH (s:Skill {id: 'github-collaboration'})
                    MERGE (f:ArchNode:File {id: $path})
                    SET f.path = $path, f.type = 'File'
                    MERGE (s)-[:USES_FILE]->(f)
                    """, {"path": str(script.relative_to(BASE_DIR)).replace("\\", "/")})

    def index_tests(self):
        tests_dir = BASE_DIR / "backend" / "tests"
        if not tests_dir.exists(): return
        
        logger.info("Indexing Tests and creating traceability links...")
        for test_file in tests_dir.rglob("test_*.py"):
            relative_path = str(test_file.relative_to(BASE_DIR)).replace("\\", "/")
            test_id = test_file.stem
            
            self.run_query("""
            MERGE (t:ArchNode:Test {id: $id})
            SET t.path = $path, t.type = 'Test'
            """, {"id": test_id, "path": relative_path})
            
            # Heuristic: Link test_example.py to app/example.py or similar
            target_name = test_file.name.replace("test_", "")
            # Look for matching source file
            source_candidates = list((BASE_DIR / "backend" / "app").rglob(target_name))
            for src in source_candidates:
                src_path = str(src.relative_to(BASE_DIR)).replace("\\", "/")
                self.run_query("""
                MATCH (t:Test {id: $tid}), (f:File {id: $fid})
                MERGE (t)-[:VERIFIES]->(f)
                """, {"tid": test_id, "fid": src_path})
                
            # Parse test content for @covers tags or DES references
            with open(test_file, encoding="utf-8", errors="ignore") as f:
                content = f.read()
                des_matches = re.findall(r"DES-\d+", content)
                for des_id in des_matches:
                    self.run_query("""
                    MATCH (t:Test {id: $tid}), (d:Design {id: $did})
                    MERGE (t)-[:VALIDATES_DESIGN]->(d)
                    """, {"tid": test_id, "did": des_id})

    def index_all_code_files(self):
        logger.info("Indexing all code files and Git history (Batched)...")
        extensions = ["*.py", "*.ts", "*.tsx"]
        files_data = []
        
        for ext in extensions:
            for file_path in BASE_DIR.rglob(ext):
                if ".agent" in str(file_path) or "node_modules" in str(file_path) or ".venv" in str(file_path):
                    continue
                rel_path = str(file_path.relative_to(BASE_DIR)).replace("\\", "/")
                
                commit_msg = ""
                last_author = ""
                commit_date = ""
                commit_count = 0
                try:
                    res = subprocess.run(["git", "log", "-1", "--format=%an|%cd|%s", "--date=short", "--", str(file_path)], capture_output=True, text=True, encoding="utf-8", errors="ignore", cwd=str(BASE_DIR))
                    if res.stdout.strip():
                        parts = res.stdout.strip().split("|", 2)
                        if len(parts) == 3:
                            last_author, commit_date, commit_msg = parts
                    
                    count_res = subprocess.run(["git", "rev-list", "--count", "HEAD", "--", str(file_path)], capture_output=True, text=True, encoding="utf-8", errors="ignore", cwd=str(BASE_DIR))
                    if count_res.stdout.strip():
                        commit_count = int(count_res.stdout.strip())
                except Exception as e:
                    logger.debug(f"Git log failed for {file_path}: {e}")

                files_data.append({
                    "path": rel_path,
                    "ext": file_path.suffix[1:],
                    "commit_msg": commit_msg,
                    "author": last_author,
                    "date": commit_date,
                    "count": commit_count
                })

        # Batch Merge Files
        if files_data:
            self.run_query("""
            UNWIND $batch AS f_info
            MERGE (f:ArchNode:File {id: f_info.path})
            SET f.path = f_info.path, f.type = 'File', f.extension = f_info.ext,
                f.last_commit_msg = f_info.commit_msg, f.last_author = f_info.author,
                f.last_commit_date = f_info.date, f.commit_count = f_info.count
            """, {"batch": files_data})
            logger.info(f"Batched {len(files_data)} files into Neo4j.")

    def index_todo_file(self):
        todo_file = BASE_DIR / "TODO.md"
        if not todo_file.exists(): return
        
        logger.info("Indexing TODO.md tasks...")
        with open(todo_file, encoding="utf-8") as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            # 1. Match List Items: - [ ] **ID** — Description or - [ ] ID — Description
            # Using simpler matching to avoid backtracking
            if line.startswith("- ["):
                status_part = line[3:4]
                content_part = line[6:].strip()
                
                status = "PENDING"
                if status_part in ["x", "✅"]: status = "COMPLETED"
                elif status_part == "🟡": status = "IN_PROGRESS"
                
                # Extract ID and Title
                # Pattern: **ID** — Title or ID — Title
                id_match = re.match(r"(?:\*\*([^*]+)\*\*|([A-Z0-9_-]+))\s*[—：:]\s*(.*)", content_part)
                if id_match:
                    task_id = id_match.group(1) or id_match.group(2)
                    title_full = id_match.group(3)
                else:
                    task_id = None
                    title_full = content_part
                
                # Extract Assignee if present: (协作者: Name)
                assignee_match = re.search(r"（协作者:\s*(.*?)）", title_full)
                assignee = assignee_match.group(1) if assignee_match else "Unassigned"
                title = re.sub(r"（协作者:.*?）", "", title_full).strip()
                
                if not task_id:
                    # Fallback: use first few words as ID if no clear ID pattern
                    task_id = "TASK-" + "".join(filter(str.isalnum, title[:20]))

                self.run_query("""
                MERGE (todo:ArchNode:Todo {id: $id})
                SET todo.title = $title, todo.status = $status, todo.type = 'Todo'
                MERGE (p:ArchNode:Person {id: $person})
                SET p.name = $person, p.type = 'Person'
                MERGE (p)-[:ASSIGNED_TO]->(todo)
                """, {"id": task_id, "title": title, "status": status, "person": assignee})

            # 2. Match Table Rows (specifically for IDs like TASK- or ARM- or FE-GOV-)
            elif line.startswith("|") and not line.startswith("|---"):
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 4:
                    # Check if first or second col looks like an ID
                    col1, col2, col3 = parts[1], parts[2], parts[3]
                    if re.match(r"^[A-Z0-9_-]+$", col1) and col1 not in ["层级", "角色", "编号"]:
                        self.run_query("""
                        MERGE (todo:ArchNode:Todo {id: $id})
                        SET todo.title = $title, todo.status = 'PENDING', todo.type = 'Todo'
                        MERGE (p:ArchNode:Person {id: $person})
                        SET p.name = $person, p.type = 'Person'
                        MERGE (p)-[:ASSIGNED_TO]->(todo)
                        """, {"id": col1, "title": col2, "person": col3})

    def index_database_seeding(self):


        # Manually sync from init_data.py to show deeper integration
        logger.info("Syncing manual seeding tasks...")
        # ... already captured by TODO.md mainly, but keeping specific links
        pass


    def index_python_ast(self):
        logger.info("Indexing Python AST for fine-grained call graphs (Batched)...")
        codebase_dir = BASE_DIR / "backend"
        all_definitions = []
        all_calls = []
        
        for py_file in codebase_dir.rglob("*.py"):
            if ".agent" in str(py_file) or ".venv" in str(py_file) or "site-packages" in str(py_file):
                continue
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    file_content = f.read()
                    if not file_content.strip(): continue
                    tree = ast.parse(file_content, filename=str(py_file))
                    
                file_id = str(py_file.relative_to(BASE_DIR)).replace("\\", "/")
                
                class ASTExtractor(ast.NodeVisitor):
                    def __init__(self):
                        self.current_class = None
                        self.current_function = None
                        self.definitions = [] # (type, name, docstring)
                        self.calls = [] # (caller_id, callee_name)
                        
                    def visit_ClassDef(self, node):
                        old_class = self.current_class
                        self.current_class = node.name
                        docstring = ast.get_docstring(node)
                        self.definitions.append(("Class", node.name, docstring or ""))
                        self.generic_visit(node)
                        self.current_class = old_class
                        
                    def visit_FunctionDef(self, node):
                        old_func = self.current_function
                        name = f"{self.current_class}.{node.name}" if self.current_class else node.name
                        self.current_function = name
                        docstring = ast.get_docstring(node)
                        self.definitions.append(("Function", name, docstring or ""))
                        self.generic_visit(node)
                        self.current_function = old_func
                        
                    def visit_Call(self, node):
                        if self.current_function:
                            caller_id = f"{file_id}::{self.current_function}"
                            if isinstance(node.func, ast.Name):
                                callee = node.func.id
                                self.calls.append((caller_id, callee))
                            elif isinstance(node.func, ast.Attribute):
                                callee = node.func.attr
                                self.calls.append((caller_id, callee))
                        self.generic_visit(node)

                extractor = ASTExtractor()
                extractor.visit(tree)
                
                for def_type, name, docstring in extractor.definitions:
                    all_definitions.append({
                        "id": f"{file_id}::{name}",
                        "name": name,
                        "def_type": def_type,
                        "file": file_id,
                        "docstring": docstring
                    })
                    
                for caller_id, callee_name in extractor.calls:
                    all_calls.append({
                        "caller_id": caller_id,
                        "callee_name": callee_name
                    })
                    
            except Exception as e:
                logger.warning(f"Failed to parse AST for {py_file}: {e}")

        # Batch 1: Create all Code Entities
        if all_definitions:
            logger.info(f"Batched merge for {len(all_definitions)} code entities...")
            self.run_query("""
            UNWIND $batch AS item
            MERGE (n:ArchNode:CodeEntity {id: item.id})
            SET n.name = item.name, n.type = item.def_type, n.file = item.file, n.docstring = item.docstring
            WITH n, item
            MATCH (f:File {id: item.file})
            MERGE (f)-[:CONTAINS]->(n)
            """, {"batch": all_definitions})

        # Batch 2: Create Calls (limit scope for performance)
        if all_calls:
            logger.info(f"Batched merge for {len(all_calls)} calls...")
            # Limit to 1000 at a time if too large
            for i in range(0, len(all_calls), 1000):
                self.run_query("""
                UNWIND $batch AS item
                MATCH (caller:CodeEntity {id: item.caller_id})
                MATCH (callee:CodeEntity {name: item.callee_name})
                MERGE (caller)-[:CALLS]->(callee)
                """, {"batch": all_calls[i:i+1000]})

    def index_database_models(self):
        logger.info("Indexing Database Models (Batched)...")
        models_dir = BASE_DIR / "backend" / "app" / "models"
        if not models_dir.exists(): return
        
        all_models = []
        all_columns = []
            
        for py_file in models_dir.glob("*.py"):
            if py_file.name == "__init__.py": continue
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    tree = ast.parse(f.read(), filename=str(py_file))
                    
                file_id = str(py_file.relative_to(BASE_DIR)).replace("\\", "/")
                
                for node in tree.body:
                    if isinstance(node, ast.ClassDef):
                        model_name = node.name
                        all_models.append({"id": model_name, "name": model_name, "file": file_id})
                        
                        for stmt in node.body:
                            field_name = None
                            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                                field_name = stmt.target.id
                            elif isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                                field_name = stmt.targets[0].id
                                
                            if field_name and field_name != "__tablename__":
                                all_columns.append({"mid": model_name, "cid": f"{model_name}.{field_name}", "name": field_name})
                                
            except Exception as e:
                logger.warning(f"Failed to parse DB model in {py_file}: {e}")

        if all_models:
            self.run_query("""
            UNWIND $batch AS item
            MERGE (m:ArchNode:DatabaseModel {id: item.id})
            SET m.name = item.name, m.type = 'DatabaseModel'
            WITH m, item
            MATCH (f:File {id: item.file})
            MERGE (f)-[:DEFINES_MODEL]->(m)
            """, {"batch": all_models})

        if all_columns:
            self.run_query("""
            UNWIND $batch AS item
            MATCH (m:DatabaseModel {id: item.mid})
            MERGE (col:ArchNode:DatabaseColumn {id: item.cid})
            SET col.name = item.name, col.type = 'DatabaseColumn'
            MERGE (m)-[:HAS_COLUMN]->(col)
            """, {"batch": all_columns})

def main():
    # Load env for Neo4j
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / "backend" / ".env")
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j123")
    
    indexer = ArchitectureIndexer(uri, user, password)
    indexer.clear_graph()
    indexer.index_requirements()
    indexer.index_designs()
    indexer.index_all_code_files() # New step: scan all codebase
    indexer.index_skills()
    indexer.link_files_to_skills()
    indexer.index_tests()
    indexer.index_database_seeding() # New step: sync from DB seeding
    indexer.index_todo_file() # New step: scan TODO.md
    
    # Advanced Code Introspection
    indexer.index_database_models()
    indexer.index_python_ast()

    indexer.close()

    logger.success("Architectural Mapping Complete!")

if __name__ == "__main__":
    main()
