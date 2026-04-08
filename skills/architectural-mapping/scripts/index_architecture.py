import os
import re
import json
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
            match = re.match(r"REQ-\d+", req_file.stem)
            if not match: continue
            req_id = match.group(0)
            
            with open(req_file, encoding="utf-8") as f:
                content = f.read()
                title_match = re.search(r"# (REQ-.*?): (.*)", content)
                title = title_match.group(2) if title_match else req_file.stem
                
                self.run_query("""
                MERGE (r:ArchNode:Requirement {id: $id})
                SET r.title = $title, r.path = $path, r.type = 'Requirement'
                """, {"id": req_id, "title": title, "path": str(req_file.relative_to(BASE_DIR))})

    def index_designs(self):
        design_dir = BASE_DIR / "docs" / "architecture"
        if not design_dir.exists(): return
        
        logger.info("Indexing Design Documents...")
        for design_file in design_dir.glob("*.md"):
            design_id = design_file.stem
            with open(design_file, encoding="utf-8") as f:
                content = f.read()
                
                # Link to Requirement (find REQ-001 pattern)
                req_match = re.search(r"REQ-\d+", content)
                req_id = req_match.group(0) if req_match else None
                
                self.run_query("""
                MERGE (d:ArchNode:Design {id: $id})
                SET d.path = $path, d.type = 'Design'
                """, {"id": design_id, "path": str(design_file.relative_to(BASE_DIR))})
                
                if req_id:
                    self.run_query("""
                    MATCH (d:Design {id: $did}), (r:Requirement {id: $rid})
                    MERGE (d)-[:ADDRESSES]->(r)
                    """, {"did": design_id, "rid": req_id})
                
                # Link to implementation files mentioned in the design
                file_matches = re.findall(r"`(app/.*?\.(?:py|js|ts))`", content)
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

    def index_source_code(self):
        logger.info("Indexing source code files (py, ts, tsx)...")
        # backend
        for py_file in (BASE_DIR / "backend" / "app").rglob("*.py"):
            if "__pycache__" in str(py_file): continue
            relative_path = str(py_file.relative_to(BASE_DIR)).replace("\\", "/")
            self.run_query("""
            MERGE (f:ArchNode:File {id: $path})
            SET f.path = $path, f.type = 'File'
            """, {"path": relative_path})
            
        # frontend
        for ts_file in (BASE_DIR / "frontend" / "src").rglob("*.[tj]s*"):
            if "node_modules" in str(ts_file): continue
            relative_path = str(ts_file.relative_to(BASE_DIR)).replace("\\", "/")
            self.run_query("""
            MERGE (f:ArchNode:File {id: $path})
            SET f.path = $path, f.type = 'File'
            """, {"path": relative_path})

    def index_dependencies(self):
        logger.info("Indexing Package Dependencies (Supply Chain)...")
        # 1. Backend: requirements.txt
        req_file = BASE_DIR / "backend" / "requirements.txt"
        if req_file.exists():
            rel_path = str(req_file.relative_to(BASE_DIR)).replace("\\", "/")
            with open(req_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        pkg_match = re.match(r"^([a-zA-Z0-9_\-]+)", line)
                        if pkg_match:
                            pkg_name = pkg_match.group(1).lower()
                            self.run_query("""
                            MERGE (p:ArchNode:Package {id: $pkg})
                            SET p.name = $pkg, p.type = 'Package'
                            WITH p
                            MERGE (f:ArchNode:File {id: $path})
                            SET f.path = $path, f.type = 'File'
                            MERGE (f)-[:IMPORTS]->(p)
                            """, {"pkg": pkg_name, "path": rel_path})

        # 2. Frontend: package.json
        pkg_json = BASE_DIR / "frontend" / "package.json"
        if pkg_json.exists():
            rel_path = str(pkg_json.relative_to(BASE_DIR)).replace("\\", "/")
            try:
                import json
                with open(pkg_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                    for pkg_name, version in deps.items():
                        self.run_query("""
                        MERGE (p:ArchNode:Package {id: $pkg})
                        SET p.name = $pkg, p.version = $version, p.type = 'Package'
                        WITH p
                        MERGE (f:ArchNode:File {id: $path})
                        SET f.path = $path, f.type = 'File'
                        MERGE (f)-[:IMPORTS]->(p)
                        """, {"pkg": pkg_name, "version": str(version), "path": rel_path})
            except Exception as e:
                logger.warning(f"Failed to parse package.json: {e}")


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
    indexer.index_source_code()
    indexer.index_dependencies()
    indexer.index_skills()
    indexer.link_files_to_skills()
    indexer.index_tests()
    indexer.close()
    logger.success("Architectural Mapping Complete!")

if __name__ == "__main__":
    main()
