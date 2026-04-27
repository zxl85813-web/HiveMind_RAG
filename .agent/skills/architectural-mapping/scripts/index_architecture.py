import os
import re
import json
import ast
import subprocess
import hashlib
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from datetime import datetime
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
        if not self.driver: return []
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
                    
                    # 🛰️ [Harden]: Always refresh Git Authorship & History nodes
                    commit_info = {"author": "Unknown", "date": "", "msg": "", "count": 0, "hash": "HEAD"}
                    try:
                        res = subprocess.run(["git", "log", "-1", "--format=%an|%cd|%s|%H", "--date=short", "--", str(file_path)], capture_output=True, text=True, encoding="utf-8", errors="ignore", cwd=str(BASE_DIR))
                        if res.stdout.strip():
                            parts = res.stdout.strip().split("|", 3)
                            if len(parts) == 4:
                                commit_info["author"], commit_info["date"], commit_info["msg"], commit_info["hash"] = parts
                        
                        count_res = subprocess.run(["git", "rev-list", "--count", "HEAD", "--", str(file_path)], capture_output=True, text=True, encoding="utf-8", errors="ignore", cwd=str(BASE_DIR))
                        if count_res.stdout.strip():
                            commit_info["count"] = int(count_res.stdout.strip())
                    except Exception: pass

                    self.run_query("""
                    MERGE (f:ArchNode:File {id: $id})
                    SET f.path = $id, f.type = 'File', f.extension = $ext, f.hash = $hash,
                        f.last_author = $author, f.last_commit_date = $date, 
                        f.last_commit_msg = $msg, f.commit_count = $count
                    
                    // 1. Create Person node and link
                    MERGE (p:ArchNode:Person {name: $author})
                    SET p.id = $author, p.type = 'Person'
                    MERGE (p)-[:COMMITTED]->(f)
                    
                    // 2. Create Commit node and link
                    MERGE (c:ArchNode:Commit {id: $commit_hash})
                    SET c.message = $msg, c.date = $date, c.type = 'Commit'
                    MERGE (p)-[:COMMITTED]->(c)
                    MERGE (c)-[:MODIFIED]->(f)

                    // 3. Reverse linkage
                    MERGE (f)-[:AUTHORED_BY]->(p)
                    """, {
                        "id": rel_path, "ext": file_path.suffix[1:], "hash": curr_hash,
                        "author": commit_info["author"], "date": commit_info["date"],
                        "msg": commit_info["msg"], "count": commit_info["count"],
                        "commit_hash": commit_info["hash"]
                    })

                    # Now check if we need intensive content indexing (AST/Requirements)
                    existing = self.run_query("MATCH (f:File {id: $id}) RETURN f.hash as hash", {"id": rel_path})
                    if existing and existing[0].get("hash") == curr_hash:
                        # Skip intensive extraction if content same
                        continue

                    logger.debug(f"Indexing changed file content: {rel_path}")
                    
                    # Check for Requirement linkage in file content
                    req_links = []
                    try:
                        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                            text = f.read()
                            req_links = re.findall(r"REQ-\d+", text)
                    except Exception: pass
                    
                    for rid in set(req_links):
                        self.run_query("""
                        MATCH (f:File {id: $fid}), (r:Requirement {id: $rid})
                        MERGE (r)-[:IMPLEMENTED_BY]->(f)
                        """, {"fid": rel_path, "rid": rid})

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
        query_string = """
        (import_statement source: (string) @import_src)
        (function_declaration name: (identifier) @comp_name) @comp_node
        (variable_declarator name: (identifier) @comp_name 
            value: [ (arrow_function) (function_expression) ]) @comp_node
        (variable_declarator name: (array_pattern (identifier) @state_val (identifier) @state_set)
          value: (call_expression function: (identifier) @hook_name (#eq? @hook_name "useState"))) @state_node
        (call_expression function: (identifier) @store_hook (#match? @store_hook "use.*Store")) @store_node
        (jsx_opening_element name: [(identifier) @jsx_tag (member_expression) @jsx_tag]) @jsx_node
        """
        try:
            # Standard API (0.21.x+)
            from tree_sitter import Language, Parser
            TSX_LANGUAGE = Language(ts_typescript.language_tsx())
            parser = Parser(TSX_LANGUAGE)
            query = TSX_LANGUAGE.query(query_string)
        except Exception as e:
            logger.debug(f"Tree-sitter 0.21 fallback: {e}")
            try:
                # Alt API / Custom build
                TSX_LANGUAGE = ts_typescript.language_tsx()
                parser = Parser()
                if hasattr(parser, 'set_language'):
                    parser.set_language(TSX_LANGUAGE)
                else:
                    parser.language = TSX_LANGUAGE
                query = TSX_LANGUAGE.query(query_string)
            except Exception as e2:
                logger.error(f"Failed to initialize tree-sitter TSX: {e2}")
                return
        
        fe_dir = BASE_DIR / "frontend" / "src"
        if not fe_dir.exists(): return
        
        for ts_file in fe_dir.rglob("*.tsx"):
            if "node_modules" in str(ts_file): continue
            rel_path = str(ts_file.relative_to(BASE_DIR)).replace("\\", "/")
            
            try:
                with open(ts_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                
                # Cleanup existing entities for THIS file before re-indexing
                self.run_query("MATCH (:File {id: $id})-[:DEFINES_COMPONENT|CONTAINS|DEPENDS_ON]->(child) DETACH DELETE child WHERE NOT child:File", {"id": rel_path})
                # Note: We don't want to double DETACH DELETE files themselves, just the relationships
                self.run_query("MATCH (:File {id: $id})-[r:DEPENDS_ON]->(:File) DELETE r", {"id": rel_path})

                tree = parser.parse(bytes(content, "utf8"))
                cursor = QueryCursor()
                captures = cursor.captures(query, tree.root_node)
                
                components = {}
                states = []; stores = []; jsx_tags = []; imports = []

                for node, tag in captures:
                    if tag == "import_src":
                        src = node.text.decode("utf8").strip("'\"")
                        if src.startswith("."): # Relative import
                            imports.append(src)
                    elif tag == "comp_node":
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

                # 🛠️ [Linkage]: Frontend File-level dependencies
                for imp in set(imports):
                    # Resolve relative path
                    target_file = Path(ts_file.parent / imp).resolve()
                    # Try possible extensions
                    for ext in [".tsx", ".ts", ".js", ".jsx"]:
                        full_path = target_file.with_suffix(ext)
                        if full_path.exists():
                            try:
                                target_rel = str(full_path.relative_to(BASE_DIR)).replace("\\", "/")
                                self.run_query("""
                                MATCH (f:File {id: $fid}), (t:File {id: $tid})
                                MERGE (f)-[:DEPENDS_ON]->(t)
                                """, {"fid": rel_path, "tid": target_rel})
                                break
                            except Exception: pass

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
                        self.imports = []
                    def visit_Import(self, node):
                        for alias in node.names: self.imports.append(alias.name)
                        self.generic_visit(node)
                    def visit_ImportFrom(self, node):
                        if node.module: self.imports.append(node.module)
                        self.generic_visit(node)
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
                
                # 🛠️ [Linkage]: File-to-File Dependencies via Imports
                for imp in set(visitor.imports):
                    # Convert module path to expected file ID snippet
                    # e.g., app.api.routes -> backend/app/api/routes
                    target_snip = imp.replace(".", "/")
                    self.run_query("""
                    MATCH (f:File {id: $fid})
                    MATCH (target:File) 
                    WHERE target.id CONTAINS $snip AND target <> f
                    MERGE (f)-[:DEPENDS_ON]->(target)
                    """, {"fid": rel_path, "snip": target_snip})

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

    # ─── GitHub Integration: PR / Review / Release ─────────────────────────────

    def _github_api(self, endpoint: str) -> list[dict] | dict | None:
        """
        Call GitHub REST API with pagination support.
        Reuses existing GITHUB_TOKEN / GITHUB_REPO_OWNER / GITHUB_REPO_NAME from settings or env.
        """
        token = os.getenv("GITHUB_TOKEN", "")
        # Support both combined GITHUB_REPO="owner/repo" and split OWNER+NAME
        repo = os.getenv("GITHUB_REPO", "")
        if not repo:
            owner = os.getenv("GITHUB_REPO_OWNER", "")
            name = os.getenv("GITHUB_REPO_NAME", "")
            if owner and name:
                repo = f"{owner}/{name}"
        if not token or not repo:
            return None

        base_url = f"https://api.github.com/repos/{repo}"
        url = f"{base_url}{endpoint}"
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        all_results = []
        page = 1
        while True:
            sep = "&" if "?" in url else "?"
            paged_url = f"{url}{sep}page={page}&per_page=100"
            try:
                req = urllib.request.Request(paged_url, headers=headers)
                with urllib.request.urlopen(req, timeout=30) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    if isinstance(data, list):
                        if not data:
                            break
                        all_results.extend(data)
                        page += 1
                    else:
                        return data  # Single object endpoint
            except Exception as e:
                logger.warning(f"GitHub API error for {endpoint}: {e}")
                break

        return all_results

    def _gh_cli_available(self) -> bool:
        """Check if gh CLI is available as a fallback."""
        try:
            res = subprocess.run(
                ["gh", "--version"], capture_output=True, text=True, timeout=5
            )
            return res.returncode == 0
        except Exception:
            return False

    def _gh_cli_json(self, args: list[str]) -> list[dict] | None:
        """Run gh CLI command and return parsed JSON."""
        try:
            res = subprocess.run(
                ["gh"] + args,
                capture_output=True, text=True, encoding="utf-8",
                errors="ignore", timeout=60, cwd=str(BASE_DIR),
            )
            if res.returncode == 0 and res.stdout.strip():
                return json.loads(res.stdout)
        except Exception as e:
            logger.warning(f"gh CLI error: {e}")
        return None

    def index_github_prs(self, limit: int = 200):
        """
        Index Pull Requests and their Reviews into Neo4j.

        Creates:
          (:PullRequest) nodes with status, title, url, timestamps
          (:Review) nodes with verdict, reviewer info
          Person -[:AUTHORED_PR]-> PullRequest
          PullRequest -[:MODIFIES]-> File
          PullRequest -[:HAS_REVIEW]-> Review
          Person -[:REVIEWED]-> Review
        """
        logger.info("📡 Indexing GitHub Pull Requests & Reviews...")

        # Strategy: try GitHub REST API first, fall back to gh CLI
        prs = self._github_api(f"/pulls?state=all&sort=updated&direction=desc&per_page={min(limit, 100)}")

        if prs is None and self._gh_cli_available():
            logger.info("Falling back to gh CLI for PR data...")
            prs = self._gh_cli_json([
                "pr", "list", "--state", "all", "--limit", str(limit),
                "--json", "number,title,state,author,createdAt,mergedAt,closedAt,url,headRefName,files,reviewDecision"
            ])

        if not prs:
            logger.warning("No PR data available. Set GITHUB_TOKEN + GITHUB_REPO_OWNER/GITHUB_REPO_NAME env vars, or install gh CLI.")
            return

        pr_count = 0
        review_count = 0

        for pr in prs[:limit]:
            # Normalize field names (REST API vs gh CLI have different schemas)
            pr_number = pr.get("number")
            pr_title = pr.get("title", "")
            pr_url = pr.get("url") or pr.get("html_url", "")
            pr_branch = pr.get("headRefName") or (pr.get("head", {}) or {}).get("ref", "")

            # Status normalization
            pr_state = pr.get("state", "").upper()
            if pr.get("mergedAt") or pr.get("merged_at"):
                pr_state = "MERGED"
            elif pr_state == "CLOSED":
                pr_state = "CLOSED"
            else:
                pr_state = "OPEN"

            # Author
            author_data = pr.get("author") or pr.get("user") or {}
            author_name = author_data.get("login", "unknown")

            # Timestamps
            created_at = pr.get("createdAt") or pr.get("created_at", "")
            merged_at = pr.get("mergedAt") or pr.get("merged_at", "")

            pr_id = f"PR-{pr_number}"

            # 1. Create PullRequest node + link to author
            self.run_query("""
                MERGE (pr:ArchNode:PullRequest {id: $id})
                SET pr.number = $number,
                    pr.title = $title,
                    pr.status = $status,
                    pr.url = $url,
                    pr.branch = $branch,
                    pr.created_at = $created_at,
                    pr.merged_at = $merged_at,
                    pr.type = 'PullRequest',
                    pr.indexed_at = $now

                MERGE (p:ArchNode:Person {name: $author})
                SET p.id = $author, p.type = 'Person'
                MERGE (p)-[:AUTHORED_PR]->(pr)
            """, {
                "id": pr_id, "number": pr_number, "title": pr_title,
                "status": pr_state, "url": pr_url, "branch": pr_branch,
                "created_at": created_at, "merged_at": merged_at,
                "author": author_name, "now": datetime.now().isoformat(),
            })
            pr_count += 1

            # 2. Link PR to modified files
            files_data = pr.get("files")
            if files_data is None:
                # REST API: need separate call for files
                files_data = self._github_api(f"/pulls/{pr_number}/files")

            if files_data:
                for f in files_data[:50]:  # Cap at 50 files per PR
                    file_path = f.get("filename") or f.get("path", "")
                    if not file_path:
                        continue
                    # Normalize path
                    file_path = file_path.replace("\\", "/")
                    self.run_query("""
                        MATCH (pr:PullRequest {id: $pr_id})
                        MATCH (f:File {id: $fpath})
                        MERGE (pr)-[r:MODIFIES]->(f)
                        SET r.additions = $additions,
                            r.deletions = $deletions,
                            r.status = $change_status
                    """, {
                        "pr_id": pr_id,
                        "fpath": file_path,
                        "additions": f.get("additions", 0),
                        "deletions": f.get("deletions", 0),
                        "change_status": f.get("status", "modified"),
                    })

            # 3. Index Reviews for this PR
            reviews = self._github_api(f"/pulls/{pr_number}/reviews")
            if reviews is None and self._gh_cli_available():
                reviews = self._gh_cli_json([
                    "pr", "view", str(pr_number),
                    "--json", "reviews",
                ])
                if reviews and isinstance(reviews, dict):
                    reviews = reviews.get("reviews", [])

            if reviews:
                for rv in reviews:
                    reviewer_data = rv.get("user") or rv.get("author") or {}
                    reviewer = reviewer_data.get("login", "unknown")
                    verdict = (rv.get("state") or "").upper()
                    # Normalize: APPROVED, CHANGES_REQUESTED, COMMENTED, DISMISSED
                    rv_id = f"{pr_id}::review::{reviewer}::{verdict}"
                    submitted_at = rv.get("submitted_at") or rv.get("submittedAt", "")
                    body = (rv.get("body") or "")[:500]  # Truncate long review bodies

                    self.run_query("""
                        MERGE (rv:ArchNode:Review {id: $rv_id})
                        SET rv.reviewer = $reviewer,
                            rv.verdict = $verdict,
                            rv.submitted_at = $submitted_at,
                            rv.body_snippet = $body,
                            rv.type = 'Review'

                        WITH rv
                        MATCH (pr:PullRequest {id: $pr_id})
                        MERGE (pr)-[:HAS_REVIEW]->(rv)

                        WITH rv
                        MERGE (p:ArchNode:Person {name: $reviewer})
                        SET p.id = $reviewer, p.type = 'Person'
                        MERGE (p)-[:REVIEWED]->(rv)
                    """, {
                        "rv_id": rv_id, "reviewer": reviewer, "verdict": verdict,
                        "submitted_at": submitted_at, "body": body, "pr_id": pr_id,
                    })
                    review_count += 1

            # 4. Link PR to Requirements (parse PR title/body for REQ-NNN)
            pr_body = pr.get("body") or ""
            req_refs = set(re.findall(r"REQ-\d+", f"{pr_title} {pr_body}"))
            for rid in req_refs:
                self.run_query("""
                    MATCH (pr:PullRequest {id: $pr_id}), (r:Requirement {id: $rid})
                    MERGE (pr)-[:ADDRESSES]->(r)
                """, {"pr_id": pr_id, "rid": rid})

        logger.info(f"✅ Indexed {pr_count} PRs and {review_count} reviews.")

    def index_github_releases(self, limit: int = 50):
        """
        Index GitHub Releases/Tags into Neo4j.

        Creates:
          (:Release) nodes with version, tag, environment, timestamps
          Release -[:INCLUDES_PR]-> PullRequest  (via merge commit matching)
          Person -[:PUBLISHED]-> Release
        """
        logger.info("📡 Indexing GitHub Releases...")

        releases = self._github_api("/releases?per_page=50")
        if releases is None and self._gh_cli_available():
            releases = self._gh_cli_json([
                "release", "list", "--limit", str(limit),
                "--json", "tagName,name,publishedAt,author,isPrerelease,isDraft,url"
            ])

        if not releases:
            logger.warning("No release data available.")
            return

        rel_count = 0
        for rel in releases[:limit]:
            tag = rel.get("tagName") or rel.get("tag_name", "")
            name = rel.get("name") or tag
            published_at = rel.get("publishedAt") or rel.get("published_at", "")
            is_prerelease = rel.get("isPrerelease") or rel.get("prerelease", False)
            is_draft = rel.get("isDraft") or rel.get("draft", False)
            url = rel.get("url") or rel.get("html_url", "")
            author_data = rel.get("author") or {}
            author = author_data.get("login", "unknown")

            env = "production"
            if is_draft:
                env = "draft"
            elif is_prerelease:
                env = "staging"

            rel_id = f"RELEASE-{tag}"

            self.run_query("""
                MERGE (rel:ArchNode:Release {id: $id})
                SET rel.tag = $tag,
                    rel.name = $name,
                    rel.environment = $env,
                    rel.published_at = $published_at,
                    rel.url = $url,
                    rel.type = 'Release',
                    rel.indexed_at = $now

                MERGE (p:ArchNode:Person {name: $author})
                SET p.id = $author, p.type = 'Person'
                MERGE (p)-[:PUBLISHED]->(rel)
            """, {
                "id": rel_id, "tag": tag, "name": name, "env": env,
                "published_at": published_at, "url": url,
                "author": author, "now": datetime.now().isoformat(),
            })
            rel_count += 1

            # Link release to PRs merged between this and previous release
            # Use tag comparison via git log
            try:
                # Get commits in this release
                res = subprocess.run(
                    ["git", "log", f"{tag}", "--oneline", "--merges", "-n", "50"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="ignore", timeout=15, cwd=str(BASE_DIR),
                )
                if res.returncode == 0:
                    # Extract PR numbers from merge commit messages: "Merge pull request #123"
                    pr_numbers = re.findall(r"#(\d+)", res.stdout)
                    for pr_num in set(pr_numbers):
                        self.run_query("""
                            MATCH (rel:Release {id: $rel_id})
                            MATCH (pr:PullRequest {number: $pr_num})
                            MERGE (rel)-[:INCLUDES_PR]->(pr)
                        """, {"rel_id": rel_id, "pr_num": int(pr_num)})
            except Exception:
                pass

        logger.info(f"✅ Indexed {rel_count} releases.")

    def build_developer_profiles(self):
        """
        Aggregate developer metrics from existing graph data into DeveloperProfile nodes.

        Computes:
          - commit_count: total commits
          - pr_count: total PRs authored
          - review_count: total reviews given
          - approval_rate: % of their PRs that got APPROVED
          - merge_rate: % of their PRs that are MERGED
          - primary_domains: top file directories they work in
          - avg_pr_size: average additions+deletions per PR
        """
        logger.info("👤 Building Developer Profiles...")

        # Get all persons
        persons = self.run_query("MATCH (p:Person) RETURN p.name AS name")
        if not persons:
            return

        profile_count = 0
        for person in persons:
            name = person["name"]
            if not name or name == "Unknown":
                continue

            # Aggregate metrics via Cypher
            metrics = self.run_query("""
                MATCH (p:Person {name: $name})

                // Commit count
                OPTIONAL MATCH (p)-[:COMMITTED]->(f:File)
                WITH p, count(DISTINCT f) AS commit_files

                // PR metrics
                OPTIONAL MATCH (p)-[:AUTHORED_PR]->(pr:PullRequest)
                WITH p, commit_files,
                     count(pr) AS pr_count,
                     count(CASE WHEN pr.status = 'MERGED' THEN 1 END) AS merged_prs

                // Review metrics (reviews given by this person)
                OPTIONAL MATCH (p)-[:REVIEWED]->(rv:Review)
                WITH p, commit_files, pr_count, merged_prs,
                     count(rv) AS reviews_given

                // Approval rate on their own PRs
                OPTIONAL MATCH (p)-[:AUTHORED_PR]->(pr2:PullRequest)-[:HAS_REVIEW]->(rv2:Review)
                WHERE rv2.verdict = 'APPROVED'
                WITH p, commit_files, pr_count, merged_prs, reviews_given,
                     count(DISTINCT pr2) AS approved_prs

                // Primary domains (top directories)
                OPTIONAL MATCH (p)-[:COMMITTED]->(f2:File)
                WITH p, commit_files, pr_count, merged_prs, reviews_given, approved_prs,
                     collect(DISTINCT f2.path) AS file_paths

                RETURN commit_files, pr_count, merged_prs, reviews_given, approved_prs, file_paths
            """, {"name": name})

            if not metrics:
                continue

            m = metrics[0]
            commit_files = m.get("commit_files", 0)
            pr_count = m.get("pr_count", 0)
            merged_prs = m.get("merged_prs", 0)
            reviews_given = m.get("reviews_given", 0)
            approved_prs = m.get("approved_prs", 0)
            file_paths = m.get("file_paths", [])

            merge_rate = round(merged_prs / pr_count, 3) if pr_count > 0 else 0.0
            approval_rate = round(approved_prs / pr_count, 3) if pr_count > 0 else 0.0

            # Extract primary domains from file paths
            domain_counter: dict[str, int] = {}
            for fp in file_paths:
                if fp:
                    parts = fp.split("/")
                    domain = "/".join(parts[:3]) if len(parts) >= 3 else "/".join(parts[:2])
                    domain_counter[domain] = domain_counter.get(domain, 0) + 1

            top_domains = sorted(domain_counter.items(), key=lambda x: x[1], reverse=True)[:5]
            primary_domains = [d[0] for d in top_domains]

            profile_id = f"PROFILE-{name}"
            self.run_query("""
                MERGE (prof:ArchNode:DeveloperProfile {id: $id})
                SET prof.name = $name,
                    prof.commit_files = $commit_files,
                    prof.pr_count = $pr_count,
                    prof.merged_prs = $merged_prs,
                    prof.merge_rate = $merge_rate,
                    prof.approval_rate = $approval_rate,
                    prof.reviews_given = $reviews_given,
                    prof.primary_domains = $primary_domains,
                    prof.type = 'DeveloperProfile',
                    prof.updated_at = $now

                WITH prof
                MATCH (p:Person {name: $name})
                MERGE (p)-[:HAS_PROFILE]->(prof)
            """, {
                "id": profile_id, "name": name,
                "commit_files": commit_files, "pr_count": pr_count,
                "merged_prs": merged_prs, "merge_rate": merge_rate,
                "approval_rate": approval_rate, "reviews_given": reviews_given,
                "primary_domains": primary_domains,
                "now": datetime.now().isoformat(),
            })
            profile_count += 1

        logger.info(f"✅ Built {profile_count} developer profiles.")

    def index_code_similarity(self, threshold: float = 0.65):
        """
        Run AST-based code similarity scan and write SIMILAR_TO relationships.
        Integrates with the existing code_similarity_tool.py logic.
        """
        logger.info(f"🔍 Running code similarity scan (threshold={threshold})...")

        # Import the similarity scanner from the co-located tool
        try:
            from code_similarity_tool import scan_codebase_similarity
        except ImportError:
            # Try adding the skills script directory to path
            import sys
            candidates = [
                str(Path(__file__).parent),
                str(BASE_DIR / "skills" / "architectural-mapping" / "scripts"),
                str(BASE_DIR / ".agent" / "skills" / "architectural-mapping" / "scripts"),
            ]
            for candidate in candidates:
                if candidate not in sys.path:
                    sys.path.insert(0, candidate)
            try:
                from code_similarity_tool import scan_codebase_similarity
            except ImportError:
                logger.warning("code_similarity_tool.py not found. Skipping similarity scan.")
                return

        results = scan_codebase_similarity(
            search_dir=str(BASE_DIR),
            threshold=threshold,
            min_len=10,
            lang="all",
            neo4j_driver=self.driver,
        )
        logger.info(f"✅ Similarity scan complete: {len(results)} pairs found.")

    # ─── Business Flow Graph: Pages / Navigation / State Conditions ──────────

    def index_page_routes(self):
        """
        Parse frontend route configuration to create Page nodes and access control relationships.

        Creates:
          (:Page) nodes with path, name, category, permissions
          Page -[:HOSTS]-> UIElement  (page contains component)
          Page -[:REQUIRES_PERMISSION]-> Permission
        """
        logger.info("🗺️  Indexing Page routes from appRoutes config...")

        # 1. Parse publicRoutes.ts and protectedRoutes.ts
        route_files = [
            BASE_DIR / "frontend" / "src" / "config" / "routes" / "modules" / "publicRoutes.ts",
            BASE_DIR / "frontend" / "src" / "config" / "routes" / "modules" / "protectedRoutes.ts",
        ]

        page_count = 0
        for route_file in route_files:
            if not route_file.exists():
                continue
            try:
                with open(route_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract route objects: { key: '...', path: '...', labelKey: '...', ... }
                # Pattern matches each object in the array
                route_pattern = re.compile(
                    r"\{\s*"
                    r"key:\s*['\"](\w+)['\"].*?"
                    r"path:\s*['\"]([^'\"]+)['\"].*?"
                    r"labelKey:\s*['\"]([^'\"]+)['\"].*?"
                    r"icon:\s*['\"]([^'\"]+)['\"].*?"
                    r"showInMenu:\s*(true|false)"
                    r"(?:.*?category:\s*['\"](\w+)['\"])?"
                    r"(?:.*?anyPermissions:\s*\[([^\]]*)\])?"
                    r".*?\}",
                    re.DOTALL,
                )

                for match in route_pattern.finditer(content):
                    key = match.group(1)
                    path = match.group(2)
                    label_key = match.group(3)
                    icon = match.group(4)
                    show_in_menu = match.group(5) == "true"
                    category = match.group(6) or "general"
                    permissions_raw = match.group(7) or ""

                    # Parse permissions list
                    permissions = [
                        p.strip().strip("'\"")
                        for p in permissions_raw.split(",")
                        if p.strip()
                    ]

                    page_id = f"PAGE:{path}"
                    is_protected = "protectedRoutes" in str(route_file)

                    self.run_query("""
                        MERGE (pg:ArchNode:Page {id: $id})
                        SET pg.path = $path,
                            pg.key = $key,
                            pg.label_key = $label_key,
                            pg.icon = $icon,
                            pg.show_in_menu = $show_in_menu,
                            pg.category = $category,
                            pg.is_protected = $is_protected,
                            pg.type = 'Page'
                    """, {
                        "id": page_id, "path": path, "key": key,
                        "label_key": label_key, "icon": icon,
                        "show_in_menu": show_in_menu, "category": category,
                        "is_protected": is_protected,
                    })
                    page_count += 1

                    # Create Permission nodes and link
                    for perm in permissions:
                        self.run_query("""
                            MERGE (perm:ArchNode:Permission {id: $perm})
                            SET perm.name = $perm, perm.type = 'Permission'
                            WITH perm
                            MATCH (pg:Page {id: $page_id})
                            MERGE (pg)-[:REQUIRES_PERMISSION]->(perm)
                        """, {"perm": perm, "page_id": page_id})

                    # Link Page to its component file (convention: pages/<Key>Page.tsx)
                    page_file_candidates = [
                        f"frontend/src/pages/{key[0].upper()}{key[1:]}Page.tsx",
                        f"frontend/src/pages/{key}Page.tsx",
                    ]
                    for pf in page_file_candidates:
                        self.run_query("""
                            MATCH (pg:Page {id: $page_id}), (f:File {id: $fpath})
                            MERGE (pg)-[:IMPLEMENTED_BY]->(f)
                        """, {"page_id": page_id, "fpath": pf})

            except Exception as e:
                logger.warning(f"Failed to parse route file {route_file}: {e}")

        logger.info(f"✅ Indexed {page_count} page routes.")

    def index_navigation_flows(self):
        """
        Parse frontend source files to extract navigation relationships between pages.

        Scans for:
          - navigate('/path') calls and their surrounding conditions
          - <Navigate to="/path" /> JSX redirects
          - onClick={() => navigate(...)} patterns with conditional context

        Creates:
          Page -[:NAVIGATES_TO {trigger, condition}]-> Page
          UIElement -[:TRIGGERS_NAVIGATION]-> Page
        """
        logger.info("🔀 Indexing navigation flows from frontend source...")

        fe_dir = BASE_DIR / "frontend" / "src"
        if not fe_dir.exists():
            return

        nav_count = 0
        ts_files = list(fe_dir.rglob("*.tsx")) + list(fe_dir.rglob("*.ts"))

        for ts_file in ts_files:
            if any(x in str(ts_file) for x in ["node_modules", ".git", "dist"]):
                continue

            try:
                with open(ts_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                if "navigate(" not in content and "<Navigate" not in content:
                    continue

                rel_path = str(ts_file.relative_to(BASE_DIR)).replace("\\", "/")

                # Determine which page this file belongs to
                source_page = self._resolve_file_to_page(rel_path)

                lines = content.split("\n")
                for i, line in enumerate(lines):
                    # Pattern 1: navigate('/some/path')
                    nav_matches = re.findall(r"navigate\(\s*['\"]([^'\"]+)['\"]", line)
                    # Pattern 2: <Navigate to="/some/path"
                    jsx_nav_matches = re.findall(r"<Navigate\s+to=['\"]([^'\"]+)['\"]", line)

                    all_targets = nav_matches + jsx_nav_matches

                    for target_path in all_targets:
                        if not target_path.startswith("/"):
                            continue

                        target_page = f"PAGE:{target_path}"

                        # Extract surrounding context for condition detection
                        context_start = max(0, i - 5)
                        context_end = min(len(lines), i + 3)
                        context_block = "\n".join(lines[context_start:context_end])

                        # Detect conditions
                        condition = self._extract_navigation_condition(context_block, line)

                        # Detect trigger element (onClick, button label, etc.)
                        trigger = self._extract_trigger_info(context_block, line)

                        self.run_query("""
                            MERGE (src:ArchNode:Page {id: $src_page})
                            ON CREATE SET src.path = $src_path, src.type = 'Page'
                            MERGE (tgt:ArchNode:Page {id: $tgt_page})
                            ON CREATE SET tgt.path = $tgt_path, tgt.type = 'Page'
                            MERGE (src)-[r:NAVIGATES_TO]->(tgt)
                            SET r.trigger = $trigger,
                                r.condition = $condition,
                                r.source_file = $source_file,
                                r.line_number = $line_num
                        """, {
                            "src_page": source_page,
                            "src_path": source_page.replace("PAGE:", ""),
                            "tgt_page": target_page,
                            "tgt_path": target_path,
                            "trigger": trigger,
                            "condition": condition,
                            "source_file": rel_path,
                            "line_num": i + 1,
                        })
                        nav_count += 1

            except Exception as e:
                logger.warning(f"Navigation scan failed for {ts_file.name}: {e}")

        logger.info(f"✅ Indexed {nav_count} navigation flows.")

    def _resolve_file_to_page(self, rel_path: str) -> str:
        """Map a source file path to its owning Page node ID."""
        # pages/XxxPage.tsx -> PAGE:/xxx
        page_match = re.search(r"pages/(\w+)Page\.tsx$", rel_path)
        if page_match:
            page_name = page_match.group(1)
            # Look up in known routes
            result = self.run_query("""
                MATCH (pg:Page) WHERE pg.key = $key RETURN pg.id AS id LIMIT 1
            """, {"key": page_name[0].lower() + page_name[1:]})
            if result:
                return result[0]["id"]

        # guards/ -> auth-related, map to login
        if "guards/" in rel_path:
            return "PAGE:/login"

        # components/common/AppLayout -> global navigation
        if "AppLayout" in rel_path:
            return "PAGE:/"

        # components/chat/ -> chat panel (global)
        if "components/chat/" in rel_path:
            return "PAGE:/"

        # Default: try to infer from directory
        return "PAGE:/"

    def _extract_navigation_condition(self, context_block: str, nav_line: str) -> str:
        """Extract the condition/guard that triggers this navigation."""
        conditions = []

        # Check for if/ternary conditions
        if_patterns = [
            r"if\s*\(([^)]{3,80})\)",
            r"(\w+)\s*\?\s*.*navigate",
            r"(\w+\s*(?:===|!==|==|!=)\s*['\"][^'\"]+['\"])",
            r"(isAuthenticated|hasAccess|hasPermission|isAdmin)",
        ]
        for pattern in if_patterns:
            matches = re.findall(pattern, context_block)
            for m in matches:
                cond = m.strip()
                if len(cond) > 3 and "import" not in cond:
                    conditions.append(cond)

        # Check for status/state checks
        state_patterns = [
            r"(status\s*===?\s*['\"][^'\"]+['\"])",
            r"(state\s*===?\s*['\"][^'\"]+['\"])",
            r"(\.status\s*===?\s*['\"][^'\"]+['\"])",
            r"(record\.\w+\s*===?\s*['\"][^'\"]+['\"])",
        ]
        for pattern in state_patterns:
            matches = re.findall(pattern, context_block)
            conditions.extend(m.strip() for m in matches)

        return "; ".join(conditions[:3]) if conditions else "unconditional"

    def _extract_trigger_info(self, context_block: str, nav_line: str) -> str:
        """Extract what UI element triggers this navigation."""
        triggers = []

        # Button/link labels
        label_patterns = [
            r"(?:label|title|text)\s*[:=]\s*['\"]([^'\"]+)['\"]",
            r">\s*([^<]{2,30})\s*<",
            r"onClick.*?['\"]([^'\"]{2,30})['\"]",
        ]
        for pattern in label_patterns:
            matches = re.findall(pattern, context_block)
            for m in matches:
                clean = m.strip()
                if clean and not clean.startswith("{") and not clean.startswith("("):
                    triggers.append(clean)

        # Component type
        comp_patterns = [
            r"<(Button|Link|Card|MenuItem|Tab)",
            r"onClick",
            r"<Navigate",
        ]
        for pattern in comp_patterns:
            if re.search(pattern, context_block):
                match = re.search(pattern, context_block)
                if match:
                    triggers.append(f"[{match.group(0).strip('<')}]")

        return "; ".join(triggers[:3]) if triggers else "unknown"

    def index_ai_navigation_actions(self):
        """
        Parse chatStore.ts PAGE_CONTEXT_MAP to index AI-driven navigation actions.

        Creates:
          Page -[:HAS_AI_ACTION {label, type}]-> Page
        """
        logger.info("🤖 Indexing AI-driven navigation actions from chatStore...")

        chat_store = BASE_DIR / "frontend" / "src" / "stores" / "chatStore.ts"
        if not chat_store.exists():
            return

        try:
            with open(chat_store, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract PAGE_CONTEXT_MAP entries
            map_match = re.search(
                r"PAGE_CONTEXT_MAP.*?=\s*\{(.*?)\}\s*;",
                content, re.DOTALL,
            )
            if not map_match:
                return

            map_content = map_match.group(1)

            # Parse each page entry
            page_pattern = re.compile(
                r"['\"]([^'\"]+)['\"]\s*:\s*\{(.*?)\}(?=\s*,\s*['\"/]|\s*\};)",
                re.DOTALL,
            )

            action_count = 0
            for page_match in page_pattern.finditer(map_content):
                source_path = page_match.group(1)
                page_body = page_match.group(2)

                # Extract actions
                action_pattern = re.compile(
                    r"\{\s*type:\s*['\"](\w+)['\"].*?"
                    r"label:\s*['\"]([^'\"]+)['\"].*?"
                    r"target:\s*['\"]([^'\"]+)['\"]",
                    re.DOTALL,
                )

                for act_match in action_pattern.finditer(page_body):
                    action_type = act_match.group(1)
                    label = act_match.group(2)
                    target = act_match.group(3)

                    source_page = f"PAGE:{source_path}"

                    if action_type == "navigate":
                        target_page = f"PAGE:{target}"
                        self.run_query("""
                            MERGE (src:ArchNode:Page {id: $src})
                            ON CREATE SET src.path = $src_path, src.type = 'Page'
                            MERGE (tgt:ArchNode:Page {id: $tgt})
                            ON CREATE SET tgt.path = $tgt_path, tgt.type = 'Page'
                            MERGE (src)-[r:HAS_AI_ACTION]->(tgt)
                            SET r.label = $label,
                                r.action_type = $action_type
                        """, {
                            "src": source_page, "src_path": source_path,
                            "tgt": target_page, "tgt_path": target,
                            "label": label, "action_type": action_type,
                        })
                        action_count += 1
                    elif action_type in ("open_modal", "execute", "show_data"):
                        # Non-navigation actions: create UserAction nodes
                        action_id = f"ACTION:{source_path}::{target}"
                        self.run_query("""
                            MERGE (src:ArchNode:Page {id: $src})
                            ON CREATE SET src.path = $src_path, src.type = 'Page'
                            MERGE (act:ArchNode:UserAction {id: $act_id})
                            SET act.label = $label,
                                act.action_type = $action_type,
                                act.target = $target,
                                act.type = 'UserAction'
                            MERGE (src)-[:HAS_ACTION]->(act)
                        """, {
                            "src": source_page, "src_path": source_path,
                            "act_id": action_id, "label": label,
                            "action_type": action_type, "target": target,
                        })
                        action_count += 1

            logger.info(f"✅ Indexed {action_count} AI navigation actions.")

        except Exception as e:
            logger.warning(f"Failed to parse chatStore: {e}")

    def index_access_control_flows(self):
        """
        Parse access.ts ROLE_PERMISSION_MAP to create Role -> Permission -> Page relationships.

        Creates:
          (:Role) nodes
          Role -[:GRANTS]-> Permission
          (Leverages existing Page -[:REQUIRES_PERMISSION]-> Permission)
        """
        logger.info("🔐 Indexing access control flows...")

        access_file = BASE_DIR / "frontend" / "src" / "config" / "access.ts"
        if not access_file.exists():
            return

        try:
            with open(access_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse ROLE_PERMISSION_MAP
            map_match = re.search(
                r"ROLE_PERMISSION_MAP\s*=\s*\{(.*?)\}\s*as\s+const",
                content, re.DOTALL,
            )
            if not map_match:
                return

            map_content = map_match.group(1)

            role_count = 0
            role_pattern = re.compile(
                r"(\w+)\s*:\s*\[(.*?)\]",
                re.DOTALL,
            )

            for role_match in role_pattern.finditer(map_content):
                role_name = role_match.group(1)
                perms_raw = role_match.group(2)
                permissions = [
                    p.strip().strip("'\"")
                    for p in perms_raw.split(",")
                    if p.strip().strip("'\"")
                ]

                self.run_query("""
                    MERGE (role:ArchNode:Role {id: $role})
                    SET role.name = $role, role.type = 'Role'
                """, {"role": role_name})

                for perm in permissions:
                    self.run_query("""
                        MATCH (role:Role {id: $role})
                        MERGE (p:ArchNode:Permission {id: $perm})
                        SET p.name = $perm, p.type = 'Permission'
                        MERGE (role)-[:GRANTS]->(p)
                    """, {"role": role_name, "perm": perm})

                role_count += 1

            logger.info(f"✅ Indexed {role_count} roles with permission mappings.")

        except Exception as e:
            logger.warning(f"Failed to parse access config: {e}")

    def build_business_flows(self):
        """
        Aggregate navigation chains into named BusinessFlow nodes.
        Uses graph traversal to detect common multi-step flows.
        """
        logger.info("📊 Building business flow aggregations...")

        # Define known business flows based on page categories and navigation chains
        known_flows = [
            {
                "id": "FLOW:auth",
                "name": "认证流程",
                "description": "用户登录 → 权限校验 → 页面访问 / 拒绝",
                "steps": ["/login", "/", "/forbidden"],
            },
            {
                "id": "FLOW:knowledge-lifecycle",
                "name": "知识库生命周期",
                "description": "概览 → 知识库管理 → 创建/上传 → 质量评估",
                "steps": ["/", "/knowledge", "/evaluation", "/kb-analytics"],
            },
            {
                "id": "FLOW:governance",
                "name": "治理审查流程",
                "description": "开发治理 → 架构资产 → Agent 治理 → 安全审计",
                "steps": ["/governance/dev", "/governance/assets", "/governance/agent", "/security", "/audit"],
            },
            {
                "id": "FLOW:studio-pipeline",
                "name": "Studio 创作流程",
                "description": "Studio → Pipeline 构建 → Canvas Lab → 批量执行",
                "steps": ["/studio", "/pipelines", "/canvas-lab", "/batch"],
            },
            {
                "id": "FLOW:observability",
                "name": "可观测性流程",
                "description": "Token 仪表盘 → 链路追踪 → 审计日志",
                "steps": ["/token-dashboard", "/trace", "/audit"],
            },
        ]

        flow_count = 0
        for flow in known_flows:
            self.run_query("""
                MERGE (bf:ArchNode:BusinessFlow {id: $id})
                SET bf.name = $name,
                    bf.description = $description,
                    bf.type = 'BusinessFlow'
            """, {
                "id": flow["id"],
                "name": flow["name"],
                "description": flow["description"],
            })

            for seq, step_path in enumerate(flow["steps"]):
                page_id = f"PAGE:{step_path}"
                self.run_query("""
                    MATCH (bf:BusinessFlow {id: $flow_id})
                    MATCH (pg:Page {id: $page_id})
                    MERGE (bf)-[r:CONTAINS_STEP]->(pg)
                    SET r.seq = $seq
                """, {
                    "flow_id": flow["id"],
                    "page_id": page_id,
                    "seq": seq,
                })

            flow_count += 1

        # Also discover flows from actual NAVIGATES_TO chains in the graph
        chains = self.run_query("""
            MATCH path = (a:Page)-[:NAVIGATES_TO*2..4]->(b:Page)
            WHERE a <> b
            WITH [n IN nodes(path) | n.path] AS steps, length(path) AS depth
            RETURN DISTINCT steps, depth
            ORDER BY depth DESC
            LIMIT 10
        """)

        for chain in (chains or []):
            steps = chain.get("steps", [])
            if len(steps) >= 3:
                chain_id = f"FLOW:discovered:{'->'.join(s for s in steps if s)}"
                self.run_query("""
                    MERGE (bf:ArchNode:BusinessFlow {id: $id})
                    SET bf.name = $name,
                        bf.description = 'Auto-discovered navigation chain',
                        bf.type = 'BusinessFlow',
                        bf.is_discovered = true
                """, {
                    "id": chain_id,
                    "name": " → ".join(s for s in steps if s),
                })

                for seq, step_path in enumerate(steps):
                    if step_path:
                        self.run_query("""
                            MATCH (bf:BusinessFlow {id: $flow_id}), (pg:Page {id: $page_id})
                            MERGE (bf)-[r:CONTAINS_STEP]->(pg)
                            SET r.seq = $seq
                        """, {"flow_id": chain_id, "page_id": f"PAGE:{step_path}", "seq": seq})

        logger.info(f"✅ Built {flow_count} predefined + discovered business flows.")

    # ─── P0: Data Model Layer (SQLModel → Neo4j) ────────────────────────────

    def index_database_models(self):
        """
        Parse backend/app/models/*.py to extract SQLModel table definitions.

        Creates:
          (:DBTable) — one per SQLModel class with table=True
          (:DBColumn) — one per Field
          DBTable -[:HAS_COLUMN]-> DBColumn
          DBTable -[:FOREIGN_KEY {column}]-> DBTable
          File -[:DEFINES_MODEL]-> DBTable
        """
        logger.info("🗄️  Indexing database models from SQLModel definitions...")

        models_dir = BASE_DIR / "backend" / "app" / "models"
        if not models_dir.exists():
            return

        table_count = 0
        fk_count = 0

        for py_file in models_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                tree = ast.parse(content)
                rel_path = str(py_file.relative_to(BASE_DIR)).replace("\\", "/")

                for node in ast.walk(tree):
                    if not isinstance(node, ast.ClassDef):
                        continue

                    # Check if it's a SQLModel table class
                    is_table = False
                    for kw in node.keywords:
                        if kw.arg == "table" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            is_table = True
                            break

                    if not is_table:
                        continue

                    class_name = node.name
                    table_name = class_name  # default

                    # Extract __tablename__
                    for item in node.body:
                        if isinstance(item, ast.Assign):
                            for target in item.targets:
                                if isinstance(target, ast.Name) and target.id == "__tablename__":
                                    if isinstance(item.value, ast.Constant):
                                        table_name = item.value.value

                    table_id = f"TABLE:{table_name}"

                    # Create DBTable node
                    self.run_query("""
                        MERGE (t:ArchNode:DBTable {id: $id})
                        SET t.table_name = $table_name,
                            t.class_name = $class_name,
                            t.source_file = $source_file,
                            t.type = 'DBTable'
                        WITH t
                        MATCH (f:File {id: $fpath})
                        MERGE (f)-[:DEFINES_MODEL]->(t)
                    """, {
                        "id": table_id, "table_name": table_name,
                        "class_name": class_name, "source_file": rel_path,
                        "fpath": rel_path,
                    })
                    table_count += 1

                    # Extract columns (Field assignments)
                    for item in node.body:
                        col_name = None
                        col_type = ""
                        is_pk = False
                        is_index = False
                        fk_target = None

                        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                            col_name = item.target.id
                            if col_name.startswith("_"):
                                continue

                            # Extract type annotation
                            if isinstance(item.annotation, ast.Name):
                                col_type = item.annotation.id
                            elif isinstance(item.annotation, ast.Subscript):
                                if isinstance(item.annotation.value, ast.Name):
                                    col_type = item.annotation.value.id
                            elif isinstance(item.annotation, ast.BinOp):
                                # X | None pattern
                                if isinstance(item.annotation.left, ast.Name):
                                    col_type = item.annotation.left.id

                            # Parse Field() call for metadata
                            if item.value and isinstance(item.value, ast.Call):
                                for kw in item.value.keywords:
                                    if kw.arg == "primary_key" and isinstance(kw.value, ast.Constant):
                                        is_pk = kw.value.value
                                    elif kw.arg == "index" and isinstance(kw.value, ast.Constant):
                                        is_index = kw.value.value
                                    elif kw.arg == "foreign_key" and isinstance(kw.value, ast.Constant):
                                        fk_target = kw.value.value  # e.g. "users.id"

                        if not col_name or col_name in ("__tablename__",):
                            continue

                        col_id = f"{table_id}::{col_name}"
                        self.run_query("""
                            MERGE (c:ArchNode:DBColumn {id: $id})
                            SET c.name = $name,
                                c.col_type = $col_type,
                                c.is_primary_key = $is_pk,
                                c.is_index = $is_index,
                                c.type = 'DBColumn'
                            WITH c
                            MATCH (t:DBTable {id: $table_id})
                            MERGE (t)-[:HAS_COLUMN]->(c)
                        """, {
                            "id": col_id, "name": col_name, "col_type": col_type,
                            "is_pk": is_pk, "is_index": is_index, "table_id": table_id,
                        })

                        # Create foreign key relationship
                        if fk_target and "." in fk_target:
                            fk_table = fk_target.split(".")[0]
                            fk_col = fk_target.split(".")[1]
                            self.run_query("""
                                MATCH (src:DBTable {id: $src_table})
                                MATCH (tgt:DBTable) WHERE tgt.table_name = $fk_table
                                MERGE (src)-[r:FOREIGN_KEY]->(tgt)
                                SET r.source_column = $src_col,
                                    r.target_column = $fk_col
                            """, {
                                "src_table": table_id, "fk_table": fk_table,
                                "src_col": col_name, "fk_col": fk_col,
                            })
                            fk_count += 1

            except Exception as e:
                logger.warning(f"Failed to parse model file {py_file.name}: {e}")

        logger.info(f"✅ Indexed {table_count} DB tables with {fk_count} foreign key relationships.")

    # ─── P0: API Endpoint Layer ──────────────────────────────────────────────

    def index_api_endpoints(self):
        """
        Parse backend API route files to extract endpoint definitions.

        Creates:
          (:APIEndpoint) — one per route handler, with method, path, tags
          APIEndpoint -[:HANDLED_BY]-> File
          APIEndpoint -[:CALLS_SERVICE]-> CodeEntity (best-effort)
          APIEndpoint -[:OPERATES_ON]-> DBTable (best-effort via model imports)
        """
        logger.info("🌐 Indexing API endpoints from FastAPI route definitions...")

        # 1. Parse router registration from api/__init__.py
        api_init = BASE_DIR / "backend" / "app" / "api" / "__init__.py"
        router_map: dict[str, dict] = {}  # module_name -> {prefix, tags}

        if api_init.exists():
            try:
                with open(api_init, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract: router.include_router(xxx.router, prefix="/yyy", tags=["ZZZ"])
                pattern = re.compile(
                    r'include_router\(\s*(\w+)\.router\s*,'
                    r'(?:\s*prefix\s*=\s*["\']([^"\']+)["\'])?,?'
                    r'(?:\s*tags\s*=\s*\[([^\]]*)\])?\s*\)',
                )
                for m in pattern.finditer(content):
                    module = m.group(1)
                    prefix = m.group(2) or ""
                    tags_raw = m.group(3) or ""
                    tags = [t.strip().strip("'\"") for t in tags_raw.split(",") if t.strip()]
                    router_map[module] = {"prefix": prefix, "tags": tags}

            except Exception as e:
                logger.warning(f"Failed to parse api/__init__.py: {e}")

        # 2. Parse each route file
        routes_dir = BASE_DIR / "backend" / "app" / "api" / "routes"
        if not routes_dir.exists():
            return

        endpoint_count = 0

        for route_file in routes_dir.glob("*.py"):
            if route_file.name.startswith("_"):
                continue

            module_name = route_file.stem
            router_info = router_map.get(module_name, {"prefix": f"/{module_name}", "tags": []})
            prefix = router_info["prefix"]
            tags = router_info["tags"]

            try:
                with open(route_file, "r", encoding="utf-8") as f:
                    content = f.read()

                rel_path = str(route_file.relative_to(BASE_DIR)).replace("\\", "/")
                tree = ast.parse(content)

                # Collect model imports to infer OPERATES_ON relationships
                imported_models = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom) and node.module:
                        if "models" in node.module:
                            for alias in node.names:
                                imported_models.add(alias.name)

                # Find decorated route handlers
                for node in ast.walk(tree):
                    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue

                    for decorator in node.decorator_list:
                        method = None
                        path = ""

                        # @router.get("/path") or @router.post("/path")
                        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                            attr = decorator.func.attr
                            if attr in ("get", "post", "put", "delete", "patch", "websocket"):
                                method = attr.upper()
                                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                                    path = decorator.args[0].value

                        if not method:
                            continue

                        full_path = f"/api/v1{prefix}{path}".rstrip("/") or f"/api/v1{prefix}"
                        func_name = node.name
                        endpoint_id = f"EP:{method}:{full_path}"

                        # Extract response_model if present
                        response_model = ""
                        for kw in (decorator.keywords if isinstance(decorator, ast.Call) else []):
                            if kw.arg == "response_model" and isinstance(kw.value, ast.Subscript):
                                if isinstance(kw.value.slice, ast.Name):
                                    response_model = kw.value.slice.id

                        self.run_query("""
                            MERGE (ep:ArchNode:APIEndpoint {id: $id})
                            SET ep.method = $method,
                                ep.path = $full_path,
                                ep.handler = $handler,
                                ep.module = $module,
                                ep.tags = $tags,
                                ep.response_model = $response_model,
                                ep.type = 'APIEndpoint'
                            WITH ep
                            MATCH (f:File {id: $fpath})
                            MERGE (ep)-[:HANDLED_BY]->(f)
                        """, {
                            "id": endpoint_id, "method": method, "full_path": full_path,
                            "handler": func_name, "module": module_name,
                            "tags": tags, "response_model": response_model,
                            "fpath": rel_path,
                        })
                        endpoint_count += 1

                        # Link to DB tables via imported models
                        # Heuristic: if the handler function body references a model class
                        # that we know maps to a table, create OPERATES_ON
                        func_source = ast.get_source_segment(content, node) or ""
                        for model_name in imported_models:
                            if model_name in func_source:
                                self.run_query("""
                                    MATCH (ep:APIEndpoint {id: $ep_id})
                                    MATCH (t:DBTable {class_name: $model})
                                    MERGE (ep)-[:OPERATES_ON]->(t)
                                """, {"ep_id": endpoint_id, "model": model_name})

            except Exception as e:
                logger.warning(f"Failed to parse route file {route_file.name}: {e}")

        # 3. Link frontend CALLS_API to backend APIEndpoint definitions
        self.run_query("""
            MATCH (fe:File)-[old:CALLS_API]->(stub:APIEndpoint)
            WHERE stub.type IS NULL OR stub.method IS NULL
            WITH fe, old, stub
            MATCH (real:APIEndpoint)
            WHERE real.path = stub.id AND real.method IS NOT NULL
            MERGE (fe)-[:CALLS_API]->(real)
            DELETE old
        """)

        logger.info(f"✅ Indexed {endpoint_count} API endpoints.")

    # ─── P1: Agent/Swarm Topology ────────────────────────────────────────────

    def index_agent_swarm_topology(self):
        """
        Parse the Swarm system to extract Agent definitions, LangGraph nodes,
        tools, skills, and LLM model tiers.

        Creates:
          (:SwarmNode) — LangGraph graph nodes (supervisor, retrieval, reflection, etc.)
          (:AgentDef) — registered agent definitions
          (:NativeTool) — tools available to agents
          (:SkillDef) — skill packages
          (:LLMModel) — model tier definitions
          SwarmNode -[:ROUTES_TO]-> SwarmNode/AgentDef
          AgentDef -[:HAS_TOOL]-> NativeTool
          AgentDef -[:HAS_SKILL]-> SkillDef
          LLMModel -[:SERVES_TIER]-> ModelTier label
        """
        logger.info("🐝 Indexing Agent/Swarm topology...")

        # --- 1. LangGraph Nodes (from swarm.py build_graph) ---
        swarm_file = BASE_DIR / "backend" / "app" / "agents" / "swarm.py"
        graph_nodes = []
        graph_edges = []

        if swarm_file.exists():
            try:
                with open(swarm_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract add_node calls: workflow.add_node("name", ...)
                for m in re.finditer(r'add_node\(\s*["\'](\w+)["\']', content):
                    graph_nodes.append(m.group(1))

                # Extract edges: add_edge("from", "to")
                for m in re.finditer(r'add_edge\(\s*["\'](\w+)["\']\s*,\s*["\'](\w+)["\']', content):
                    graph_edges.append((m.group(1), m.group(2)))

                # Extract conditional edges targets
                for m in re.finditer(r'["\'](\w+)["\']\s*:\s*["\'](\w+)["\']', content):
                    src_candidate = m.group(1)
                    tgt_candidate = m.group(2)
                    if src_candidate in graph_nodes or tgt_candidate in graph_nodes:
                        graph_edges.append((src_candidate, tgt_candidate))

                # Extract entry point
                entry_match = re.search(r'set_entry_point\(\s*["\'](\w+)["\']', content)
                entry_point = entry_match.group(1) if entry_match else "supervisor"

            except Exception as e:
                logger.warning(f"Failed to parse swarm.py: {e}")

        # Write SwarmNode nodes
        for node_name in set(graph_nodes):
            node_id = f"SWARM_NODE:{node_name}"
            is_entry = node_name == entry_point if 'entry_point' in dir() else False
            self.run_query("""
                MERGE (sn:ArchNode:SwarmNode {id: $id})
                SET sn.name = $name, sn.is_entry_point = $is_entry, sn.type = 'SwarmNode'
            """, {"id": node_id, "name": node_name, "is_entry": is_entry})

        # Write ROUTES_TO edges
        seen_edges = set()
        for src, tgt in graph_edges:
            if tgt in ("FINISH", "END") or src == tgt:
                continue
            key = (src, tgt)
            if key in seen_edges:
                continue
            seen_edges.add(key)
            self.run_query("""
                MATCH (a:SwarmNode {name: $src})
                MATCH (b) WHERE (b:SwarmNode OR b:AgentDef) AND b.name = $tgt
                MERGE (a)-[:ROUTES_TO]->(b)
            """, {"src": src, "tgt": tgt})

        logger.info(f"  Graph nodes: {len(set(graph_nodes))}, edges: {len(seen_edges)}")

        # --- 2. Native Tools (from tools.py) ---
        tools_file = BASE_DIR / "backend" / "app" / "agents" / "tools.py"
        tool_count = 0
        if tools_file.exists():
            try:
                with open(tools_file, "r", encoding="utf-8") as f:
                    content = f.read()
                tree = ast.parse(content)
                rel_path = str(tools_file.relative_to(BASE_DIR)).replace("\\", "/")

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Check if decorated with @hive_tool or @tool
                        is_tool = any(
                            (isinstance(d, ast.Name) and d.id == "tool") or
                            (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id in ("tool", "hive_tool"))
                            for d in node.decorator_list
                        )
                        if not is_tool:
                            continue

                        tool_name = node.name
                        docstring = ast.get_docstring(node) or ""
                        tool_id = f"TOOL:{tool_name}"

                        self.run_query("""
                            MERGE (t:ArchNode:NativeTool {id: $id})
                            SET t.name = $name,
                                t.description = $desc,
                                t.source_file = $fpath,
                                t.type = 'NativeTool'
                        """, {"id": tool_id, "name": tool_name, "desc": docstring[:200], "fpath": rel_path})
                        tool_count += 1
            except Exception as e:
                logger.warning(f"Failed to parse tools.py: {e}")

        # Also parse agentic_search.py
        search_tools_file = BASE_DIR / "backend" / "app" / "agents" / "agentic_search.py"
        if search_tools_file.exists():
            try:
                with open(search_tools_file, "r", encoding="utf-8") as f:
                    content = f.read()
                tree = ast.parse(content)
                rel_path = str(search_tools_file.relative_to(BASE_DIR)).replace("\\", "/")
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        is_tool = any(
                            (isinstance(d, ast.Name) and d.id == "tool") or
                            (isinstance(d, ast.Call) and isinstance(d.func, ast.Name) and d.func.id == "tool")
                            for d in node.decorator_list
                        )
                        if not is_tool:
                            continue
                        tool_id = f"TOOL:{node.name}"
                        docstring = ast.get_docstring(node) or ""
                        self.run_query("""
                            MERGE (t:ArchNode:NativeTool {id: $id})
                            SET t.name = $name, t.description = $desc,
                                t.source_file = $fpath, t.type = 'NativeTool'
                        """, {"id": tool_id, "name": node.name, "desc": docstring[:200], "fpath": rel_path})
                        tool_count += 1
            except Exception as e:
                logger.warning(f"Failed to parse agentic_search.py: {e}")

        logger.info(f"  Native tools: {tool_count}")

        # --- 3. Skills (from backend/app/skills/) ---
        skill_count = 0
        skills_dir = BASE_DIR / "backend" / "app" / "skills"
        if skills_dir.exists():
            for skill_dir in skills_dir.iterdir():
                if not skill_dir.is_dir() or skill_dir.name.startswith("__"):
                    continue
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    continue
                try:
                    with open(skill_md, "r", encoding="utf-8") as f:
                        md_content = f.read()
                    # Parse frontmatter
                    desc = skill_dir.name
                    version = "0.1.0"
                    fm_match = re.search(r'^---\s*\n(.*?)\n---', md_content, re.DOTALL)
                    if fm_match:
                        for line in fm_match.group(1).splitlines():
                            kv = re.match(r'^(\w[\w-]*):\s*"?(.*?)"?\s*$', line)
                            if kv:
                                if kv.group(1) == "description":
                                    desc = kv.group(2)
                                elif kv.group(1) == "version":
                                    version = kv.group(2)

                    skill_id = f"SKILL:{skill_dir.name}"
                    has_tools = (skill_dir / "tools.py").exists()
                    self.run_query("""
                        MERGE (s:ArchNode:SkillDef {id: $id})
                        SET s.name = $name, s.description = $desc,
                            s.version = $version, s.has_tools = $has_tools,
                            s.type = 'SkillDef'
                    """, {"id": skill_id, "name": skill_dir.name, "desc": desc,
                          "version": version, "has_tools": has_tools})
                    skill_count += 1
                except Exception:
                    pass

        logger.info(f"  Skills: {skill_count}")

        # --- 4. LLM Model Tiers (from config) ---
        tiers = [
            ("simple", "SIMPLE", "Fast, low-cost model for simple tasks"),
            ("medium", "MEDIUM", "Balanced model for general tasks"),
            ("complex", "COMPLEX", "High-capability model for complex tasks"),
            ("reasoning", "REASONING", "Top-tier model for deep reasoning"),
        ]
        for tier_key, tier_name, tier_desc in tiers:
            tier_id = f"LLM_TIER:{tier_name}"
            self.run_query("""
                MERGE (t:ArchNode:LLMTier {id: $id})
                SET t.name = $name, t.description = $desc, t.type = 'LLMTier'
            """, {"id": tier_id, "name": tier_name, "desc": tier_desc})

        # Link supervisor to LLM tiers
        self.run_query("""
            MATCH (sn:SwarmNode {name: 'supervisor'}), (t:LLMTier)
            MERGE (sn)-[:USES_LLM]->(t)
        """)

        logger.info(f"✅ Agent/Swarm topology indexed: {len(set(graph_nodes))} nodes, {tool_count} tools, {skill_count} skills.")

    # ─── P1: Pipeline Definitions ────────────────────────────────────────────

    def index_pipeline_definitions(self):
        """
        Parse the Pipeline/Batch system to extract stage definitions and artifact flow.

        Creates:
          (:PipelineStage) — from batch/pipeline.py ArtifactType enum
          (:ArtifactType) — artifact types that flow between stages
          PipelineStage -[:PRODUCES]-> ArtifactType
          PipelineStage -[:CONSUMES]-> ArtifactType
          Links to existing DBTable for PipelineConfig
        """
        logger.info("🔧 Indexing Pipeline definitions...")

        # 1. Parse ArtifactType enum from pipeline.py
        pipeline_file = BASE_DIR / "backend" / "app" / "batch" / "pipeline.py"
        artifact_types = []
        if pipeline_file.exists():
            try:
                with open(pipeline_file, "r", encoding="utf-8") as f:
                    content = f.read()
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == "ArtifactType":
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name) and isinstance(item.value, ast.Constant):
                                        artifact_types.append({
                                            "name": target.id,
                                            "value": item.value.value,
                                        })

                for at in artifact_types:
                    at_id = f"ARTIFACT_TYPE:{at['value']}"
                    self.run_query("""
                        MERGE (a:ArchNode:ArtifactType {id: $id})
                        SET a.name = $name, a.value = $value, a.type = 'ArtifactType'
                    """, {"id": at_id, "name": at["name"], "value": at["value"]})

            except Exception as e:
                logger.warning(f"Failed to parse pipeline.py: {e}")

        # 2. Parse BatchEngine nodes from engine.py
        engine_file = BASE_DIR / "backend" / "app" / "batch" / "engine.py"
        if engine_file.exists():
            try:
                with open(engine_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract node methods: scheduler_node, worker_node
                for m in re.finditer(r'async def (\w+_node)\(self', content):
                    node_name = m.group(1)
                    stage_id = f"PIPELINE_STAGE:{node_name}"
                    self.run_query("""
                        MERGE (s:ArchNode:PipelineStage {id: $id})
                        SET s.name = $name, s.type = 'PipelineStage'
                    """, {"id": stage_id, "name": node_name})

                # Link scheduler -> worker flow
                self.run_query("""
                    MATCH (s:PipelineStage {name: 'scheduler_node'})
                    MATCH (w:PipelineStage {name: 'worker_node'})
                    MERGE (s)-[:FEEDS_INTO]->(w)
                """)

            except Exception as e:
                logger.warning(f"Failed to parse engine.py: {e}")

        # 3. Link PipelineConfig table to pipeline system
        self.run_query("""
            MATCH (t:DBTable {class_name: 'PipelineConfig'})
            MATCH (s:PipelineStage)
            MERGE (t)-[:CONFIGURES]->(s)
        """)

        logger.info(f"✅ Pipeline definitions indexed: {len(artifact_types)} artifact types.")

    # ─── P2: Observability Trace Templates ───────────────────────────────────

    def index_observability_traces(self):
        """
        Map the observability trace chain: which DB tables store traces,
        which services produce them, and how spans nest.

        Creates:
          (:TraceType) — categories of traces (RAG, Swarm, File, LLM)
          TraceType -[:STORED_IN]-> DBTable
          TraceType -[:HAS_SPAN_TYPE]-> TraceType (parent-child)
          APIEndpoint -[:PRODUCES_TRACE]-> TraceType
          Service(File) -[:EMITS_TRACE]-> TraceType
        """
        logger.info("📡 Indexing observability trace templates...")

        # Define the trace hierarchy based on the observability models
        trace_types = [
            {"id": "TRACE:rag_query", "name": "RAG Query Trace", "table": "obs_rag_query_traces",
             "description": "Records every RAG retrieval request with quality metrics"},
            {"id": "TRACE:file_trace", "name": "File Processing Trace", "table": "obs_file_traces",
             "description": "Traces a single file through the ingestion swarm"},
            {"id": "TRACE:agent_span", "name": "Agent Span", "table": "obs_agent_spans",
             "description": "Individual agent action within a file trace", "parent": "TRACE:file_trace"},
            {"id": "TRACE:swarm_trace", "name": "Swarm Trace", "table": "obs_swarm_traces",
             "description": "High-level multi-agent swarm request trace"},
            {"id": "TRACE:swarm_span", "name": "Swarm Span", "table": "obs_swarm_spans",
             "description": "Individual agent task in a swarm trace", "parent": "TRACE:swarm_trace"},
            {"id": "TRACE:llm_metric", "name": "LLM Metric", "table": "obs_llm_metrics",
             "description": "Per-model health, latency, and cost tracking"},
            {"id": "TRACE:baseline_metric", "name": "Baseline Metric", "table": "obs_baseline_metrics",
             "description": "Frontend performance baseline measurements"},
            {"id": "TRACE:hitl_task", "name": "HITL Task", "table": "obs_hitl_tasks",
             "description": "Human-in-the-loop review queue item", "parent": "TRACE:file_trace"},
            {"id": "TRACE:ingestion_batch", "name": "Ingestion Batch", "table": "obs_ingestion_batches",
             "description": "Batch job tracking for mass file processing"},
            {"id": "TRACE:intent_cache", "name": "Intent Cache", "table": "obs_intent_cache",
             "description": "Predictive prefetch cache entries"},
            {"id": "TRACE:audit_log", "name": "Audit Log", "table": "audit_logs",
             "description": "Immutable security and operation audit trail"},
        ]

        for tt in trace_types:
            self.run_query("""
                MERGE (t:ArchNode:TraceType {id: $id})
                SET t.name = $name, t.description = $desc, t.type = 'TraceType'
                WITH t
                OPTIONAL MATCH (db:DBTable {table_name: $table})
                FOREACH (_ IN CASE WHEN db IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (t)-[:STORED_IN]->(db)
                )
            """, {"id": tt["id"], "name": tt["name"], "desc": tt["description"], "table": tt["table"]})

            # Parent-child span nesting
            if "parent" in tt:
                self.run_query("""
                    MATCH (parent:TraceType {id: $parent_id})
                    MATCH (child:TraceType {id: $child_id})
                    MERGE (parent)-[:HAS_SPAN_TYPE]->(child)
                """, {"parent_id": tt["parent"], "child_id": tt["id"]})

        # Link services that produce traces
        trace_producers = [
            ("backend/app/services/observability_service.py", "TRACE:rag_query"),
            ("backend/app/services/observability_service.py", "TRACE:llm_metric"),
            ("backend/app/services/observability_service.py", "TRACE:baseline_metric"),
            ("backend/app/services/rag_gateway.py", "TRACE:rag_query"),
            ("backend/app/agents/engine.py", "TRACE:swarm_trace"),
            ("backend/app/batch/engine.py", "TRACE:file_trace"),
            ("backend/app/audit/logger.py", "TRACE:audit_log"),
        ]
        for file_path, trace_id in trace_producers:
            self.run_query("""
                MATCH (f:File {id: $fpath}), (t:TraceType {id: $tid})
                MERGE (f)-[:EMITS_TRACE]->(t)
            """, {"fpath": file_path, "tid": trace_id})

        # Link API endpoints that produce traces
        trace_api_patterns = [
            ("/api/v1/chat/completions", "TRACE:swarm_trace"),
            ("/api/v1/observability", "TRACE:baseline_metric"),
            ("/api/v1/evaluation", "TRACE:rag_query"),
        ]
        for api_prefix, trace_id in trace_api_patterns:
            self.run_query("""
                MATCH (ep:APIEndpoint) WHERE ep.path STARTS WITH $prefix
                MATCH (t:TraceType {id: $tid})
                MERGE (ep)-[:PRODUCES_TRACE]->(t)
            """, {"prefix": api_prefix, "tid": trace_id})

        logger.info(f"✅ Indexed {len(trace_types)} trace types with hierarchy.")

    # ─── P2: Event/Message Bus Topology ──────────────────────────────────────

    def index_event_bus_topology(self):
        """
        Map the event/message bus channels and their producers/consumers.

        Creates:
          (:EventChannel) — communication channels (WriteEventBus, AgentBus, WebSocket, Blackboard)
          (:EventType) — specific event types flowing through channels
          File -[:PUBLISHES_TO]-> EventChannel
          File -[:SUBSCRIBES_TO]-> EventChannel
          EventChannel -[:CARRIES]-> EventType
        """
        logger.info("📨 Indexing event bus topology...")

        # Define known channels
        channels = [
            {"id": "CHANNEL:write_event_bus", "name": "WriteEventBus",
             "transport": "Redis Pub/Sub", "channel_key": "hivemind:kb_write_events",
             "description": "Knowledge base write-side events for cache invalidation"},
            {"id": "CHANNEL:agent_bus", "name": "AgentMessageBus",
             "transport": "In-process Pub/Sub", "channel_key": "agent_bus",
             "description": "Real-time peer-to-peer communication between agents"},
            {"id": "CHANNEL:websocket", "name": "WebSocket Manager",
             "transport": "WebSocket", "channel_key": "ws",
             "description": "Push notifications to connected frontend clients"},
            {"id": "CHANNEL:blackboard", "name": "Redis Blackboard",
             "transport": "Redis Pub/Sub + Hash", "channel_key": "swarm_blackboard",
             "description": "Cluster-wide shared memory for agent reflections"},
        ]

        for ch in channels:
            self.run_query("""
                MERGE (c:ArchNode:EventChannel {id: $id})
                SET c.name = $name, c.transport = $transport,
                    c.channel_key = $channel_key, c.description = $desc,
                    c.type = 'EventChannel'
            """, {"id": ch["id"], "name": ch["name"], "transport": ch["transport"],
                  "channel_key": ch["channel_key"], "desc": ch["description"]})

        # Define event types
        event_types = [
            {"id": "EVT:document_uploaded", "name": "document_uploaded", "channel": "CHANNEL:write_event_bus"},
            {"id": "EVT:document_linked", "name": "document_linked", "channel": "CHANNEL:write_event_bus"},
            {"id": "EVT:document_unlinked", "name": "document_unlinked", "channel": "CHANNEL:write_event_bus"},
            {"id": "EVT:agent_event", "name": "agent_stream_event", "channel": "CHANNEL:websocket"},
            {"id": "EVT:notification", "name": "notification", "channel": "CHANNEL:websocket"},
            {"id": "EVT:agent_reflection", "name": "agent_reflection", "channel": "CHANNEL:blackboard"},
            {"id": "EVT:agent_coordination", "name": "agent_coordination", "channel": "CHANNEL:agent_bus"},
        ]

        for evt in event_types:
            self.run_query("""
                MERGE (e:ArchNode:EventType {id: $id})
                SET e.name = $name, e.type = 'EventType'
                WITH e
                MATCH (ch:EventChannel {id: $channel})
                MERGE (ch)-[:CARRIES]->(e)
            """, {"id": evt["id"], "name": evt["name"], "channel": evt["channel"]})

        # Map producers and consumers
        producers = [
            ("backend/app/api/routes/knowledge.py", "CHANNEL:write_event_bus"),
            ("backend/app/services/write_event_bus.py", "CHANNEL:write_event_bus"),
            ("backend/app/agents/engine.py", "CHANNEL:websocket"),
            ("backend/app/agents/engine.py", "CHANNEL:agent_bus"),
            ("backend/app/agents/bus.py", "CHANNEL:agent_bus"),
            ("backend/app/core/telemetry/blackboard.py", "CHANNEL:blackboard"),
            ("backend/app/services/ws_manager.py", "CHANNEL:websocket"),
        ]
        for fpath, ch_id in producers:
            self.run_query("""
                MATCH (f:File {id: $fpath}), (ch:EventChannel {id: $ch_id})
                MERGE (f)-[:PUBLISHES_TO]->(ch)
            """, {"fpath": fpath, "ch_id": ch_id})

        consumers = [
            ("backend/app/agents/nodes/agent.py", "CHANNEL:agent_bus"),
            ("backend/app/agents/swarm.py", "CHANNEL:agent_bus"),
            ("frontend/src/stores/wsStore.ts", "CHANNEL:websocket"),
            ("frontend/src/stores/chatStore.ts", "CHANNEL:websocket"),
        ]
        for fpath, ch_id in consumers:
            self.run_query("""
                MATCH (f:File {id: $fpath}), (ch:EventChannel {id: $ch_id})
                MERGE (f)-[:SUBSCRIBES_TO]->(ch)
            """, {"fpath": fpath, "ch_id": ch_id})

        logger.info(f"✅ Indexed {len(channels)} event channels with {len(event_types)} event types.")

    # ─── State Machines (Test-Critical) ──────────────────────────────────────

    def index_state_machines(self):
        """
        Index entity state machines with all valid transitions.
        Derived from StrEnum definitions + actual .status = assignments in code.

        Creates:
          (:StateMachine) — one per entity with status field
          (:EntityState) — one per valid state value
          StateMachine -[:HAS_STATE]-> EntityState
          EntityState -[:TRANSITIONS_TO {trigger, source_file, guard}]-> EntityState
          StateMachine -[:INITIAL_STATE]-> EntityState
          DBTable -[:HAS_STATE_MACHINE]-> StateMachine
        """
        logger.info("🔄 Indexing entity state machines...")

        # All state machines extracted from code analysis
        machines = [
            {
                "id": "SM:kb_document_link",
                "name": "KB Document Link Status",
                "entity": "KnowledgeBaseDocumentLink",
                "table": "knowledge_base_documents",
                "field": "status",
                "initial": "pending",
                "states": ["pending", "processing", "indexed", "pending_review", "failed"],
                "transitions": [
                    {"from": "pending", "to": "processing", "trigger": "index_document_task dispatched", "source": "backend/app/services/indexing.py"},
                    {"from": "pending", "to": "failed", "trigger": "document or KB not found", "source": "backend/app/services/indexing.py"},
                    {"from": "processing", "to": "indexed", "trigger": "swarm indexing success (confidence >= 0.8)", "source": "backend/app/services/ingestion/tasks.py"},
                    {"from": "processing", "to": "pending_review", "trigger": "low confidence (< 0.8) or flagged", "source": "backend/app/services/ingestion/tasks.py"},
                    {"from": "processing", "to": "failed", "trigger": "critical error during swarm dispatch", "source": "backend/app/services/indexing.py"},
                    {"from": "pending_review", "to": "indexed", "trigger": "HITL review approved", "source": "backend/app/api/routes/audit_v3.py"},
                    {"from": "pending_review", "to": "failed", "trigger": "HITL review rejected", "source": "backend/app/api/routes/audit_v3.py"},
                ],
            },
            {
                "id": "SM:document",
                "name": "Document Parsing Status",
                "entity": "Document",
                "table": "documents",
                "field": "status",
                "initial": "pending",
                "states": ["pending", "processing", "parsed", "failed", "stale"],
                "transitions": [
                    {"from": "pending", "to": "processing", "trigger": "ingestion pipeline started", "source": "backend/app/services/indexing.py"},
                    {"from": "processing", "to": "parsed", "trigger": "parsing completed successfully", "source": "backend/app/services/ingestion/tasks.py"},
                    {"from": "processing", "to": "failed", "trigger": "parsing error", "source": "backend/app/services/ingestion/tasks.py"},
                    {"from": "parsed", "to": "stale", "trigger": "lifecycle check: expiry_date passed", "source": "backend/app/services/knowledge/lifecycle.py"},
                    {"from": "stale", "to": "pending", "trigger": "re-index triggered", "source": "backend/app/services/knowledge/lifecycle.py"},
                ],
            },
            {
                "id": "SM:file_trace",
                "name": "File Trace Status",
                "entity": "FileTrace",
                "table": "obs_file_traces",
                "field": "status",
                "initial": "pending",
                "states": ["pending", "running", "success", "failed", "pending_review", "approved", "rejected"],
                "transitions": [
                    {"from": "pending", "to": "running", "trigger": "celery worker picks up task", "source": "backend/app/services/ingestion/tasks.py"},
                    {"from": "running", "to": "success", "trigger": "confidence >= 0.8", "source": "backend/app/services/ingestion/tasks.py"},
                    {"from": "running", "to": "pending_review", "trigger": "confidence < 0.8 or flagged", "source": "backend/app/services/ingestion/tasks.py"},
                    {"from": "running", "to": "failed", "trigger": "exception during processing", "source": "backend/app/services/ingestion/tasks.py"},
                    {"from": "pending_review", "to": "approved", "trigger": "HITL verdict: APPROVED", "source": "backend/app/api/routes/audit_v3.py"},
                    {"from": "pending_review", "to": "rejected", "trigger": "HITL verdict: REJECTED", "source": "backend/app/api/routes/audit_v3.py"},
                    {"from": "pending_review", "to": "pending", "trigger": "HITL verdict: RETRY", "source": "backend/app/api/routes/audit_v3.py"},
                ],
            },
            {
                "id": "SM:bad_case",
                "name": "Bad Case Lifecycle",
                "entity": "BadCase",
                "table": "bad_cases",
                "field": "status",
                "initial": "pending",
                "states": ["pending", "reviewed", "fixed", "added_to_dataset"],
                "transitions": [
                    {"from": "pending", "to": "reviewed", "trigger": "learning service processes case", "source": "backend/app/services/learning_service.py"},
                    {"from": "reviewed", "to": "fixed", "trigger": "human provides expected_answer", "source": "backend/app/api/routes/evaluation.py"},
                    {"from": "reviewed", "to": "added_to_dataset", "trigger": "auto-export to SFT dataset", "source": "backend/app/services/evaluation/__init__.py"},
                    {"from": "fixed", "to": "added_to_dataset", "trigger": "export corrected pair to SFT", "source": "backend/app/services/evaluation/__init__.py"},
                ],
            },
            {
                "id": "SM:eval_report",
                "name": "Evaluation Report Status",
                "entity": "EvaluationReport",
                "table": "evaluation_reports",
                "field": "status",
                "initial": "pending",
                "states": ["pending", "running", "completed", "failed"],
                "transitions": [
                    {"from": "pending", "to": "running", "trigger": "evaluation job started", "source": "backend/app/services/evaluation/__init__.py"},
                    {"from": "running", "to": "completed", "trigger": "all items scored", "source": "backend/app/services/evaluation/__init__.py"},
                    {"from": "running", "to": "failed", "trigger": "evaluation error", "source": "backend/app/services/evaluation/__init__.py"},
                ],
            },
            {
                "id": "SM:cognitive_directive",
                "name": "Cognitive Directive Approval",
                "entity": "CognitiveDirective",
                "table": "swarm_cognitive_directives",
                "field": "status",
                "initial": "pending",
                "states": ["pending", "approved", "rejected"],
                "transitions": [
                    {"from": "pending", "to": "approved", "trigger": "admin approves directive", "source": "backend/app/api/routes/governance.py"},
                    {"from": "pending", "to": "rejected", "trigger": "admin rejects directive", "source": "backend/app/api/routes/governance.py"},
                ],
            },
            {
                "id": "SM:prompt_definition",
                "name": "Prompt Governance Lifecycle",
                "entity": "PromptDefinition",
                "table": "gov_prompt_definitions",
                "field": "status",
                "initial": "draft",
                "states": ["draft", "active", "deprecated", "rollback"],
                "transitions": [
                    {"from": "draft", "to": "active", "trigger": "promote to production", "source": "backend/app/api/routes/governance.py"},
                    {"from": "active", "to": "deprecated", "trigger": "new version replaces it", "source": "backend/app/api/routes/governance.py"},
                    {"from": "active", "to": "rollback", "trigger": "emergency rollback", "source": "backend/app/api/routes/governance.py"},
                    {"from": "rollback", "to": "active", "trigger": "re-activate after fix", "source": "backend/app/api/routes/governance.py"},
                ],
            },
            {
                "id": "SM:sync_task",
                "name": "Sync Task Status",
                "entity": "SyncTask",
                "table": "sync_tasks",
                "field": "status",
                "initial": "idle",
                "states": ["idle", "running", "error"],
                "transitions": [
                    {"from": "idle", "to": "running", "trigger": "cron schedule fires", "source": "backend/app/services/sync_service.py"},
                    {"from": "running", "to": "idle", "trigger": "sync completed successfully", "source": "backend/app/services/sync_service.py"},
                    {"from": "running", "to": "idle", "trigger": "sync failed (error logged)", "source": "backend/app/services/sync_service.py"},
                ],
            },
            {
                "id": "SM:document_review",
                "name": "Document Quality Review",
                "entity": "DocumentReview",
                "table": "DocumentReview",
                "field": "status",
                "initial": "pending",
                "states": ["pending", "approved", "rejected", "needs_revision"],
                "transitions": [
                    {"from": "pending", "to": "approved", "trigger": "reviewer approves", "source": "backend/app/api/routes/audit.py"},
                    {"from": "pending", "to": "rejected", "trigger": "reviewer rejects", "source": "backend/app/api/routes/audit.py"},
                    {"from": "pending", "to": "needs_revision", "trigger": "reviewer requests changes", "source": "backend/app/api/routes/audit.py"},
                    {"from": "needs_revision", "to": "pending", "trigger": "author resubmits", "source": "backend/app/api/routes/audit.py"},
                ],
            },
            {
                "id": "SM:finetuning_item",
                "name": "Fine-tuning Item Lifecycle",
                "entity": "FineTuningItem",
                "table": "finetuning_items",
                "field": "status",
                "initial": "pending_review",
                "states": ["pending_review", "verified", "exported"],
                "transitions": [
                    {"from": "pending_review", "to": "verified", "trigger": "human verifies quality", "source": "backend/app/api/routes/finetuning.py"},
                    {"from": "verified", "to": "exported", "trigger": "batch export to SFT dataset", "source": "backend/app/api/routes/finetuning.py"},
                ],
            },
            {
                "id": "SM:todo_item",
                "name": "Swarm Todo Lifecycle",
                "entity": "TodoItem",
                "table": "swarm_todos",
                "field": "status",
                "initial": "pending",
                "states": ["pending", "in_progress", "waiting_user", "completed", "cancelled"],
                "transitions": [
                    {"from": "pending", "to": "in_progress", "trigger": "agent picks up task", "source": "backend/app/agents/tools.py"},
                    {"from": "pending", "to": "cancelled", "trigger": "user or agent cancels", "source": "backend/app/api/routes/agents.py"},
                    {"from": "in_progress", "to": "waiting_user", "trigger": "agent needs user input", "source": "backend/app/agents/memory.py"},
                    {"from": "in_progress", "to": "completed", "trigger": "task finished", "source": "backend/app/agents/memory.py"},
                    {"from": "in_progress", "to": "cancelled", "trigger": "task aborted", "source": "backend/app/agents/memory.py"},
                    {"from": "waiting_user", "to": "in_progress", "trigger": "user provides input", "source": "backend/app/api/routes/agents.py"},
                ],
            },
            {
                "id": "SM:batch_task",
                "name": "Batch Task Status",
                "entity": "TaskUnit",
                "table": "(in-memory)",
                "field": "status",
                "initial": "pending",
                "states": ["pending", "queued", "running", "success", "failed", "cancelled", "retry_wait"],
                "transitions": [
                    {"from": "pending", "to": "queued", "trigger": "dependencies met, added to queue", "source": "backend/app/batch/task_queue.py"},
                    {"from": "queued", "to": "running", "trigger": "worker picks up task", "source": "backend/app/batch/engine.py"},
                    {"from": "running", "to": "success", "trigger": "execution completed", "source": "backend/app/batch/engine.py"},
                    {"from": "running", "to": "failed", "trigger": "max retries exhausted", "source": "backend/app/batch/worker_pool.py"},
                    {"from": "running", "to": "retry_wait", "trigger": "error with retries remaining", "source": "backend/app/batch/worker_pool.py"},
                    {"from": "retry_wait", "to": "queued", "trigger": "retry timer expires", "source": "backend/app/batch/controller.py"},
                    {"from": "pending", "to": "cancelled", "trigger": "dependency failed (fail-fast)", "source": "backend/app/batch/task_queue.py"},
                    {"from": "queued", "to": "cancelled", "trigger": "job cancelled", "source": "backend/app/batch/controller.py"},
                    {"from": "running", "to": "cancelled", "trigger": "job cancelled", "source": "backend/app/batch/controller.py"},
                ],
            },
            {
                "id": "SM:batch_job",
                "name": "Batch Job Status",
                "entity": "BatchJob",
                "table": "(in-memory)",
                "field": "status",
                "initial": "created",
                "states": ["created", "running", "completed", "partial", "failed", "cancelled"],
                "transitions": [
                    {"from": "created", "to": "running", "trigger": "job.start() called", "source": "backend/app/batch/controller.py"},
                    {"from": "running", "to": "completed", "trigger": "all tasks succeeded", "source": "backend/app/batch/engine.py"},
                    {"from": "running", "to": "partial", "trigger": "some tasks succeeded, some failed", "source": "backend/app/batch/controller.py"},
                    {"from": "running", "to": "failed", "trigger": "all tasks failed", "source": "backend/app/batch/controller.py"},
                    {"from": "running", "to": "cancelled", "trigger": "user cancels job", "source": "backend/app/batch/controller.py"},
                ],
            },
            {
                "id": "SM:agent_worker",
                "name": "Agent Worker Lifecycle",
                "entity": "AgentWorker",
                "table": "(in-memory)",
                "field": "status",
                "initial": "idle",
                "states": ["idle", "planning", "executing", "reflecting", "done", "failed"],
                "transitions": [
                    {"from": "idle", "to": "executing", "trigger": "task assigned", "source": "backend/app/services/agents/worker.py"},
                    {"from": "executing", "to": "reflecting", "trigger": "execution completed", "source": "backend/app/services/agents/worker.py"},
                    {"from": "reflecting", "to": "done", "trigger": "reflection passed", "source": "backend/app/services/agents/worker.py"},
                    {"from": "executing", "to": "failed", "trigger": "execution error", "source": "backend/app/services/agents/worker.py"},
                ],
            },
        ]

        sm_count = 0
        state_count = 0
        transition_count = 0

        for sm in machines:
            # Create StateMachine node
            self.run_query("""
                MERGE (sm:ArchNode:StateMachine {id: $id})
                SET sm.name = $name, sm.entity = $entity,
                    sm.field = $field, sm.type = 'StateMachine'
                WITH sm
                OPTIONAL MATCH (t:DBTable {table_name: $table})
                FOREACH (_ IN CASE WHEN t IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (t)-[:HAS_STATE_MACHINE]->(sm)
                )
            """, {"id": sm["id"], "name": sm["name"], "entity": sm["entity"],
                  "field": sm["field"], "table": sm["table"]})
            sm_count += 1

            # Create EntityState nodes
            for state_val in sm["states"]:
                state_id = f"{sm['id']}::{state_val}"
                is_initial = state_val == sm["initial"]
                is_terminal = state_val in ("success", "completed", "done", "exported",
                                            "cancelled", "rejected", "failed", "added_to_dataset")

                self.run_query("""
                    MERGE (s:ArchNode:EntityState {id: $id})
                    SET s.value = $value, s.machine_id = $machine_id,
                        s.is_initial = $is_initial, s.is_terminal = $is_terminal,
                        s.type = 'EntityState'
                    WITH s
                    MATCH (sm:StateMachine {id: $machine_id})
                    MERGE (sm)-[:HAS_STATE]->(s)
                """, {"id": state_id, "value": state_val, "machine_id": sm["id"],
                      "is_initial": is_initial, "is_terminal": is_terminal})
                state_count += 1

                if is_initial:
                    self.run_query("""
                        MATCH (sm:StateMachine {id: $sm_id}), (s:EntityState {id: $state_id})
                        MERGE (sm)-[:INITIAL_STATE]->(s)
                    """, {"sm_id": sm["id"], "state_id": state_id})

            # Create transitions
            for t in sm["transitions"]:
                from_id = f"{sm['id']}::{t['from']}"
                to_id = f"{sm['id']}::{t['to']}"
                self.run_query("""
                    MATCH (from_s:EntityState {id: $from_id})
                    MATCH (to_s:EntityState {id: $to_id})
                    MERGE (from_s)-[r:TRANSITIONS_TO]->(to_s)
                    SET r.trigger = $trigger,
                        r.source_file = $source
                """, {"from_id": from_id, "to_id": to_id,
                      "trigger": t["trigger"], "source": t["source"]})
                transition_count += 1

        logger.info(f"✅ Indexed {sm_count} state machines, {state_count} states, {transition_count} transitions.")

    # ─── Config Dependencies ─────────────────────────────────────────────────

    def index_config_dependencies(self):
        """
        Parse Settings class to extract config keys and map which services depend on them.
        """
        logger.info("⚙️  Indexing configuration dependencies...")

        config_file = BASE_DIR / "backend" / "app" / "sdk" / "core" / "config.py"
        if not config_file.exists():
            return

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                content = f.read()
            tree = ast.parse(content)

            config_count = 0
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef) or node.name != "Settings":
                    continue
                for item in node.body:
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        key = item.target.id
                        if key.startswith("_") or key == "model_config":
                            continue
                        # Determine category
                        category = "general"
                        kl = key.lower()
                        if any(x in kl for x in ["postgres", "database"]):
                            category = "database"
                        elif any(x in kl for x in ["redis"]):
                            category = "redis"
                        elif any(x in kl for x in ["neo4j"]):
                            category = "neo4j"
                        elif any(x in kl for x in ["es_", "elastic"]):
                            category = "elasticsearch"
                        elif any(x in kl for x in ["llm", "openai", "deepseek", "kimi", "ark", "model", "embedding"]):
                            category = "llm"
                        elif any(x in kl for x in ["github", "learning"]):
                            category = "external_learning"
                        elif any(x in kl for x in ["cors", "secret", "auth", "token_expire"]):
                            category = "security"
                        elif any(x in kl for x in ["cb_", "circuit", "governance", "budget", "sandbox"]):
                            category = "governance"
                        elif any(x in kl for x in ["vector", "chroma"]):
                            category = "vector_store"

                        config_id = f"CONFIG:{key}"
                        self.run_query("""
                            MERGE (c:ArchNode:ConfigKey {id: $id})
                            SET c.name = $name, c.category = $category, c.type = 'ConfigKey'
                        """, {"id": config_id, "name": key, "category": category})
                        config_count += 1

            # Link config keys to files that reference them
            # Scan backend for settings.XXX references
            backend_dir = BASE_DIR / "backend" / "app"
            for py_file in backend_dir.rglob("*.py"):
                if any(x in str(py_file) for x in [".venv", "__pycache__", ".agent"]):
                    continue
                try:
                    with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                        src = f.read()
                    if "settings." not in src:
                        continue
                    rel_path = str(py_file.relative_to(BASE_DIR)).replace("\\", "/")
                    refs = set(re.findall(r"settings\.([A-Z][A-Z_0-9]+)", src))
                    for ref in refs:
                        self.run_query("""
                            MATCH (f:File {id: $fpath}), (c:ConfigKey {name: $key})
                            MERGE (f)-[:DEPENDS_ON_CONFIG]->(c)
                        """, {"fpath": rel_path, "key": ref})
                except Exception:
                    pass

            logger.info(f"✅ Indexed {config_count} config keys.")
        except Exception as e:
            logger.warning(f"Failed to parse config: {e}")

    # ─── External Service Dependencies ───────────────────────────────────────

    def index_external_services(self):
        """Map external service dependencies and which components rely on them."""
        logger.info("🌍 Indexing external service dependencies...")

        services = [
            {"id": "EXT:postgresql", "name": "PostgreSQL", "type": "database",
             "config_keys": ["POSTGRES_SERVER", "POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB", "DATABASE_URL"]},
            {"id": "EXT:redis", "name": "Redis", "type": "cache/pubsub",
             "config_keys": ["REDIS_URL"]},
            {"id": "EXT:neo4j", "name": "Neo4j", "type": "graph_database",
             "config_keys": ["NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"]},
            {"id": "EXT:elasticsearch", "name": "Elasticsearch", "type": "search_engine",
             "config_keys": ["ES_HOST", "ES_PORT", "ES_API_KEY"]},
            {"id": "EXT:siliconflow", "name": "SiliconFlow LLM", "type": "llm_provider",
             "config_keys": ["LLM_API_KEY", "LLM_BASE_URL"]},
            {"id": "EXT:moonshot", "name": "Moonshot/Kimi", "type": "llm_provider",
             "config_keys": ["KIMI_API_KEY", "KIMI_API_BASE"]},
            {"id": "EXT:ark", "name": "Volcengine ARK", "type": "llm_provider",
             "config_keys": ["ARK_API_KEY", "ARK_BASE_URL"]},
            {"id": "EXT:zhipu", "name": "Zhipu Embedding", "type": "embedding_provider",
             "config_keys": ["EMBEDDING_API_KEY", "EMBEDDING_MODEL"]},
            {"id": "EXT:github_api", "name": "GitHub API", "type": "external_api",
             "config_keys": ["GITHUB_TOKEN", "GITHUB_REPO_OWNER"]},
            {"id": "EXT:celery", "name": "Celery Worker", "type": "task_queue",
             "config_keys": ["REDIS_URL"]},
        ]

        for svc in services:
            self.run_query("""
                MERGE (s:ArchNode:ExternalService {id: $id})
                SET s.name = $name, s.service_type = $stype, s.type = 'ExternalService'
            """, {"id": svc["id"], "name": svc["name"], "stype": svc["type"]})

            for ck in svc["config_keys"]:
                self.run_query("""
                    MATCH (s:ExternalService {id: $sid}), (c:ConfigKey {name: $ck})
                    MERGE (s)-[:CONFIGURED_BY]->(c)
                """, {"sid": svc["id"], "ck": ck})

        # Link EventChannels to backing services
        channel_backing = [
            ("CHANNEL:write_event_bus", "EXT:redis"),
            ("CHANNEL:blackboard", "EXT:redis"),
            ("CHANNEL:agent_bus", "EXT:celery"),
        ]
        for ch_id, svc_id in channel_backing:
            self.run_query("""
                MATCH (ch:EventChannel {id: $ch}), (s:ExternalService {id: $svc})
                MERGE (ch)-[:BACKED_BY]->(s)
            """, {"ch": ch_id, "svc": svc_id})

        # Link DBTables to PostgreSQL
        self.run_query("""
            MATCH (t:DBTable), (pg:ExternalService {id: 'EXT:postgresql'})
            WHERE NOT t.table_name STARTS WITH '(in-memory)'
            MERGE (t)-[:HOSTED_ON]->(pg)
        """)

        # Link TraceTypes stored in DB to PostgreSQL
        self.run_query("""
            MATCH (tt:TraceType)-[:STORED_IN]->(t:DBTable)-[:HOSTED_ON]->(pg:ExternalService)
            MERGE (tt)-[:DEPENDS_ON_EXTERNAL]->(pg)
        """)

        logger.info(f"✅ Indexed {len(services)} external services.")

    # ─── Alembic Migration Chain ─────────────────────────────────────────────

    def index_alembic_migrations(self):
        """Parse alembic/versions/ to build the migration version chain."""
        logger.info("📦 Indexing Alembic migration chain...")

        versions_dir = BASE_DIR / "backend" / "alembic" / "versions"
        if not versions_dir.exists():
            return

        migration_count = 0
        for py_file in sorted(versions_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()

                revision = None
                down_revision = None
                message = py_file.stem

                for m in re.finditer(r"^revision\s*[:=]\s*['\"]([^'\"]+)['\"]", content, re.MULTILINE):
                    revision = m.group(1)
                for m in re.finditer(r"^down_revision\s*[:=]\s*['\"]([^'\"]*)['\"]", content, re.MULTILINE):
                    down_revision = m.group(1)
                # Extract message from filename: hash_message.py
                parts = py_file.stem.split("_", 1)
                if len(parts) > 1:
                    message = parts[1].replace("_", " ")

                if not revision:
                    continue

                mig_id = f"MIGRATION:{revision}"
                self.run_query("""
                    MERGE (m:ArchNode:Migration {id: $id})
                    SET m.revision = $revision, m.message = $message,
                        m.filename = $filename, m.type = 'Migration'
                """, {"id": mig_id, "revision": revision, "message": message,
                      "filename": py_file.name})
                migration_count += 1

                # Link to parent migration
                if down_revision:
                    self.run_query("""
                        MATCH (child:Migration {revision: $child_rev})
                        MATCH (parent:Migration {revision: $parent_rev})
                        MERGE (child)-[:DEPENDS_ON_MIGRATION]->(parent)
                    """, {"child_rev": revision, "parent_rev": down_revision})

                # Link to tables mentioned in the migration
                table_refs = re.findall(r"op\.create_table\(['\"](\w+)['\"]", content)
                table_refs += re.findall(r"op\.add_column\(['\"](\w+)['\"]", content)
                table_refs += re.findall(r"op\.alter_column\(['\"](\w+)['\"]", content)
                for table_name in set(table_refs):
                    self.run_query("""
                        MATCH (m:Migration {revision: $rev}), (t:DBTable {table_name: $table})
                        MERGE (m)-[:MODIFIES_TABLE]->(t)
                    """, {"rev": revision, "table": table_name})

            except Exception as e:
                logger.warning(f"Failed to parse migration {py_file.name}: {e}")

        logger.info(f"✅ Indexed {migration_count} Alembic migrations.")

    # ─── Governance Gates (Harness) ──────────────────────────────────────────

    def index_governance_gates(self):
        """
        Index all governance gates, circuit breakers, rate limiters, and permission checks.
        """
        logger.info("🛡️  Indexing governance gates and harness system...")

        # 1. Backend Permission enum → GateRule nodes
        auth_schema = BASE_DIR / "backend" / "app" / "schemas" / "auth.py"
        perm_count = 0
        if auth_schema.exists():
            try:
                with open(auth_schema, "r", encoding="utf-8") as f:
                    content = f.read()
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef) and node.name == "Permission":
                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name) and isinstance(item.value, ast.Constant):
                                        perm_name = target.id
                                        perm_value = item.value.value
                                        gate_id = f"GATE:perm:{perm_value}"
                                        self.run_query("""
                                            MERGE (g:ArchNode:GateRule {id: $id})
                                            SET g.name = $name, g.value = $value,
                                                g.gate_type = 'permission', g.type = 'GateRule'
                                        """, {"id": gate_id, "name": perm_name, "value": perm_value})
                                        perm_count += 1
            except Exception as e:
                logger.warning(f"Failed to parse auth schema: {e}")

        # 2. Link API endpoints to their required permissions
        # Scan route files for require_permission(Permission.XXX)
        routes_dir = BASE_DIR / "backend" / "app" / "api" / "routes"
        if routes_dir.exists():
            for route_file in routes_dir.glob("*.py"):
                try:
                    with open(route_file, "r", encoding="utf-8") as f:
                        content = f.read()
                    rel_path = str(route_file.relative_to(BASE_DIR)).replace("\\", "/")

                    # Find all require_permission references
                    for m in re.finditer(r"require_permission\(Permission\.(\w+)\)", content):
                        perm_enum = m.group(1)
                        # Find the nearest route decorator above this line
                        pos = m.start()
                        preceding = content[:pos]
                        route_matches = list(re.finditer(
                            r'@router\.(\w+)\(\s*["\']([^"\']*)["\']', preceding
                        ))
                        if route_matches:
                            last_route = route_matches[-1]
                            method = last_route.group(1).upper()
                            path = last_route.group(2)
                            # Find the matching APIEndpoint
                            self.run_query("""
                                MATCH (ep:APIEndpoint)
                                WHERE ep.path CONTAINS $path AND ep.method = $method
                                MATCH (g:GateRule {name: $perm})
                                MERGE (ep)-[:GUARDED_BY]->(g)
                            """, {"path": path, "method": method, "perm": perm_enum})
                except Exception:
                    pass

        # 3. Circuit Breakers
        circuit_breakers = [
            {"id": "GATE:cb:llm", "name": "LLM Circuit Breaker", "target": "EXT:siliconflow",
             "config": "CB_TIMEOUT_LLM_MS", "source": "backend/app/services/dependency_circuit_breaker.py"},
            {"id": "GATE:cb:es", "name": "Elasticsearch Circuit Breaker", "target": "EXT:elasticsearch",
             "config": "CB_TIMEOUT_ES_MS", "source": "backend/app/services/dependency_circuit_breaker.py"},
            {"id": "GATE:cb:neo4j", "name": "Neo4j Circuit Breaker", "target": "EXT:neo4j",
             "config": "CB_TIMEOUT_NEO4J_MS", "source": "backend/app/services/dependency_circuit_breaker.py"},
            {"id": "GATE:cb:swarm", "name": "Swarm Ingestion Circuit Breaker", "target": None,
             "config": None, "source": "backend/app/services/ingestion/swarm/governance.py"},
            {"id": "GATE:cb:rag", "name": "RAG Gateway Circuit Breaker", "target": None,
             "config": None, "source": "backend/app/services/rag_gateway.py"},
        ]
        for cb in circuit_breakers:
            self.run_query("""
                MERGE (g:ArchNode:GateRule {id: $id})
                SET g.name = $name, g.gate_type = 'circuit_breaker',
                    g.source_file = $source, g.type = 'GateRule'
            """, {"id": cb["id"], "name": cb["name"], "source": cb["source"]})

            if cb["target"]:
                self.run_query("""
                    MATCH (g:GateRule {id: $gid}), (s:ExternalService {id: $sid})
                    MERGE (g)-[:PROTECTS]->(s)
                """, {"gid": cb["id"], "sid": cb["target"]})

            if cb["config"]:
                self.run_query("""
                    MATCH (g:GateRule {id: $gid}), (c:ConfigKey {name: $ck})
                    MERGE (g)-[:CONFIGURED_BY]->(c)
                """, {"gid": cb["id"], "ck": cb["config"]})

        # 4. Rate Limiters
        rate_limiters = [
            {"id": "GATE:rl:api", "name": "API Rate Limiter (60/min)", "scope": "global"},
            {"id": "GATE:rl:chat", "name": "Chat Rate Limiter (20/min)", "scope": "chat"},
            {"id": "GATE:rl:upload", "name": "Upload Rate Limiter (10/min)", "scope": "upload"},
            {"id": "GATE:rl:governance", "name": "Governance Rate Limiter", "scope": "per-route"},
        ]
        for rl in rate_limiters:
            self.run_query("""
                MERGE (g:ArchNode:GateRule {id: $id})
                SET g.name = $name, g.gate_type = 'rate_limiter',
                    g.scope = $scope, g.type = 'GateRule'
            """, {"id": rl["id"], "name": rl["name"], "scope": rl["scope"]})

        # 5. Quality Gates (L3, L4, Phase Gates)
        quality_gates = [
            {"id": "GATE:l3:intelligence", "name": "L3 Intelligence Quality Gate",
             "description": "Minimum agentic quality score >= 0.60",
             "source": "backend/app/sdk/harness/gate_l3_intelligence.py"},
            {"id": "GATE:l4:process_integrity", "name": "L4 Process Integrity Gate",
             "description": "Audit trail integrity and red team resilience",
             "source": "backend/scripts/gate_l4_process_integrity.py"},
            {"id": "GATE:hmer:phase", "name": "HMER Phase Gate",
             "description": "Phase readiness audit for architecture evolution",
             "source": "backend/app/services/observability_service.py"},
            {"id": "GATE:l5:scoping", "name": "L5 Scoping Gate",
             "description": "Query scoping and priority assessment before debate",
             "source": "backend/app/services/agents/debate_orchestrator.py"},
        ]
        for qg in quality_gates:
            self.run_query("""
                MERGE (g:ArchNode:GateRule {id: $id})
                SET g.name = $name, g.gate_type = 'quality_gate',
                    g.description = $desc, g.source_file = $source, g.type = 'GateRule'
            """, {"id": qg["id"], "name": qg["name"], "desc": qg["description"], "source": qg["source"]})

            # Link to source file
            self.run_query("""
                MATCH (g:GateRule {id: $gid}), (f:File {id: $fpath})
                MERGE (f)-[:IMPLEMENTS_GATE]->(g)
            """, {"gid": qg["id"], "fpath": qg["source"]})

        total = perm_count + len(circuit_breakers) + len(rate_limiters) + len(quality_gates)
        logger.info(f"✅ Indexed {total} governance gates ({perm_count} permissions, {len(circuit_breakers)} circuit breakers, {len(rate_limiters)} rate limiters, {len(quality_gates)} quality gates).")

    # ─── Test Coverage Mapping ───────────────────────────────────────────────

    def index_test_coverage(self):
        """Map test files to the API endpoints and state transitions they cover."""
        logger.info("🧪 Indexing test coverage mapping...")

        test_dirs = [
            BASE_DIR / "backend" / "tests",
            BASE_DIR / "frontend" / "e2e",
            BASE_DIR / "frontend" / "tests",
        ]

        test_count = 0
        for test_dir in test_dirs:
            if not test_dir.exists():
                continue
            for test_file in test_dir.rglob("*.py"):
                if not test_file.name.startswith("test_"):
                    continue
                try:
                    with open(test_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    rel_path = str(test_file.relative_to(BASE_DIR)).replace("\\", "/")
                    test_id = f"TEST:{rel_path}"

                    self.run_query("""
                        MERGE (t:ArchNode:TestFile {id: $id})
                        SET t.path = $path, t.name = $name, t.type = 'TestFile'
                        WITH t
                        MATCH (f:File {id: $fpath})
                        MERGE (f)-[:IS_TEST]->(t)
                    """, {"id": test_id, "path": rel_path, "name": test_file.name, "fpath": rel_path})
                    test_count += 1

                    # Link to API endpoints referenced in test
                    api_refs = re.findall(r"['\"](/api/v1/[^'\"]+)['\"]", content)
                    for api_path in set(api_refs):
                        clean = api_path.split("?")[0].rstrip("/")
                        self.run_query("""
                            MATCH (t:TestFile {id: $tid})
                            MATCH (ep:APIEndpoint) WHERE ep.path STARTS WITH $api
                            MERGE (t)-[:COVERS_ENDPOINT]->(ep)
                        """, {"tid": test_id, "api": clean})

                    # Link to state machines referenced in test
                    status_refs = re.findall(r"['\"](\w+)['\"]\s*(?:==|!=|in|not in).*status|status.*['\"](\w+)['\"]", content)
                    for ref_tuple in status_refs:
                        for ref in ref_tuple:
                            if ref:
                                self.run_query("""
                                    MATCH (t:TestFile {id: $tid})
                                    MATCH (s:EntityState {value: $val})
                                    MERGE (t)-[:TESTS_STATE]->(s)
                                """, {"tid": test_id, "val": ref})

                except Exception:
                    pass

            # Also handle .spec.ts E2E tests
            for spec_file in test_dir.rglob("*.spec.ts"):
                try:
                    with open(spec_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    rel_path = str(spec_file.relative_to(BASE_DIR)).replace("\\", "/")
                    test_id = f"TEST:{rel_path}"

                    self.run_query("""
                        MERGE (t:ArchNode:TestFile {id: $id})
                        SET t.path = $path, t.name = $name, t.test_type = 'e2e', t.type = 'TestFile'
                    """, {"id": test_id, "path": rel_path, "name": spec_file.name})
                    test_count += 1

                    # Link to pages navigated in E2E tests
                    page_refs = re.findall(r"goto\(['\"]([^'\"]+)['\"]", content)
                    for page_path in set(page_refs):
                        if page_path.startswith("/"):
                            self.run_query("""
                                MATCH (t:TestFile {id: $tid}), (pg:Page {path: $path})
                                MERGE (t)-[:COVERS_PAGE]->(pg)
                            """, {"tid": test_id, "path": page_path})

                    # Link to API routes mocked in E2E
                    api_mocks = re.findall(r"route\(['\"].*?(/api/v1/[^'\"*]+)", content)
                    for api_path in set(api_mocks):
                        self.run_query("""
                            MATCH (t:TestFile {id: $tid})
                            MATCH (ep:APIEndpoint) WHERE ep.path STARTS WITH $api
                            MERGE (t)-[:COVERS_ENDPOINT]->(ep)
                        """, {"tid": test_id, "api": api_path})

                except Exception:
                    pass

        logger.info(f"✅ Indexed {test_count} test files with coverage mapping.")

    # ─── E2E Test Flow Extraction ────────────────────────────────────────────

    def index_e2e_test_flows(self):
        """
        Parse E2E test files to extract step-by-step test flows with checkpoints and assertions.

        Creates:
          (:TestFlow) — a named end-to-end test scenario
          (:TestStep) — individual checkpoint within a flow
          TestFlow -[:HAS_STEP {seq}]-> TestStep
          TestStep -[:NAVIGATES_TO_PAGE]-> Page
          TestStep -[:ASSERTS_STATE]-> EntityState
          TestStep -[:CALLS_API]-> APIEndpoint
        """
        logger.info("🧪 Indexing E2E test flows with checkpoints...")

        e2e_dirs = [
            BASE_DIR / "frontend" / "e2e",
            BASE_DIR / "frontend" / "tests" / "e2e",
        ]

        flow_count = 0
        step_count = 0

        for e2e_dir in e2e_dirs:
            if not e2e_dir.exists():
                continue

            for spec_file in e2e_dir.rglob("*.spec.ts"):
                try:
                    with open(spec_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()

                    rel_path = str(spec_file.relative_to(BASE_DIR)).replace("\\", "/")

                    # Extract test.describe blocks as flows
                    describe_matches = re.finditer(
                        r"test\.describe\(['\"]([^'\"]+)['\"]", content
                    )
                    for dm in describe_matches:
                        flow_name = dm.group(1)
                        flow_id = f"FLOW:e2e:{rel_path}::{flow_name[:50]}"

                        self.run_query("""
                            MERGE (tf:ArchNode:TestFlow {id: $id})
                            SET tf.name = $name, tf.source_file = $source,
                                tf.type = 'TestFlow'
                            WITH tf
                            MATCH (t:TestFile {path: $source})
                            MERGE (t)-[:DEFINES_FLOW]->(tf)
                        """, {"id": flow_id, "name": flow_name, "source": rel_path})
                        flow_count += 1

                    # Extract Checkpoint comments as steps
                    checkpoint_pattern = re.compile(
                        r"//\s*\[Checkpoint\s+(\d+)[:\s]*([^\]]*)\]",
                        re.IGNORECASE,
                    )
                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        cp_match = checkpoint_pattern.search(line)
                        if not cp_match:
                            continue

                        cp_num = int(cp_match.group(1))
                        cp_name = cp_match.group(2).strip()
                        step_id = f"STEP:{rel_path}::C{cp_num}"

                        # Look ahead for page navigation, assertions, and API calls
                        context_end = min(len(lines), i + 20)
                        context_block = "\n".join(lines[i:context_end])

                        # Extract page navigation
                        page_nav = re.findall(r"goto\(['\"]([^'\"]+)['\"]", context_block)
                        # Extract assertions
                        assertions = re.findall(r"expect\(.*?\)\.(\w+)\(['\"]?([^'\")\n]{0,60})", context_block)
                        assertion_strs = [f"{a[0]}({a[1]})" for a in assertions[:5]]
                        # Extract status checks
                        status_checks = re.findall(r"has-text\(['\"](\w+)['\"]\)", context_block)
                        # Extract API route mocks
                        api_routes = re.findall(r"route\(['\"].*?(/api/v1/[^'\"*]+)", context_block)

                        self.run_query("""
                            MERGE (ts:ArchNode:TestStep {id: $id})
                            SET ts.seq = $seq, ts.name = $name,
                                ts.assertions = $assertions,
                                ts.source_file = $source,
                                ts.type = 'TestStep'
                        """, {
                            "id": step_id, "seq": cp_num, "name": cp_name,
                            "assertions": assertion_strs, "source": rel_path,
                        })
                        step_count += 1

                        # Link to flow
                        # Use the first flow found in this file
                        self.run_query("""
                            MATCH (tf:TestFlow {source_file: $source})
                            MATCH (ts:TestStep {id: $step_id})
                            MERGE (tf)-[r:HAS_STEP]->(ts)
                            SET r.seq = $seq
                        """, {"source": rel_path, "step_id": step_id, "seq": cp_num})

                        # Link to pages
                        for page_path in page_nav:
                            if page_path.startswith("/"):
                                self.run_query("""
                                    MATCH (ts:TestStep {id: $step_id}), (pg:Page {path: $path})
                                    MERGE (ts)-[:NAVIGATES_TO_PAGE]->(pg)
                                """, {"step_id": step_id, "path": page_path})

                        # Link to status states
                        for status_val in status_checks:
                            status_lower = status_val.lower()
                            self.run_query("""
                                MATCH (ts:TestStep {id: $step_id})
                                MATCH (s:EntityState) WHERE toLower(s.value) = $val
                                MERGE (ts)-[:ASSERTS_STATE]->(s)
                            """, {"step_id": step_id, "val": status_lower})

                except Exception as e:
                    logger.warning(f"Failed to parse E2E flow from {spec_file.name}: {e}")

        logger.info(f"✅ Indexed {flow_count} E2E test flows with {step_count} checkpoints.")

    # ─── API Schema Extraction ───────────────────────────────────────────────

    def index_api_schemas(self):
        """
        Parse api.generated.ts to extract request/response schemas for API endpoints.

        Creates:
          (:APISchema) — request or response schema definition
          APIEndpoint -[:REQUEST_SCHEMA]-> APISchema
          APIEndpoint -[:RESPONSE_SCHEMA]-> APISchema
          APISchema -[:HAS_FIELD]-> SchemaField
        """
        logger.info("📋 Indexing API schemas from OpenAPI generated types...")

        api_types_file = BASE_DIR / "frontend" / "src" / "types" / "api.generated.ts"
        if not api_types_file.exists():
            logger.warning("api.generated.ts not found. Skipping schema indexing.")
            return

        try:
            with open(api_types_file, "r", encoding="utf-8") as f:
                content = f.read()

            # 1. Extract schema definitions from components.schemas section
            schema_count = 0

            # Pattern: SchemaName: { ... fields ... }
            # We look for interface-like blocks in the schemas section
            schema_pattern = re.compile(
                r'(?:\/\*\*\s*([^*]*?)\s*\*\/\s*)?'  # optional JSDoc comment
                r'(\w+):\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}',  # name: { fields }
                re.DOTALL,
            )

            # Find the schemas section
            schemas_start = content.find("schemas: {")
            if schemas_start == -1:
                schemas_start = content.find('"schemas"')
            if schemas_start == -1:
                logger.warning("Could not find schemas section in api.generated.ts")
                return

            schemas_section = content[schemas_start:]

            # Extract individual schema blocks
            for m in schema_pattern.finditer(schemas_section):
                doc_comment = (m.group(1) or "").strip()
                schema_name = m.group(2).strip()
                schema_body = m.group(3).strip()

                # Skip internal/wrapper types
                if schema_name.startswith("ApiResponse_") or schema_name in ("paths", "operations"):
                    continue
                if not schema_name[0].isupper():
                    continue

                schema_id = f"SCHEMA:{schema_name}"

                # Extract fields
                fields = []
                field_pattern = re.compile(
                    r'(?:\/\*\*\s*(.*?)\s*\*\/\s*)?'  # optional comment
                    r'(\w+)(\??):\s*([^;]+);',  # name?: type;
                    re.DOTALL,
                )
                for fm in field_pattern.finditer(schema_body):
                    field_doc = (fm.group(1) or "").strip().replace("\n", " ").replace("*", "").strip()
                    field_name = fm.group(2)
                    is_optional = fm.group(3) == "?"
                    field_type = fm.group(4).strip()

                    # Clean up type
                    field_type = re.sub(r'\s+', ' ', field_type)
                    if len(field_type) > 100:
                        field_type = field_type[:100] + "..."

                    fields.append({
                        "name": field_name,
                        "type": field_type,
                        "optional": is_optional,
                        "description": field_doc[:200] if field_doc else "",
                    })

                if not fields:
                    continue

                # Create schema node
                self.run_query("""
                    MERGE (s:ArchNode:APISchema {id: $id})
                    SET s.name = $name, s.description = $doc,
                        s.field_count = $field_count, s.type = 'APISchema'
                """, {
                    "id": schema_id, "name": schema_name,
                    "doc": doc_comment[:200], "field_count": len(fields),
                })
                schema_count += 1

                # Create field nodes (only for important schemas, limit to avoid explosion)
                if len(fields) <= 20:
                    for field in fields:
                        field_id = f"{schema_id}::{field['name']}"
                        self.run_query("""
                            MERGE (f:ArchNode:SchemaField {id: $id})
                            SET f.name = $name, f.field_type = $ftype,
                                f.is_optional = $optional, f.description = $desc,
                                f.type = 'SchemaField'
                            WITH f
                            MATCH (s:APISchema {id: $schema_id})
                            MERGE (s)-[:HAS_FIELD]->(f)
                        """, {
                            "id": field_id, "name": field["name"],
                            "ftype": field["type"], "optional": field["optional"],
                            "desc": field["description"], "schema_id": schema_id,
                        })

            # 2. Link schemas to API endpoints via operation definitions
            # Pattern: "application/json": components["schemas"]["SchemaName"]
            op_pattern = re.compile(
                r'(post|get|put|delete|patch):\s*operations\["([^"]+)"\]'
            )
            req_schema_pattern = re.compile(
                r'requestBody.*?schemas\["(\w+)"\]', re.DOTALL
            )
            resp_schema_pattern = re.compile(
                r'responses.*?200.*?schemas\["(\w+)"\]', re.DOTALL
            )

            # Link by matching endpoint paths to operations
            for path_match in re.finditer(r'"(/api/v1/[^"]+)":\s*\{(.*?)\n    \}', content, re.DOTALL):
                api_path = path_match.group(1).rstrip("/")
                path_block = path_match.group(2)

                for op_match in op_pattern.finditer(path_block):
                    method = op_match.group(1).upper()
                    op_name = op_match.group(2)

                    # Find the operation definition
                    op_def_match = re.search(
                        rf'{re.escape(op_name)}:\s*\{{(.*?)\n    \}}',
                        content, re.DOTALL,
                    )
                    if not op_def_match:
                        continue

                    op_body = op_def_match.group(1)

                    # Request schema
                    req_match = req_schema_pattern.search(op_body)
                    if req_match:
                        req_schema = req_match.group(1)
                        if not req_schema.startswith("ApiResponse"):
                            self.run_query("""
                                MATCH (ep:APIEndpoint) WHERE ep.path = $path AND ep.method = $method
                                MATCH (s:APISchema {name: $schema})
                                MERGE (ep)-[:REQUEST_SCHEMA]->(s)
                            """, {"path": api_path, "method": method, "schema": req_schema})

                    # Response schema
                    resp_match = resp_schema_pattern.search(op_body)
                    if resp_match:
                        resp_schema = resp_match.group(1)
                        # Unwrap ApiResponse wrapper
                        inner_match = re.search(r'ApiResponse_(\w+?)_', resp_schema)
                        actual_schema = inner_match.group(1) if inner_match else resp_schema
                        if actual_schema and not actual_schema.startswith("ApiResponse"):
                            self.run_query("""
                                MATCH (ep:APIEndpoint) WHERE ep.path = $path AND ep.method = $method
                                MATCH (s:APISchema {name: $schema})
                                MERGE (ep)-[:RESPONSE_SCHEMA]->(s)
                            """, {"path": api_path, "method": method, "schema": actual_schema})

            logger.info(f"✅ Indexed {schema_count} API schemas.")

        except Exception as e:
            logger.warning(f"Failed to parse api.generated.ts: {e}")

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
    
    # Phase 1: Structural Indexing (existing)
    indexer.index_requirements()
    indexer.index_designs()
    indexer.index_all_code_files()
    indexer.index_typescript_ast()
    indexer.index_python_ast()
    indexer.index_todo_file()

    # Phase 2: Engineering Process Indexing (new)
    indexer.index_github_prs()
    indexer.index_github_releases()

    # Phase 3: Derived Intelligence (new)
    indexer.index_code_similarity()
    indexer.build_developer_profiles()

    # Phase 4: Business Flow Graph (new)
    indexer.index_page_routes()
    indexer.index_navigation_flows()
    indexer.index_ai_navigation_actions()
    indexer.index_access_control_flows()
    indexer.build_business_flows()

    # Phase 5: Data Model & API Layer (P0)
    indexer.index_database_models()
    indexer.index_api_endpoints()

    # Phase 6: Agent/Swarm Topology & Pipeline (P1)
    indexer.index_agent_swarm_topology()
    indexer.index_pipeline_definitions()

    # Phase 7: Observability & Event Bus (P2)
    indexer.index_observability_traces()
    indexer.index_event_bus_topology()

    # Phase 8: State Machines (Test-Critical)
    indexer.index_state_machines()

    # Phase 9: Config, External Services, Migrations, Gates, Tests
    indexer.index_config_dependencies()
    indexer.index_external_services()
    indexer.index_alembic_migrations()
    indexer.index_governance_gates()
    indexer.index_test_coverage()

    # Phase 10: E2E Flows + API Schemas (Test Completeness)
    indexer.index_e2e_test_flows()
    indexer.index_api_schemas()
    
    indexer.close()
    logger.success("Incremental Architectural Mapping Complete!")

if __name__ == "__main__":
    main()
