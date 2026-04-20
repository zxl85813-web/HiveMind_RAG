import os
import re
import json
import subprocess
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from datetime import datetime
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
        if not self.driver: return []
        try:
            with self.driver.session() as session:
                return session.run(query, params or {}).data()
        except Exception as e:
            logger.error(f"Neo4j Query Failed: {e}\nQuery: {query[:200]}...")
            return []

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

    # ─── GitHub Integration: PR / Review / Release ─────────────────────────────

    def _github_api(self, endpoint: str) -> list[dict] | dict | None:
        """
        Call GitHub REST API with pagination support.
        Reuses existing GITHUB_TOKEN / GITHUB_REPO_OWNER / GITHUB_REPO_NAME from settings or env.
        """
        token = os.getenv("GITHUB_TOKEN", "")
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
                        return data
            except Exception as e:
                logger.warning(f"GitHub API error for {endpoint}: {e}")
                break

        return all_results

    def _gh_cli_available(self) -> bool:
        try:
            res = subprocess.run(["gh", "--version"], capture_output=True, text=True, timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def _gh_cli_json(self, args: list[str]) -> list[dict] | None:
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
            pr_number = pr.get("number")
            pr_title = pr.get("title", "")
            pr_url = pr.get("url") or pr.get("html_url", "")
            pr_branch = pr.get("headRefName") or (pr.get("head", {}) or {}).get("ref", "")

            pr_state = pr.get("state", "").upper()
            if pr.get("mergedAt") or pr.get("merged_at"):
                pr_state = "MERGED"
            elif pr_state == "CLOSED":
                pr_state = "CLOSED"
            else:
                pr_state = "OPEN"

            author_data = pr.get("author") or pr.get("user") or {}
            author_name = author_data.get("login", "unknown")
            created_at = pr.get("createdAt") or pr.get("created_at", "")
            merged_at = pr.get("mergedAt") or pr.get("merged_at", "")
            pr_id = f"PR-{pr_number}"

            self.run_query("""
                MERGE (pr:ArchNode:PullRequest {id: $id})
                SET pr.number = $number, pr.title = $title, pr.status = $status,
                    pr.url = $url, pr.branch = $branch,
                    pr.created_at = $created_at, pr.merged_at = $merged_at,
                    pr.type = 'PullRequest', pr.indexed_at = $now
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

            # Link PR to modified files
            files_data = pr.get("files")
            if files_data is None:
                files_data = self._github_api(f"/pulls/{pr_number}/files")
            if files_data:
                for f in files_data[:50]:
                    file_path = (f.get("filename") or f.get("path", "")).replace("\\", "/")
                    if not file_path:
                        continue
                    self.run_query("""
                        MATCH (pr:PullRequest {id: $pr_id}), (f:File {id: $fpath})
                        MERGE (pr)-[r:MODIFIES]->(f)
                        SET r.additions = $additions, r.deletions = $deletions, r.status = $change_status
                    """, {
                        "pr_id": pr_id, "fpath": file_path,
                        "additions": f.get("additions", 0),
                        "deletions": f.get("deletions", 0),
                        "change_status": f.get("status", "modified"),
                    })

            # Index Reviews
            reviews = self._github_api(f"/pulls/{pr_number}/reviews")
            if reviews is None and self._gh_cli_available():
                reviews = self._gh_cli_json(["pr", "view", str(pr_number), "--json", "reviews"])
                if reviews and isinstance(reviews, dict):
                    reviews = reviews.get("reviews", [])
            if reviews:
                for rv in reviews:
                    reviewer_data = rv.get("user") or rv.get("author") or {}
                    reviewer = reviewer_data.get("login", "unknown")
                    verdict = (rv.get("state") or "").upper()
                    rv_id = f"{pr_id}::review::{reviewer}::{verdict}"
                    submitted_at = rv.get("submitted_at") or rv.get("submittedAt", "")
                    body = (rv.get("body") or "")[:500]
                    self.run_query("""
                        MERGE (rv:ArchNode:Review {id: $rv_id})
                        SET rv.reviewer = $reviewer, rv.verdict = $verdict,
                            rv.submitted_at = $submitted_at, rv.body_snippet = $body, rv.type = 'Review'
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

            # Link PR to Requirements
            pr_body = pr.get("body") or ""
            for rid in set(re.findall(r"REQ-\d+", f"{pr_title} {pr_body}")):
                self.run_query("""
                    MATCH (pr:PullRequest {id: $pr_id}), (r:Requirement {id: $rid})
                    MERGE (pr)-[:ADDRESSES]->(r)
                """, {"pr_id": pr_id, "rid": rid})

        logger.info(f"✅ Indexed {pr_count} PRs and {review_count} reviews.")

    def index_github_releases(self, limit: int = 50):
        """
        Index GitHub Releases into Neo4j.

        Creates:
          (:Release) nodes
          Release -[:INCLUDES_PR]-> PullRequest
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
                SET rel.tag = $tag, rel.name = $name, rel.environment = $env,
                    rel.published_at = $published_at, rel.url = $url,
                    rel.type = 'Release', rel.indexed_at = $now
                MERGE (p:ArchNode:Person {name: $author})
                SET p.id = $author, p.type = 'Person'
                MERGE (p)-[:PUBLISHED]->(rel)
            """, {
                "id": rel_id, "tag": tag, "name": name, "env": env,
                "published_at": published_at, "url": url,
                "author": author, "now": datetime.now().isoformat(),
            })
            rel_count += 1

            # Link release to PRs via merge commits
            try:
                res = subprocess.run(
                    ["git", "log", f"{tag}", "--oneline", "--merges", "-n", "50"],
                    capture_output=True, text=True, encoding="utf-8",
                    errors="ignore", timeout=15, cwd=str(BASE_DIR),
                )
                if res.returncode == 0:
                    for pr_num in set(re.findall(r"#(\d+)", res.stdout)):
                        self.run_query("""
                            MATCH (rel:Release {id: $rel_id}), (pr:PullRequest {number: $pr_num})
                            MERGE (rel)-[:INCLUDES_PR]->(pr)
                        """, {"rel_id": rel_id, "pr_num": int(pr_num)})
            except Exception:
                pass

        logger.info(f"✅ Indexed {rel_count} releases.")

    def build_developer_profiles(self):
        """
        Aggregate developer metrics into DeveloperProfile nodes.
        """
        logger.info("👤 Building Developer Profiles...")
        persons = self.run_query("MATCH (p:Person) RETURN p.name AS name")
        if not persons:
            return

        profile_count = 0
        for person in persons:
            name = person["name"]
            if not name or name == "Unknown":
                continue

            metrics = self.run_query("""
                MATCH (p:Person {name: $name})
                OPTIONAL MATCH (p)-[:COMMITTED]->(f:File)
                WITH p, count(DISTINCT f) AS commit_files
                OPTIONAL MATCH (p)-[:AUTHORED_PR]->(pr:PullRequest)
                WITH p, commit_files,
                     count(pr) AS pr_count,
                     count(CASE WHEN pr.status = 'MERGED' THEN 1 END) AS merged_prs
                OPTIONAL MATCH (p)-[:REVIEWED]->(rv:Review)
                WITH p, commit_files, pr_count, merged_prs,
                     count(rv) AS reviews_given
                OPTIONAL MATCH (p)-[:AUTHORED_PR]->(pr2:PullRequest)-[:HAS_REVIEW]->(rv2:Review)
                WHERE rv2.verdict = 'APPROVED'
                WITH p, commit_files, pr_count, merged_prs, reviews_given,
                     count(DISTINCT pr2) AS approved_prs
                OPTIONAL MATCH (p)-[:COMMITTED]->(f2:File)
                WITH p, commit_files, pr_count, merged_prs, reviews_given, approved_prs,
                     collect(DISTINCT f2.path) AS file_paths
                RETURN commit_files, pr_count, merged_prs, reviews_given, approved_prs, file_paths
            """, {"name": name})

            if not metrics:
                continue

            m = metrics[0]
            pr_count = m.get("pr_count", 0)
            merged_prs = m.get("merged_prs", 0)
            approved_prs = m.get("approved_prs", 0)
            file_paths = m.get("file_paths", [])

            merge_rate = round(merged_prs / pr_count, 3) if pr_count > 0 else 0.0
            approval_rate = round(approved_prs / pr_count, 3) if pr_count > 0 else 0.0

            domain_counter: dict[str, int] = {}
            for fp in file_paths:
                if fp:
                    parts = fp.split("/")
                    domain = "/".join(parts[:3]) if len(parts) >= 3 else "/".join(parts[:2])
                    domain_counter[domain] = domain_counter.get(domain, 0) + 1
            primary_domains = [d[0] for d in sorted(domain_counter.items(), key=lambda x: x[1], reverse=True)[:5]]

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
                "commit_files": m.get("commit_files", 0), "pr_count": pr_count,
                "merged_prs": merged_prs, "merge_rate": merge_rate,
                "approval_rate": approval_rate, "reviews_given": m.get("reviews_given", 0),
                "primary_domains": primary_domains,
                "now": datetime.now().isoformat(),
            })
            profile_count += 1

        logger.info(f"✅ Built {profile_count} developer profiles.")

    def index_code_similarity(self, threshold: float = 0.65):
        """Run AST-based code similarity scan and write SIMILAR_TO relationships."""
        logger.info(f"🔍 Running code similarity scan (threshold={threshold})...")
        try:
            from code_similarity_tool import scan_codebase_similarity
        except ImportError:
            import sys
            script_dir = str(Path(__file__).parent)
            if script_dir not in sys.path:
                sys.path.insert(0, script_dir)
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
        """Parse frontend route config to create Page nodes."""
        logger.info("🗺️  Indexing Page routes from appRoutes config...")

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

                route_pattern = re.compile(
                    r"\{\s*key:\s*['\"](\w+)['\"].*?"
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
                    key, path, label_key, icon = match.group(1), match.group(2), match.group(3), match.group(4)
                    show_in_menu = match.group(5) == "true"
                    category = match.group(6) or "general"
                    permissions = [p.strip().strip("'\"") for p in (match.group(7) or "").split(",") if p.strip()]
                    page_id = f"PAGE:{path}"
                    is_protected = "protectedRoutes" in str(route_file)

                    self.run_query("""
                        MERGE (pg:ArchNode:Page {id: $id})
                        SET pg.path=$path, pg.key=$key, pg.label_key=$label_key, pg.icon=$icon,
                            pg.show_in_menu=$show_in_menu, pg.category=$category,
                            pg.is_protected=$is_protected, pg.type='Page'
                    """, {"id": page_id, "path": path, "key": key, "label_key": label_key,
                          "icon": icon, "show_in_menu": show_in_menu, "category": category,
                          "is_protected": is_protected})
                    page_count += 1

                    for perm in permissions:
                        self.run_query("""
                            MERGE (perm:ArchNode:Permission {id: $perm})
                            SET perm.name=$perm, perm.type='Permission'
                            WITH perm MATCH (pg:Page {id: $page_id})
                            MERGE (pg)-[:REQUIRES_PERMISSION]->(perm)
                        """, {"perm": perm, "page_id": page_id})

                    for pf in [f"frontend/src/pages/{key[0].upper()}{key[1:]}Page.tsx"]:
                        self.run_query("""
                            MATCH (pg:Page {id: $page_id}), (f:File {id: $fpath})
                            MERGE (pg)-[:IMPLEMENTED_BY]->(f)
                        """, {"page_id": page_id, "fpath": pf})

            except Exception as e:
                logger.warning(f"Failed to parse route file {route_file}: {e}")

        logger.info(f"✅ Indexed {page_count} page routes.")

    def index_navigation_flows(self):
        """Parse frontend source to extract navigate() calls and conditions."""
        logger.info("🔀 Indexing navigation flows from frontend source...")

        fe_dir = BASE_DIR / "frontend" / "src"
        if not fe_dir.exists():
            return

        nav_count = 0
        for ts_file in list(fe_dir.rglob("*.tsx")) + list(fe_dir.rglob("*.ts")):
            if any(x in str(ts_file) for x in ["node_modules", ".git", "dist"]):
                continue
            try:
                with open(ts_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if "navigate(" not in content and "<Navigate" not in content:
                    continue

                rel_path = str(ts_file.relative_to(BASE_DIR)).replace("\\", "/")
                source_page = self._resolve_file_to_page(rel_path)
                lines = content.split("\n")

                for i, line in enumerate(lines):
                    targets = re.findall(r"navigate\(\s*['\"]([^'\"]+)['\"]", line)
                    targets += re.findall(r"<Navigate\s+to=['\"]([^'\"]+)['\"]", line)

                    for target_path in targets:
                        if not target_path.startswith("/"):
                            continue
                        ctx_start, ctx_end = max(0, i - 5), min(len(lines), i + 3)
                        ctx = "\n".join(lines[ctx_start:ctx_end])
                        condition = self._extract_navigation_condition(ctx, line)
                        trigger = self._extract_trigger_info(ctx, line)

                        self.run_query("""
                            MERGE (src:ArchNode:Page {id: $src_page})
                            ON CREATE SET src.path=$src_path, src.type='Page'
                            MERGE (tgt:ArchNode:Page {id: $tgt_page})
                            ON CREATE SET tgt.path=$tgt_path, tgt.type='Page'
                            MERGE (src)-[r:NAVIGATES_TO]->(tgt)
                            SET r.trigger=$trigger, r.condition=$condition,
                                r.source_file=$source_file, r.line_number=$line_num
                        """, {
                            "src_page": source_page, "src_path": source_page.replace("PAGE:", ""),
                            "tgt_page": f"PAGE:{target_path}", "tgt_path": target_path,
                            "trigger": trigger, "condition": condition,
                            "source_file": rel_path, "line_num": i + 1,
                        })
                        nav_count += 1
            except Exception as e:
                logger.warning(f"Navigation scan failed for {ts_file.name}: {e}")

        logger.info(f"✅ Indexed {nav_count} navigation flows.")

    def _resolve_file_to_page(self, rel_path: str) -> str:
        page_match = re.search(r"pages/(\w+)Page\.tsx$", rel_path)
        if page_match:
            name = page_match.group(1)
            result = self.run_query("MATCH (pg:Page) WHERE pg.key=$key RETURN pg.id AS id LIMIT 1",
                                    {"key": name[0].lower() + name[1:]})
            if result:
                return result[0]["id"]
        if "guards/" in rel_path:
            return "PAGE:/login"
        if "AppLayout" in rel_path:
            return "PAGE:/"
        return "PAGE:/"

    def _extract_navigation_condition(self, context_block: str, nav_line: str) -> str:
        conditions = []
        for pattern in [r"if\s*\(([^)]{3,80})\)", r"(\w+\s*(?:===|!==)\s*['\"][^'\"]+['\"])",
                        r"(isAuthenticated|hasAccess|hasPermission)",
                        r"(status\s*===?\s*['\"][^'\"]+['\"])", r"(\.status\s*===?\s*['\"][^'\"]+['\"])"]:
            for m in re.findall(pattern, context_block):
                if len(m.strip()) > 3 and "import" not in m:
                    conditions.append(m.strip())
        return "; ".join(conditions[:3]) if conditions else "unconditional"

    def _extract_trigger_info(self, context_block: str, nav_line: str) -> str:
        triggers = []
        for pattern in [r"(?:label|title)\s*[:=]\s*['\"]([^'\"]+)['\"]", r">\s*([^<]{2,30})\s*<"]:
            for m in re.findall(pattern, context_block):
                if m.strip() and not m.strip().startswith("{"):
                    triggers.append(m.strip())
        for pattern in [r"<(Button|Link|Card|MenuItem)", r"onClick", r"<Navigate"]:
            if re.search(pattern, context_block):
                match = re.search(pattern, context_block)
                if match:
                    triggers.append(f"[{match.group(0).strip('<')}]")
        return "; ".join(triggers[:3]) if triggers else "unknown"

    def index_ai_navigation_actions(self):
        """Parse chatStore PAGE_CONTEXT_MAP for AI-driven navigation."""
        logger.info("🤖 Indexing AI-driven navigation actions...")
        chat_store = BASE_DIR / "frontend" / "src" / "stores" / "chatStore.ts"
        if not chat_store.exists():
            return
        try:
            with open(chat_store, "r", encoding="utf-8") as f:
                content = f.read()
            map_match = re.search(r"PAGE_CONTEXT_MAP.*?=\s*\{(.*?)\}\s*;", content, re.DOTALL)
            if not map_match:
                return
            action_count = 0
            action_pattern = re.compile(
                r"\{\s*type:\s*['\"](\w+)['\"].*?label:\s*['\"]([^'\"]+)['\"].*?target:\s*['\"]([^'\"]+)['\"]",
                re.DOTALL,
            )
            page_pattern = re.compile(r"['\"]([^'\"]+)['\"]\s*:\s*\{(.*?)\}(?=\s*,\s*['\"/]|\s*\};)", re.DOTALL)
            for page_match in page_pattern.finditer(map_match.group(1)):
                source_path = page_match.group(1)
                for act in action_pattern.finditer(page_match.group(2)):
                    atype, label, target = act.group(1), act.group(2), act.group(3)
                    if atype == "navigate":
                        self.run_query("""
                            MERGE (src:ArchNode:Page {id: $src}) ON CREATE SET src.path=$sp, src.type='Page'
                            MERGE (tgt:ArchNode:Page {id: $tgt}) ON CREATE SET tgt.path=$tp, tgt.type='Page'
                            MERGE (src)-[r:HAS_AI_ACTION]->(tgt) SET r.label=$label, r.action_type=$atype
                        """, {"src": f"PAGE:{source_path}", "sp": source_path,
                              "tgt": f"PAGE:{target}", "tp": target, "label": label, "atype": atype})
                    else:
                        self.run_query("""
                            MERGE (src:ArchNode:Page {id: $src}) ON CREATE SET src.path=$sp, src.type='Page'
                            MERGE (act:ArchNode:UserAction {id: $aid})
                            SET act.label=$label, act.action_type=$atype, act.target=$target, act.type='UserAction'
                            MERGE (src)-[:HAS_ACTION]->(act)
                        """, {"src": f"PAGE:{source_path}", "sp": source_path,
                              "aid": f"ACTION:{source_path}::{target}", "label": label, "atype": atype, "target": target})
                    action_count += 1
            logger.info(f"✅ Indexed {action_count} AI navigation actions.")
        except Exception as e:
            logger.warning(f"Failed to parse chatStore: {e}")

    def index_access_control_flows(self):
        """Parse ROLE_PERMISSION_MAP to create Role -> Permission -> Page chains."""
        logger.info("🔐 Indexing access control flows...")
        access_file = BASE_DIR / "frontend" / "src" / "config" / "access.ts"
        if not access_file.exists():
            return
        try:
            with open(access_file, "r", encoding="utf-8") as f:
                content = f.read()
            map_match = re.search(r"ROLE_PERMISSION_MAP\s*=\s*\{(.*?)\}\s*as\s+const", content, re.DOTALL)
            if not map_match:
                return
            role_count = 0
            for role_match in re.finditer(r"(\w+)\s*:\s*\[(.*?)\]", map_match.group(1), re.DOTALL):
                role_name = role_match.group(1)
                perms = [p.strip().strip("'\"") for p in role_match.group(2).split(",") if p.strip().strip("'\"")]
                self.run_query("MERGE (role:ArchNode:Role {id: $role}) SET role.name=$role, role.type='Role'", {"role": role_name})
                for perm in perms:
                    self.run_query("""
                        MATCH (role:Role {id: $role})
                        MERGE (p:ArchNode:Permission {id: $perm}) SET p.name=$perm, p.type='Permission'
                        MERGE (role)-[:GRANTS]->(p)
                    """, {"role": role_name, "perm": perm})
                role_count += 1
            logger.info(f"✅ Indexed {role_count} roles with permission mappings.")
        except Exception as e:
            logger.warning(f"Failed to parse access config: {e}")

    def build_business_flows(self):
        """Aggregate navigation chains into named BusinessFlow nodes."""
        logger.info("📊 Building business flow aggregations...")
        known_flows = [
            {"id": "FLOW:auth", "name": "认证流程", "description": "登录 → 权限校验 → 页面/拒绝",
             "steps": ["/login", "/", "/forbidden"]},
            {"id": "FLOW:knowledge-lifecycle", "name": "知识库生命周期",
             "description": "概览 → 知识库 → 评估 → 分析",
             "steps": ["/", "/knowledge", "/evaluation", "/kb-analytics"]},
            {"id": "FLOW:governance", "name": "治理审查流程",
             "description": "开发治理 → 架构资产 → Agent治理 → 安全 → 审计",
             "steps": ["/governance/dev", "/governance/assets", "/governance/agent", "/security", "/audit"]},
            {"id": "FLOW:studio-pipeline", "name": "Studio 创作流程",
             "description": "Studio → Pipeline → Canvas → 批量执行",
             "steps": ["/studio", "/pipelines", "/canvas-lab", "/batch"]},
            {"id": "FLOW:observability", "name": "可观测性流程",
             "description": "Token仪表盘 → 链路追踪 → 审计",
             "steps": ["/token-dashboard", "/trace", "/audit"]},
        ]
        flow_count = 0
        for flow in known_flows:
            self.run_query("""
                MERGE (bf:ArchNode:BusinessFlow {id: $id})
                SET bf.name=$name, bf.description=$description, bf.type='BusinessFlow'
            """, flow)
            for seq, step in enumerate(flow["steps"]):
                self.run_query("""
                    MATCH (bf:BusinessFlow {id: $fid}), (pg:Page {id: $pid})
                    MERGE (bf)-[r:CONTAINS_STEP]->(pg) SET r.seq=$seq
                """, {"fid": flow["id"], "pid": f"PAGE:{step}", "seq": seq})
            flow_count += 1

        # Discover flows from actual navigation chains
        chains = self.run_query("""
            MATCH path = (a:Page)-[:NAVIGATES_TO*2..4]->(b:Page)
            WHERE a <> b
            WITH [n IN nodes(path) | n.path] AS steps, length(path) AS depth
            RETURN DISTINCT steps, depth ORDER BY depth DESC LIMIT 10
        """)
        for chain in (chains or []):
            steps = [s for s in chain.get("steps", []) if s]
            if len(steps) >= 3:
                cid = f"FLOW:discovered:{'->'.join(steps)}"
                self.run_query("""
                    MERGE (bf:ArchNode:BusinessFlow {id: $id})
                    SET bf.name=$name, bf.description='Auto-discovered navigation chain',
                        bf.type='BusinessFlow', bf.is_discovered=true
                """, {"id": cid, "name": " → ".join(steps)})
                for seq, s in enumerate(steps):
                    self.run_query("""
                        MATCH (bf:BusinessFlow {id: $fid}), (pg:Page {id: $pid})
                        MERGE (bf)-[r:CONTAINS_STEP]->(pg) SET r.seq=$seq
                    """, {"fid": cid, "pid": f"PAGE:{s}", "seq": seq})

        logger.info(f"✅ Built {flow_count} predefined + discovered business flows.")

    # ─── P0: Data Model Layer (SQLModel → Neo4j) ────────────────────────────

    def index_database_models(self):
        """Parse backend/app/models/*.py to extract SQLModel table definitions."""
        import ast as _ast
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
                tree = _ast.parse(content)
                rel_path = str(py_file.relative_to(BASE_DIR)).replace("\\", "/")

                for node in _ast.walk(tree):
                    if not isinstance(node, _ast.ClassDef):
                        continue
                    is_table = any(
                        kw.arg == "table" and isinstance(kw.value, _ast.Constant) and kw.value.value is True
                        for kw in node.keywords
                    )
                    if not is_table:
                        continue

                    class_name = node.name
                    table_name = class_name
                    for item in node.body:
                        if isinstance(item, _ast.Assign):
                            for target in item.targets:
                                if isinstance(target, _ast.Name) and target.id == "__tablename__" and isinstance(item.value, _ast.Constant):
                                    table_name = item.value.value

                    table_id = f"TABLE:{table_name}"
                    self.run_query("""
                        MERGE (t:ArchNode:DBTable {id: $id})
                        SET t.table_name=$table_name, t.class_name=$class_name,
                            t.source_file=$source_file, t.type='DBTable'
                        WITH t MATCH (f:File {id: $fpath}) MERGE (f)-[:DEFINES_MODEL]->(t)
                    """, {"id": table_id, "table_name": table_name, "class_name": class_name,
                          "source_file": rel_path, "fpath": rel_path})
                    table_count += 1

                    for item in node.body:
                        if not (isinstance(item, _ast.AnnAssign) and isinstance(item.target, _ast.Name)):
                            continue
                        col_name = item.target.id
                        if col_name.startswith("_"):
                            continue
                        col_type = ""
                        if isinstance(item.annotation, _ast.Name):
                            col_type = item.annotation.id
                        elif isinstance(item.annotation, _ast.Subscript) and isinstance(item.annotation.value, _ast.Name):
                            col_type = item.annotation.value.id
                        elif isinstance(item.annotation, _ast.BinOp) and isinstance(item.annotation.left, _ast.Name):
                            col_type = item.annotation.left.id

                        is_pk = False; is_index = False; fk_target = None
                        if item.value and isinstance(item.value, _ast.Call):
                            for kw in item.value.keywords:
                                if kw.arg == "primary_key" and isinstance(kw.value, _ast.Constant):
                                    is_pk = kw.value.value
                                elif kw.arg == "index" and isinstance(kw.value, _ast.Constant):
                                    is_index = kw.value.value
                                elif kw.arg == "foreign_key" and isinstance(kw.value, _ast.Constant):
                                    fk_target = kw.value.value

                        if col_name == "__tablename__":
                            continue
                        col_id = f"{table_id}::{col_name}"
                        self.run_query("""
                            MERGE (c:ArchNode:DBColumn {id: $id})
                            SET c.name=$name, c.col_type=$col_type, c.is_primary_key=$is_pk,
                                c.is_index=$is_index, c.type='DBColumn'
                            WITH c MATCH (t:DBTable {id: $tid}) MERGE (t)-[:HAS_COLUMN]->(c)
                        """, {"id": col_id, "name": col_name, "col_type": col_type,
                              "is_pk": is_pk, "is_index": is_index, "tid": table_id})

                        if fk_target and "." in fk_target:
                            fk_table, fk_col = fk_target.split(".", 1)
                            self.run_query("""
                                MATCH (src:DBTable {id: $src}), (tgt:DBTable) WHERE tgt.table_name=$fkt
                                MERGE (src)-[r:FOREIGN_KEY]->(tgt)
                                SET r.source_column=$sc, r.target_column=$fc
                            """, {"src": table_id, "fkt": fk_table, "sc": col_name, "fc": fk_col})
                            fk_count += 1
            except Exception as e:
                logger.warning(f"Failed to parse model file {py_file.name}: {e}")

        logger.info(f"✅ Indexed {table_count} DB tables with {fk_count} foreign key relationships.")

    # ─── P0: API Endpoint Layer ──────────────────────────────────────────────

    def index_api_endpoints(self):
        """Parse backend API route files to extract endpoint definitions."""
        import ast as _ast
        logger.info("🌐 Indexing API endpoints from FastAPI route definitions...")

        api_init = BASE_DIR / "backend" / "app" / "api" / "__init__.py"
        router_map = {}
        if api_init.exists():
            try:
                with open(api_init, "r", encoding="utf-8") as f:
                    content = f.read()
                pattern = re.compile(
                    r'include_router\(\s*(\w+)\.router\s*,'
                    r'(?:\s*prefix\s*=\s*["\']([^"\']+)["\'])?,?'
                    r'(?:\s*tags\s*=\s*\[([^\]]*)\])?\s*\)',
                )
                for m in pattern.finditer(content):
                    module = m.group(1)
                    prefix = m.group(2) or ""
                    tags = [t.strip().strip("'\"") for t in (m.group(3) or "").split(",") if t.strip()]
                    router_map[module] = {"prefix": prefix, "tags": tags}
            except Exception as e:
                logger.warning(f"Failed to parse api/__init__.py: {e}")

        routes_dir = BASE_DIR / "backend" / "app" / "api" / "routes"
        if not routes_dir.exists():
            return

        endpoint_count = 0
        for route_file in routes_dir.glob("*.py"):
            if route_file.name.startswith("_"):
                continue
            module_name = route_file.stem
            info = router_map.get(module_name, {"prefix": f"/{module_name}", "tags": []})
            prefix, tags = info["prefix"], info["tags"]
            try:
                with open(route_file, "r", encoding="utf-8") as f:
                    content = f.read()
                rel_path = str(route_file.relative_to(BASE_DIR)).replace("\\", "/")
                tree = _ast.parse(content)

                imported_models = set()
                for n in _ast.walk(tree):
                    if isinstance(n, _ast.ImportFrom) and n.module and "models" in n.module:
                        for alias in n.names:
                            imported_models.add(alias.name)

                for n in _ast.walk(tree):
                    if not isinstance(n, (_ast.FunctionDef, _ast.AsyncFunctionDef)):
                        continue
                    for dec in n.decorator_list:
                        method = None; path = ""
                        if isinstance(dec, _ast.Call) and isinstance(dec.func, _ast.Attribute):
                            attr = dec.func.attr
                            if attr in ("get", "post", "put", "delete", "patch", "websocket"):
                                method = attr.upper()
                                if dec.args and isinstance(dec.args[0], _ast.Constant):
                                    path = dec.args[0].value
                        if not method:
                            continue
                        full_path = f"/api/v1{prefix}{path}".rstrip("/") or f"/api/v1{prefix}"
                        ep_id = f"EP:{method}:{full_path}"
                        self.run_query("""
                            MERGE (ep:ArchNode:APIEndpoint {id: $id})
                            SET ep.method=$method, ep.path=$full_path, ep.handler=$handler,
                                ep.module=$module, ep.tags=$tags, ep.type='APIEndpoint'
                            WITH ep MATCH (f:File {id: $fpath}) MERGE (ep)-[:HANDLED_BY]->(f)
                        """, {"id": ep_id, "method": method, "full_path": full_path,
                              "handler": n.name, "module": module_name, "tags": tags, "fpath": rel_path})
                        endpoint_count += 1

                        func_src = _ast.get_source_segment(content, n) or ""
                        for model in imported_models:
                            if model in func_src:
                                self.run_query("""
                                    MATCH (ep:APIEndpoint {id: $eid}), (t:DBTable {class_name: $m})
                                    MERGE (ep)-[:OPERATES_ON]->(t)
                                """, {"eid": ep_id, "m": model})
            except Exception as e:
                logger.warning(f"Failed to parse route file {route_file.name}: {e}")

        logger.info(f"✅ Indexed {endpoint_count} API endpoints.")

    # ─── P1: Agent/Swarm Topology ────────────────────────────────────────────

    def index_agent_swarm_topology(self):
        """Parse Swarm system: LangGraph nodes, tools, skills, LLM tiers."""
        import ast as _ast
        logger.info("🐝 Indexing Agent/Swarm topology...")

        # 1. LangGraph nodes from swarm.py
        swarm_file = BASE_DIR / "backend" / "app" / "agents" / "swarm.py"
        graph_nodes = []; graph_edges = []; entry_point = "supervisor"
        if swarm_file.exists():
            try:
                with open(swarm_file, "r", encoding="utf-8") as f:
                    content = f.read()
                for m in re.finditer(r'add_node\(\s*["\'](\w+)["\']', content):
                    graph_nodes.append(m.group(1))
                for m in re.finditer(r'add_edge\(\s*["\'](\w+)["\']\s*,\s*["\'](\w+)["\']', content):
                    graph_edges.append((m.group(1), m.group(2)))
                for m in re.finditer(r'["\'](\w+)["\']\s*:\s*["\'](\w+)["\']', content):
                    if m.group(1) in graph_nodes or m.group(2) in graph_nodes:
                        graph_edges.append((m.group(1), m.group(2)))
                em = re.search(r'set_entry_point\(\s*["\'](\w+)["\']', content)
                if em: entry_point = em.group(1)
            except Exception as e:
                logger.warning(f"Failed to parse swarm.py: {e}")

        for n in set(graph_nodes):
            self.run_query("MERGE (sn:ArchNode:SwarmNode {id: $id}) SET sn.name=$name, sn.is_entry_point=$ep, sn.type='SwarmNode'",
                           {"id": f"SWARM_NODE:{n}", "name": n, "ep": n == entry_point})
        seen = set()
        for s, t in graph_edges:
            if t in ("FINISH", "END") or s == t or (s, t) in seen: continue
            seen.add((s, t))
            self.run_query("MATCH (a:SwarmNode {name:$s}) MATCH (b) WHERE (b:SwarmNode OR b:AgentDef) AND b.name=$t MERGE (a)-[:ROUTES_TO]->(b)",
                           {"s": s, "t": t})

        # 2. Native Tools
        tool_count = 0
        for tf in ["backend/app/agents/tools.py", "backend/app/agents/agentic_search.py"]:
            tp = BASE_DIR / tf
            if not tp.exists(): continue
            try:
                with open(tp, "r", encoding="utf-8") as f:
                    src = f.read()
                tree = _ast.parse(src)
                rp = str(tp.relative_to(BASE_DIR)).replace("\\", "/")
                for node in _ast.walk(tree):
                    if not isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)): continue
                    is_tool = any((isinstance(d, _ast.Name) and d.id == "tool") or
                                  (isinstance(d, _ast.Call) and isinstance(d.func, _ast.Name) and d.func.id in ("tool", "hive_tool"))
                                  for d in node.decorator_list)
                    if not is_tool: continue
                    doc = _ast.get_docstring(node) or ""
                    self.run_query("MERGE (t:ArchNode:NativeTool {id:$id}) SET t.name=$name, t.description=$desc, t.source_file=$fp, t.type='NativeTool'",
                                   {"id": f"TOOL:{node.name}", "name": node.name, "desc": doc[:200], "fp": rp})
                    tool_count += 1
            except Exception: pass

        # 3. Skills
        skill_count = 0
        skills_dir = BASE_DIR / "backend" / "app" / "skills"
        if skills_dir.exists():
            for sd in skills_dir.iterdir():
                if not sd.is_dir() or sd.name.startswith("__"): continue
                sm = sd / "SKILL.md"
                if not sm.exists(): continue
                try:
                    md = sm.read_text(encoding="utf-8", errors="ignore")
                    desc = sd.name; ver = "0.1.0"
                    fm = re.search(r'^---\s*\n(.*?)\n---', md, re.DOTALL)
                    if fm:
                        for line in fm.group(1).splitlines():
                            kv = re.match(r'^(\w[\w-]*):\s*"?(.*?)"?\s*$', line)
                            if kv:
                                if kv.group(1) == "description": desc = kv.group(2)
                                elif kv.group(1) == "version": ver = kv.group(2)
                    self.run_query("MERGE (s:ArchNode:SkillDef {id:$id}) SET s.name=$n, s.description=$d, s.version=$v, s.has_tools=$ht, s.type='SkillDef'",
                                   {"id": f"SKILL:{sd.name}", "n": sd.name, "d": desc, "v": ver, "ht": (sd / "tools.py").exists()})
                    skill_count += 1
                except Exception: pass

        # 4. LLM Tiers
        for name, desc in [("SIMPLE","Fast low-cost"),("MEDIUM","Balanced"),("COMPLEX","High-capability"),("REASONING","Deep reasoning")]:
            self.run_query("MERGE (t:ArchNode:LLMTier {id:$id}) SET t.name=$n, t.description=$d, t.type='LLMTier'",
                           {"id": f"LLM_TIER:{name}", "n": name, "d": desc})
        self.run_query("MATCH (sn:SwarmNode {name:'supervisor'}), (t:LLMTier) MERGE (sn)-[:USES_LLM]->(t)")

        logger.info(f"✅ Swarm topology: {len(set(graph_nodes))} nodes, {tool_count} tools, {skill_count} skills.")

    def index_pipeline_definitions(self):
        """Parse Pipeline/Batch system: artifact types, engine stages."""
        import ast as _ast
        logger.info("🔧 Indexing Pipeline definitions...")

        pipeline_file = BASE_DIR / "backend" / "app" / "batch" / "pipeline.py"
        artifact_types = []
        if pipeline_file.exists():
            try:
                with open(pipeline_file, "r", encoding="utf-8") as f:
                    content = f.read()
                tree = _ast.parse(content)
                for node in _ast.walk(tree):
                    if isinstance(node, _ast.ClassDef) and node.name == "ArtifactType":
                        for item in node.body:
                            if isinstance(item, _ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, _ast.Name) and isinstance(item.value, _ast.Constant):
                                        artifact_types.append({"name": target.id, "value": item.value.value})
                for at in artifact_types:
                    self.run_query("MERGE (a:ArchNode:ArtifactType {id:$id}) SET a.name=$n, a.value=$v, a.type='ArtifactType'",
                                   {"id": f"ARTIFACT_TYPE:{at['value']}", "n": at["name"], "v": at["value"]})
            except Exception as e:
                logger.warning(f"Failed to parse pipeline.py: {e}")

        engine_file = BASE_DIR / "backend" / "app" / "batch" / "engine.py"
        if engine_file.exists():
            try:
                with open(engine_file, "r", encoding="utf-8") as f:
                    content = f.read()
                for m in re.finditer(r'async def (\w+_node)\(self', content):
                    self.run_query("MERGE (s:ArchNode:PipelineStage {id:$id}) SET s.name=$n, s.type='PipelineStage'",
                                   {"id": f"PIPELINE_STAGE:{m.group(1)}", "n": m.group(1)})
                self.run_query("MATCH (s:PipelineStage {name:'scheduler_node'}), (w:PipelineStage {name:'worker_node'}) MERGE (s)-[:FEEDS_INTO]->(w)")
            except Exception as e:
                logger.warning(f"Failed to parse engine.py: {e}")

        self.run_query("MATCH (t:DBTable {class_name:'PipelineConfig'}), (s:PipelineStage) MERGE (t)-[:CONFIGURES]->(s)")
        logger.info(f"✅ Pipeline: {len(artifact_types)} artifact types indexed.")

    # ─── P2: Observability Trace Templates ───────────────────────────────────

    def index_observability_traces(self):
        """Map observability trace chain: trace types, DB storage, span nesting."""
        logger.info("📡 Indexing observability trace templates...")
        trace_types = [
            {"id": "TRACE:rag_query", "name": "RAG Query Trace", "table": "obs_rag_query_traces", "desc": "RAG retrieval request tracking"},
            {"id": "TRACE:file_trace", "name": "File Processing Trace", "table": "obs_file_traces", "desc": "Single file ingestion trace"},
            {"id": "TRACE:agent_span", "name": "Agent Span", "table": "obs_agent_spans", "desc": "Agent action within file trace", "parent": "TRACE:file_trace"},
            {"id": "TRACE:swarm_trace", "name": "Swarm Trace", "table": "obs_swarm_traces", "desc": "Multi-agent swarm request trace"},
            {"id": "TRACE:swarm_span", "name": "Swarm Span", "table": "obs_swarm_spans", "desc": "Agent task in swarm trace", "parent": "TRACE:swarm_trace"},
            {"id": "TRACE:llm_metric", "name": "LLM Metric", "table": "obs_llm_metrics", "desc": "Per-model health and cost"},
            {"id": "TRACE:baseline_metric", "name": "Baseline Metric", "table": "obs_baseline_metrics", "desc": "Frontend performance baseline"},
            {"id": "TRACE:hitl_task", "name": "HITL Task", "table": "obs_hitl_tasks", "desc": "Human-in-the-loop review", "parent": "TRACE:file_trace"},
            {"id": "TRACE:ingestion_batch", "name": "Ingestion Batch", "table": "obs_ingestion_batches", "desc": "Batch job tracking"},
            {"id": "TRACE:intent_cache", "name": "Intent Cache", "table": "obs_intent_cache", "desc": "Predictive prefetch cache"},
            {"id": "TRACE:audit_log", "name": "Audit Log", "table": "audit_logs", "desc": "Security audit trail"},
        ]
        for tt in trace_types:
            self.run_query("""
                MERGE (t:ArchNode:TraceType {id:$id}) SET t.name=$name, t.description=$desc, t.type='TraceType'
                WITH t OPTIONAL MATCH (db:DBTable {table_name:$table})
                FOREACH (_ IN CASE WHEN db IS NOT NULL THEN [1] ELSE [] END | MERGE (t)-[:STORED_IN]->(db))
            """, {"id": tt["id"], "name": tt["name"], "desc": tt["desc"], "table": tt["table"]})
            if "parent" in tt:
                self.run_query("MATCH (p:TraceType {id:$pid}), (c:TraceType {id:$cid}) MERGE (p)-[:HAS_SPAN_TYPE]->(c)",
                               {"pid": tt["parent"], "cid": tt["id"]})

        for fp, tid in [("backend/app/services/observability_service.py","TRACE:rag_query"),
                        ("backend/app/services/observability_service.py","TRACE:llm_metric"),
                        ("backend/app/services/rag_gateway.py","TRACE:rag_query"),
                        ("backend/app/agents/engine.py","TRACE:swarm_trace"),
                        ("backend/app/batch/engine.py","TRACE:file_trace"),
                        ("backend/app/audit/logger.py","TRACE:audit_log")]:
            self.run_query("MATCH (f:File {id:$fp}), (t:TraceType {id:$tid}) MERGE (f)-[:EMITS_TRACE]->(t)", {"fp": fp, "tid": tid})

        for prefix, tid in [("/api/v1/chat/completions","TRACE:swarm_trace"),("/api/v1/observability","TRACE:baseline_metric")]:
            self.run_query("MATCH (ep:APIEndpoint) WHERE ep.path STARTS WITH $p MATCH (t:TraceType {id:$tid}) MERGE (ep)-[:PRODUCES_TRACE]->(t)",
                           {"p": prefix, "tid": tid})
        logger.info(f"✅ Indexed {len(trace_types)} trace types.")

    def index_event_bus_topology(self):
        """Map event/message bus channels, event types, producers and consumers."""
        logger.info("📨 Indexing event bus topology...")
        channels = [
            {"id": "CHANNEL:write_event_bus", "name": "WriteEventBus", "transport": "Redis Pub/Sub", "key": "hivemind:kb_write_events", "desc": "KB write events"},
            {"id": "CHANNEL:agent_bus", "name": "AgentMessageBus", "transport": "In-process Pub/Sub", "key": "agent_bus", "desc": "Agent peer-to-peer"},
            {"id": "CHANNEL:websocket", "name": "WebSocket Manager", "transport": "WebSocket", "key": "ws", "desc": "Frontend push notifications"},
            {"id": "CHANNEL:blackboard", "name": "Redis Blackboard", "transport": "Redis Pub/Sub + Hash", "key": "swarm_blackboard", "desc": "Cluster shared memory"},
        ]
        for ch in channels:
            self.run_query("MERGE (c:ArchNode:EventChannel {id:$id}) SET c.name=$n, c.transport=$tr, c.channel_key=$k, c.description=$d, c.type='EventChannel'",
                           {"id": ch["id"], "n": ch["name"], "tr": ch["transport"], "k": ch["key"], "d": ch["desc"]})

        events = [
            ("EVT:document_uploaded","document_uploaded","CHANNEL:write_event_bus"),
            ("EVT:document_linked","document_linked","CHANNEL:write_event_bus"),
            ("EVT:document_unlinked","document_unlinked","CHANNEL:write_event_bus"),
            ("EVT:agent_event","agent_stream_event","CHANNEL:websocket"),
            ("EVT:notification","notification","CHANNEL:websocket"),
            ("EVT:agent_reflection","agent_reflection","CHANNEL:blackboard"),
            ("EVT:agent_coordination","agent_coordination","CHANNEL:agent_bus"),
        ]
        for eid, ename, chid in events:
            self.run_query("MERGE (e:ArchNode:EventType {id:$id}) SET e.name=$n, e.type='EventType' WITH e MATCH (ch:EventChannel {id:$ch}) MERGE (ch)-[:CARRIES]->(e)",
                           {"id": eid, "n": ename, "ch": chid})

        for fp, ch in [("backend/app/api/routes/knowledge.py","CHANNEL:write_event_bus"),
                       ("backend/app/services/write_event_bus.py","CHANNEL:write_event_bus"),
                       ("backend/app/agents/engine.py","CHANNEL:websocket"),
                       ("backend/app/agents/engine.py","CHANNEL:agent_bus"),
                       ("backend/app/agents/bus.py","CHANNEL:agent_bus"),
                       ("backend/app/core/telemetry/blackboard.py","CHANNEL:blackboard"),
                       ("backend/app/services/ws_manager.py","CHANNEL:websocket")]:
            self.run_query("MATCH (f:File {id:$fp}), (ch:EventChannel {id:$ch}) MERGE (f)-[:PUBLISHES_TO]->(ch)", {"fp": fp, "ch": ch})

        for fp, ch in [("backend/app/agents/nodes/agent.py","CHANNEL:agent_bus"),
                       ("backend/app/agents/swarm.py","CHANNEL:agent_bus"),
                       ("frontend/src/stores/wsStore.ts","CHANNEL:websocket"),
                       ("frontend/src/stores/chatStore.ts","CHANNEL:websocket")]:
            self.run_query("MATCH (f:File {id:$fp}), (ch:EventChannel {id:$ch}) MERGE (f)-[:SUBSCRIBES_TO]->(ch)", {"fp": fp, "ch": ch})

        logger.info(f"✅ Indexed {len(channels)} channels, {len(events)} event types.")

    # ─── State Machines (Test-Critical) ──────────────────────────────────────

    def index_state_machines(self):
        """Index entity state machines with all valid transitions from code analysis."""
        logger.info("🔄 Indexing entity state machines...")

        machines = [
            {"id":"SM:kb_document_link","name":"KB Document Link Status","entity":"KnowledgeBaseDocumentLink","table":"knowledge_base_documents","field":"status","initial":"pending",
             "states":["pending","processing","indexed","pending_review","failed"],
             "transitions":[
                 {"from":"pending","to":"processing","trigger":"index_document_task dispatched","source":"backend/app/services/indexing.py"},
                 {"from":"pending","to":"failed","trigger":"document or KB not found","source":"backend/app/services/indexing.py"},
                 {"from":"processing","to":"indexed","trigger":"swarm success (confidence >= 0.8)","source":"backend/app/services/ingestion/tasks.py"},
                 {"from":"processing","to":"pending_review","trigger":"low confidence or flagged","source":"backend/app/services/ingestion/tasks.py"},
                 {"from":"processing","to":"failed","trigger":"critical error","source":"backend/app/services/indexing.py"},
                 {"from":"pending_review","to":"indexed","trigger":"HITL approved","source":"backend/app/api/routes/audit_v3.py"},
                 {"from":"pending_review","to":"failed","trigger":"HITL rejected","source":"backend/app/api/routes/audit_v3.py"},
             ]},
            {"id":"SM:document","name":"Document Parsing Status","entity":"Document","table":"documents","field":"status","initial":"pending",
             "states":["pending","processing","parsed","failed","stale"],
             "transitions":[
                 {"from":"pending","to":"processing","trigger":"ingestion started","source":"backend/app/services/indexing.py"},
                 {"from":"processing","to":"parsed","trigger":"parsing success","source":"backend/app/services/ingestion/tasks.py"},
                 {"from":"processing","to":"failed","trigger":"parsing error","source":"backend/app/services/ingestion/tasks.py"},
                 {"from":"parsed","to":"stale","trigger":"lifecycle expiry","source":"backend/app/services/knowledge/lifecycle.py"},
                 {"from":"stale","to":"pending","trigger":"re-index triggered","source":"backend/app/services/knowledge/lifecycle.py"},
             ]},
            {"id":"SM:file_trace","name":"File Trace Status","entity":"FileTrace","table":"obs_file_traces","field":"status","initial":"pending",
             "states":["pending","running","success","failed","pending_review","approved","rejected"],
             "transitions":[
                 {"from":"pending","to":"running","trigger":"celery worker picks up","source":"backend/app/services/ingestion/tasks.py"},
                 {"from":"running","to":"success","trigger":"confidence >= 0.8","source":"backend/app/services/ingestion/tasks.py"},
                 {"from":"running","to":"pending_review","trigger":"confidence < 0.8","source":"backend/app/services/ingestion/tasks.py"},
                 {"from":"running","to":"failed","trigger":"exception","source":"backend/app/services/ingestion/tasks.py"},
                 {"from":"pending_review","to":"approved","trigger":"HITL APPROVED","source":"backend/app/api/routes/audit_v3.py"},
                 {"from":"pending_review","to":"rejected","trigger":"HITL REJECTED","source":"backend/app/api/routes/audit_v3.py"},
                 {"from":"pending_review","to":"pending","trigger":"HITL RETRY","source":"backend/app/api/routes/audit_v3.py"},
             ]},
            {"id":"SM:bad_case","name":"Bad Case Lifecycle","entity":"BadCase","table":"bad_cases","field":"status","initial":"pending",
             "states":["pending","reviewed","fixed","added_to_dataset"],
             "transitions":[
                 {"from":"pending","to":"reviewed","trigger":"learning service processes","source":"backend/app/services/learning_service.py"},
                 {"from":"reviewed","to":"fixed","trigger":"human provides answer","source":"backend/app/api/routes/evaluation.py"},
                 {"from":"reviewed","to":"added_to_dataset","trigger":"auto-export to SFT","source":"backend/app/services/evaluation/__init__.py"},
                 {"from":"fixed","to":"added_to_dataset","trigger":"export corrected pair","source":"backend/app/services/evaluation/__init__.py"},
             ]},
            {"id":"SM:eval_report","name":"Evaluation Report Status","entity":"EvaluationReport","table":"evaluation_reports","field":"status","initial":"pending",
             "states":["pending","running","completed","failed"],
             "transitions":[
                 {"from":"pending","to":"running","trigger":"evaluation started","source":"backend/app/services/evaluation/__init__.py"},
                 {"from":"running","to":"completed","trigger":"all items scored","source":"backend/app/services/evaluation/__init__.py"},
                 {"from":"running","to":"failed","trigger":"evaluation error","source":"backend/app/services/evaluation/__init__.py"},
             ]},
            {"id":"SM:cognitive_directive","name":"Cognitive Directive Approval","entity":"CognitiveDirective","table":"swarm_cognitive_directives","field":"status","initial":"pending",
             "states":["pending","approved","rejected"],
             "transitions":[
                 {"from":"pending","to":"approved","trigger":"admin approves","source":"backend/app/api/routes/governance.py"},
                 {"from":"pending","to":"rejected","trigger":"admin rejects","source":"backend/app/api/routes/governance.py"},
             ]},
            {"id":"SM:prompt_definition","name":"Prompt Governance Lifecycle","entity":"PromptDefinition","table":"gov_prompt_definitions","field":"status","initial":"draft",
             "states":["draft","active","deprecated","rollback"],
             "transitions":[
                 {"from":"draft","to":"active","trigger":"promote to production","source":"backend/app/api/routes/governance.py"},
                 {"from":"active","to":"deprecated","trigger":"new version replaces","source":"backend/app/api/routes/governance.py"},
                 {"from":"active","to":"rollback","trigger":"emergency rollback","source":"backend/app/api/routes/governance.py"},
                 {"from":"rollback","to":"active","trigger":"re-activate after fix","source":"backend/app/api/routes/governance.py"},
             ]},
            {"id":"SM:sync_task","name":"Sync Task Status","entity":"SyncTask","table":"sync_tasks","field":"status","initial":"idle",
             "states":["idle","running","error"],
             "transitions":[
                 {"from":"idle","to":"running","trigger":"cron fires","source":"backend/app/services/sync_service.py"},
                 {"from":"running","to":"idle","trigger":"sync completed","source":"backend/app/services/sync_service.py"},
                 {"from":"running","to":"idle","trigger":"sync failed (error logged)","source":"backend/app/services/sync_service.py"},
             ]},
            {"id":"SM:document_review","name":"Document Quality Review","entity":"DocumentReview","table":"DocumentReview","field":"status","initial":"pending",
             "states":["pending","approved","rejected","needs_revision"],
             "transitions":[
                 {"from":"pending","to":"approved","trigger":"reviewer approves","source":"backend/app/api/routes/audit.py"},
                 {"from":"pending","to":"rejected","trigger":"reviewer rejects","source":"backend/app/api/routes/audit.py"},
                 {"from":"pending","to":"needs_revision","trigger":"reviewer requests changes","source":"backend/app/api/routes/audit.py"},
                 {"from":"needs_revision","to":"pending","trigger":"author resubmits","source":"backend/app/api/routes/audit.py"},
             ]},
            {"id":"SM:finetuning_item","name":"Fine-tuning Item Lifecycle","entity":"FineTuningItem","table":"finetuning_items","field":"status","initial":"pending_review",
             "states":["pending_review","verified","exported"],
             "transitions":[
                 {"from":"pending_review","to":"verified","trigger":"human verifies","source":"backend/app/api/routes/finetuning.py"},
                 {"from":"verified","to":"exported","trigger":"batch export","source":"backend/app/api/routes/finetuning.py"},
             ]},
            {"id":"SM:todo_item","name":"Swarm Todo Lifecycle","entity":"TodoItem","table":"swarm_todos","field":"status","initial":"pending",
             "states":["pending","in_progress","waiting_user","completed","cancelled"],
             "transitions":[
                 {"from":"pending","to":"in_progress","trigger":"agent picks up","source":"backend/app/agents/tools.py"},
                 {"from":"pending","to":"cancelled","trigger":"cancelled","source":"backend/app/api/routes/agents.py"},
                 {"from":"in_progress","to":"waiting_user","trigger":"needs user input","source":"backend/app/agents/memory.py"},
                 {"from":"in_progress","to":"completed","trigger":"task finished","source":"backend/app/agents/memory.py"},
                 {"from":"in_progress","to":"cancelled","trigger":"aborted","source":"backend/app/agents/memory.py"},
                 {"from":"waiting_user","to":"in_progress","trigger":"user provides input","source":"backend/app/api/routes/agents.py"},
             ]},
            {"id":"SM:batch_task","name":"Batch Task Status","entity":"TaskUnit","table":"(in-memory)","field":"status","initial":"pending",
             "states":["pending","queued","running","success","failed","cancelled","retry_wait"],
             "transitions":[
                 {"from":"pending","to":"queued","trigger":"deps met","source":"backend/app/batch/task_queue.py"},
                 {"from":"queued","to":"running","trigger":"worker picks up","source":"backend/app/batch/engine.py"},
                 {"from":"running","to":"success","trigger":"completed","source":"backend/app/batch/engine.py"},
                 {"from":"running","to":"failed","trigger":"max retries exhausted","source":"backend/app/batch/worker_pool.py"},
                 {"from":"running","to":"retry_wait","trigger":"error with retries left","source":"backend/app/batch/worker_pool.py"},
                 {"from":"retry_wait","to":"queued","trigger":"retry timer","source":"backend/app/batch/controller.py"},
                 {"from":"pending","to":"cancelled","trigger":"dep failed","source":"backend/app/batch/task_queue.py"},
                 {"from":"queued","to":"cancelled","trigger":"job cancelled","source":"backend/app/batch/controller.py"},
             ]},
            {"id":"SM:batch_job","name":"Batch Job Status","entity":"BatchJob","table":"(in-memory)","field":"status","initial":"created",
             "states":["created","running","completed","partial","failed","cancelled"],
             "transitions":[
                 {"from":"created","to":"running","trigger":"job.start()","source":"backend/app/batch/controller.py"},
                 {"from":"running","to":"completed","trigger":"all tasks succeeded","source":"backend/app/batch/engine.py"},
                 {"from":"running","to":"partial","trigger":"some succeeded some failed","source":"backend/app/batch/controller.py"},
                 {"from":"running","to":"failed","trigger":"all tasks failed","source":"backend/app/batch/controller.py"},
                 {"from":"running","to":"cancelled","trigger":"user cancels","source":"backend/app/batch/controller.py"},
             ]},
            {"id":"SM:agent_worker","name":"Agent Worker Lifecycle","entity":"AgentWorker","table":"(in-memory)","field":"status","initial":"idle",
             "states":["idle","planning","executing","reflecting","done","failed"],
             "transitions":[
                 {"from":"idle","to":"executing","trigger":"task assigned","source":"backend/app/services/agents/worker.py"},
                 {"from":"executing","to":"reflecting","trigger":"execution done","source":"backend/app/services/agents/worker.py"},
                 {"from":"reflecting","to":"done","trigger":"reflection passed","source":"backend/app/services/agents/worker.py"},
                 {"from":"executing","to":"failed","trigger":"execution error","source":"backend/app/services/agents/worker.py"},
             ]},
        ]

        sm_count = 0; state_count = 0; transition_count = 0
        terminals = {"success","completed","done","exported","cancelled","rejected","failed","added_to_dataset"}

        for sm in machines:
            self.run_query("""
                MERGE (sm:ArchNode:StateMachine {id:$id}) SET sm.name=$name, sm.entity=$entity, sm.field=$field, sm.type='StateMachine'
                WITH sm OPTIONAL MATCH (t:DBTable {table_name:$table})
                FOREACH (_ IN CASE WHEN t IS NOT NULL THEN [1] ELSE [] END | MERGE (t)-[:HAS_STATE_MACHINE]->(sm))
            """, {"id": sm["id"], "name": sm["name"], "entity": sm["entity"], "field": sm["field"], "table": sm["table"]})
            sm_count += 1

            for sv in sm["states"]:
                sid = sm["id"] + "::" + sv
                self.run_query("""
                    MERGE (s:ArchNode:EntityState {id:$id}) SET s.value=$v, s.machine_id=$mid, s.is_initial=$ii, s.is_terminal=$it, s.type='EntityState'
                    WITH s MATCH (sm:StateMachine {id:$mid}) MERGE (sm)-[:HAS_STATE]->(s)
                """, {"id": sid, "v": sv, "mid": sm["id"], "ii": sv == sm["initial"], "it": sv in terminals})
                state_count += 1
                if sv == sm["initial"]:
                    self.run_query("MATCH (sm:StateMachine {id:$sid}), (s:EntityState {id:$eid}) MERGE (sm)-[:INITIAL_STATE]->(s)",
                                   {"sid": sm["id"], "eid": sid})

            for t in sm["transitions"]:
                self.run_query("""
                    MATCH (f:EntityState {id:$fid}), (t:EntityState {id:$tid})
                    MERGE (f)-[r:TRANSITIONS_TO]->(t) SET r.trigger=$trigger, r.source_file=$src
                """, {"fid": sm["id"]+"::"+t["from"], "tid": sm["id"]+"::"+t["to"], "trigger": t["trigger"], "src": t["source"]})
                transition_count += 1

        logger.info(f"✅ Indexed {sm_count} state machines, {state_count} states, {transition_count} transitions.")

    # ─── Config Dependencies ─────────────────────────────────────────────────

    def index_config_dependencies(self):
        """Parse Settings class to extract config keys and map service dependencies."""
        import ast as _ast
        logger.info("⚙️  Indexing configuration dependencies...")
        config_file = BASE_DIR / "backend" / "app" / "sdk" / "core" / "config.py"
        if not config_file.exists(): return
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                content = f.read()
            tree = _ast.parse(content)
            count = 0
            for node in _ast.walk(tree):
                if not isinstance(node, _ast.ClassDef) or node.name != "Settings": continue
                for item in node.body:
                    if not (isinstance(item, _ast.AnnAssign) and isinstance(item.target, _ast.Name)): continue
                    key = item.target.id
                    if key.startswith("_") or key == "model_config": continue
                    kl = key.lower()
                    cat = "general"
                    for kw, c in [("postgres","database"),("redis","redis"),("neo4j","neo4j"),("es_","elasticsearch"),
                                  ("llm","llm"),("openai","llm"),("kimi","llm"),("ark","llm"),("embedding","llm"),
                                  ("github","external"),("cors","security"),("secret","security"),("cb_","governance"),
                                  ("budget","governance"),("vector","vector_store")]:
                        if kw in kl: cat = c; break
                    self.run_query("MERGE (c:ArchNode:ConfigKey {id:$id}) SET c.name=$n, c.category=$cat, c.type='ConfigKey'",
                                   {"id": f"CONFIG:{key}", "n": key, "cat": cat})
                    count += 1
            # Link files that reference settings.XXX
            for py_file in (BASE_DIR / "backend" / "app").rglob("*.py"):
                if any(x in str(py_file) for x in [".venv","__pycache__"]): continue
                try:
                    with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                        src = f.read()
                    if "settings." not in src: continue
                    rp = str(py_file.relative_to(BASE_DIR)).replace("\\", "/")
                    for ref in set(re.findall(r"settings\.([A-Z][A-Z_0-9]+)", src)):
                        self.run_query("MATCH (f:File {id:$fp}), (c:ConfigKey {name:$k}) MERGE (f)-[:DEPENDS_ON_CONFIG]->(c)", {"fp": rp, "k": ref})
                except Exception: pass
            logger.info(f"✅ Indexed {count} config keys.")
        except Exception as e:
            logger.warning(f"Failed to parse config: {e}")

    def index_external_services(self):
        """Map external service dependencies."""
        logger.info("🌍 Indexing external service dependencies...")
        services = [
            ("EXT:postgresql","PostgreSQL","database",["POSTGRES_SERVER","DATABASE_URL"]),
            ("EXT:redis","Redis","cache/pubsub",["REDIS_URL"]),
            ("EXT:neo4j","Neo4j","graph_database",["NEO4J_URI"]),
            ("EXT:elasticsearch","Elasticsearch","search_engine",["ES_HOST"]),
            ("EXT:siliconflow","SiliconFlow LLM","llm_provider",["LLM_API_KEY"]),
            ("EXT:moonshot","Moonshot/Kimi","llm_provider",["KIMI_API_KEY"]),
            ("EXT:ark","Volcengine ARK","llm_provider",["ARK_API_KEY"]),
            ("EXT:zhipu","Zhipu Embedding","embedding_provider",["EMBEDDING_API_KEY"]),
            ("EXT:github_api","GitHub API","external_api",["GITHUB_TOKEN"]),
            ("EXT:celery","Celery Worker","task_queue",["REDIS_URL"]),
        ]
        for sid, name, stype, cks in services:
            self.run_query("MERGE (s:ArchNode:ExternalService {id:$id}) SET s.name=$n, s.service_type=$st, s.type='ExternalService'",
                           {"id": sid, "n": name, "st": stype})
            for ck in cks:
                self.run_query("MATCH (s:ExternalService {id:$sid}), (c:ConfigKey {name:$ck}) MERGE (s)-[:CONFIGURED_BY]->(c)", {"sid": sid, "ck": ck})
        for ch, svc in [("CHANNEL:write_event_bus","EXT:redis"),("CHANNEL:blackboard","EXT:redis")]:
            self.run_query("MATCH (ch:EventChannel {id:$ch}), (s:ExternalService {id:$svc}) MERGE (ch)-[:BACKED_BY]->(s)", {"ch": ch, "svc": svc})
        self.run_query("MATCH (t:DBTable), (pg:ExternalService {id:'EXT:postgresql'}) WHERE NOT t.table_name STARTS WITH '(in-memory)' MERGE (t)-[:HOSTED_ON]->(pg)")
        logger.info(f"✅ Indexed {len(services)} external services.")

    def index_alembic_migrations(self):
        """Parse alembic/versions/ to build migration chain."""
        logger.info("📦 Indexing Alembic migration chain...")
        versions_dir = BASE_DIR / "backend" / "alembic" / "versions"
        if not versions_dir.exists(): return
        count = 0
        for py_file in sorted(versions_dir.glob("*.py")):
            if py_file.name.startswith("_"): continue
            try:
                with open(py_file, "r", encoding="utf-8") as f:
                    content = f.read()
                rev = None; down = None
                for m in re.finditer(r"^revision\s*[:=]\s*['\"]([^'\"]+)['\"]", content, re.MULTILINE): rev = m.group(1)
                for m in re.finditer(r"^down_revision\s*[:=]\s*['\"]([^'\"]*)['\"]", content, re.MULTILINE): down = m.group(1)
                if not rev: continue
                parts = py_file.stem.split("_", 1)
                msg = parts[1].replace("_", " ") if len(parts) > 1 else py_file.stem
                self.run_query("MERGE (m:ArchNode:Migration {id:$id}) SET m.revision=$rev, m.message=$msg, m.filename=$fn, m.type='Migration'",
                               {"id": f"MIGRATION:{rev}", "rev": rev, "msg": msg, "fn": py_file.name})
                count += 1
                if down:
                    self.run_query("MATCH (c:Migration {revision:$cr}), (p:Migration {revision:$pr}) MERGE (c)-[:DEPENDS_ON_MIGRATION]->(p)", {"cr": rev, "pr": down})
                for table in set(re.findall(r"op\.(?:create_table|add_column|alter_column)\(['\"](\w+)['\"]", content)):
                    self.run_query("MATCH (m:Migration {revision:$rev}), (t:DBTable {table_name:$t}) MERGE (m)-[:MODIFIES_TABLE]->(t)", {"rev": rev, "t": table})
            except Exception: pass
        logger.info(f"✅ Indexed {count} migrations.")

    def index_governance_gates(self):
        """Index governance gates: permissions, circuit breakers, rate limiters, quality gates."""
        import ast as _ast
        logger.info("🛡️  Indexing governance gates...")
        # 1. Permissions
        auth_file = BASE_DIR / "backend" / "app" / "schemas" / "auth.py"
        perm_count = 0
        if auth_file.exists():
            try:
                with open(auth_file, "r", encoding="utf-8") as f:
                    content = f.read()
                tree = _ast.parse(content)
                for node in _ast.walk(tree):
                    if isinstance(node, _ast.ClassDef) and node.name == "Permission":
                        for item in node.body:
                            if isinstance(item, _ast.Assign):
                                for t in item.targets:
                                    if isinstance(t, _ast.Name) and isinstance(item.value, _ast.Constant):
                                        self.run_query("MERGE (g:ArchNode:GateRule {id:$id}) SET g.name=$n, g.value=$v, g.gate_type='permission', g.type='GateRule'",
                                                       {"id": f"GATE:perm:{item.value.value}", "n": t.id, "v": item.value.value})
                                        perm_count += 1
            except Exception: pass

        # Link endpoints to permissions
        routes_dir = BASE_DIR / "backend" / "app" / "api" / "routes"
        if routes_dir.exists():
            for rf in routes_dir.glob("*.py"):
                try:
                    with open(rf, "r", encoding="utf-8") as f:
                        content = f.read()
                    for m in re.finditer(r"require_permission\(Permission\.(\w+)\)", content):
                        perm = m.group(1)
                        preceding = content[:m.start()]
                        routes = list(re.finditer(r'@router\.(\w+)\(\s*["\']([^"\']*)["\']', preceding))
                        if routes:
                            lr = routes[-1]
                            self.run_query("MATCH (ep:APIEndpoint) WHERE ep.path CONTAINS $p AND ep.method=$m MATCH (g:GateRule {name:$perm}) MERGE (ep)-[:GUARDED_BY]->(g)",
                                           {"p": lr.group(2), "m": lr.group(1).upper(), "perm": perm})
                except Exception: pass

        # 2. Circuit Breakers
        for gid, name, target, src in [
            ("GATE:cb:llm","LLM CB","EXT:siliconflow","backend/app/services/dependency_circuit_breaker.py"),
            ("GATE:cb:es","ES CB","EXT:elasticsearch","backend/app/services/dependency_circuit_breaker.py"),
            ("GATE:cb:neo4j","Neo4j CB","EXT:neo4j","backend/app/services/dependency_circuit_breaker.py"),
            ("GATE:cb:swarm","Swarm CB",None,"backend/app/services/ingestion/swarm/governance.py"),
            ("GATE:cb:rag","RAG CB",None,"backend/app/services/rag_gateway.py"),
        ]:
            self.run_query("MERGE (g:ArchNode:GateRule {id:$id}) SET g.name=$n, g.gate_type='circuit_breaker', g.source_file=$s, g.type='GateRule'",
                           {"id": gid, "n": name, "s": src})
            if target:
                self.run_query("MATCH (g:GateRule {id:$gid}), (s:ExternalService {id:$sid}) MERGE (g)-[:PROTECTS]->(s)", {"gid": gid, "sid": target})

        # 3. Rate Limiters
        for gid, name, scope in [("GATE:rl:api","API RL 60/min","global"),("GATE:rl:chat","Chat RL 20/min","chat"),
                                  ("GATE:rl:upload","Upload RL 10/min","upload"),("GATE:rl:governance","Governance RL","per-route")]:
            self.run_query("MERGE (g:ArchNode:GateRule {id:$id}) SET g.name=$n, g.gate_type='rate_limiter', g.scope=$sc, g.type='GateRule'",
                           {"id": gid, "n": name, "sc": scope})

        # 4. Quality Gates
        for gid, name, desc, src in [
            ("GATE:l3:intelligence","L3 Intelligence Gate","Min quality score >= 0.60","backend/app/sdk/harness/gate_l3_intelligence.py"),
            ("GATE:l4:process_integrity","L4 Process Integrity Gate","Audit trail integrity","backend/scripts/gate_l4_process_integrity.py"),
            ("GATE:hmer:phase","HMER Phase Gate","Phase readiness audit","backend/app/services/observability_service.py"),
            ("GATE:l5:scoping","L5 Scoping Gate","Query scoping before debate","backend/app/services/agents/debate_orchestrator.py"),
        ]:
            self.run_query("MERGE (g:ArchNode:GateRule {id:$id}) SET g.name=$n, g.gate_type='quality_gate', g.description=$d, g.source_file=$s, g.type='GateRule'",
                           {"id": gid, "n": name, "d": desc, "s": src})
            self.run_query("MATCH (g:GateRule {id:$gid}), (f:File {id:$fp}) MERGE (f)-[:IMPLEMENTS_GATE]->(g)", {"gid": gid, "fp": src})

        total = perm_count + 5 + 4 + 4
        logger.info(f"✅ Indexed {total} governance gates.")

    def index_test_coverage(self):
        """Map test files to API endpoints and state transitions they cover."""
        logger.info("🧪 Indexing test coverage mapping...")
        test_dirs = [BASE_DIR/"backend"/"tests", BASE_DIR/"frontend"/"e2e", BASE_DIR/"frontend"/"tests"]
        count = 0
        for td in test_dirs:
            if not td.exists(): continue
            for tf in td.rglob("test_*.py"):
                try:
                    with open(tf, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    rp = str(tf.relative_to(BASE_DIR)).replace("\\", "/")
                    tid = f"TEST:{rp}"
                    self.run_query("MERGE (t:ArchNode:TestFile {id:$id}) SET t.path=$p, t.name=$n, t.type='TestFile'", {"id": tid, "p": rp, "n": tf.name})
                    count += 1
                    for api in set(re.findall(r"['\"](/api/v1/[^'\"]+)['\"]", content)):
                        self.run_query("MATCH (t:TestFile {id:$tid}), (ep:APIEndpoint) WHERE ep.path STARTS WITH $api MERGE (t)-[:COVERS_ENDPOINT]->(ep)",
                                       {"tid": tid, "api": api.split("?")[0].rstrip("/")})
                except Exception: pass
            for sf in td.rglob("*.spec.ts"):
                try:
                    with open(sf, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    rp = str(sf.relative_to(BASE_DIR)).replace("\\", "/")
                    tid = f"TEST:{rp}"
                    self.run_query("MERGE (t:ArchNode:TestFile {id:$id}) SET t.path=$p, t.name=$n, t.test_type='e2e', t.type='TestFile'", {"id": tid, "p": rp, "n": sf.name})
                    count += 1
                    for pg in set(re.findall(r"goto\(['\"]([^'\"]+)['\"]", content)):
                        if pg.startswith("/"):
                            self.run_query("MATCH (t:TestFile {id:$tid}), (pg:Page {path:$p}) MERGE (t)-[:COVERS_PAGE]->(pg)", {"tid": tid, "p": pg})
                    for api in set(re.findall(r"route\(['\"].*?(/api/v1/[^'\"*]+)", content)):
                        self.run_query("MATCH (t:TestFile {id:$tid}), (ep:APIEndpoint) WHERE ep.path STARTS WITH $api MERGE (t)-[:COVERS_ENDPOINT]->(ep)",
                                       {"tid": tid, "api": api})
                except Exception: pass
        logger.info(f"✅ Indexed {count} test files.")

    # ─── E2E Test Flow Extraction ────────────────────────────────────────────

    def index_e2e_test_flows(self):
        """Parse E2E tests to extract step-by-step flows with checkpoints and assertions."""
        logger.info("🧪 Indexing E2E test flows with checkpoints...")
        e2e_dirs = [BASE_DIR/"frontend"/"e2e", BASE_DIR/"frontend"/"tests"/"e2e"]
        flow_count = 0; step_count = 0
        for e2e_dir in e2e_dirs:
            if not e2e_dir.exists(): continue
            for spec_file in e2e_dir.rglob("*.spec.ts"):
                try:
                    with open(spec_file, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    rp = str(spec_file.relative_to(BASE_DIR)).replace("\\", "/")

                    for dm in re.finditer(r"test\.describe\(['\"]([^'\"]+)['\"]", content):
                        fid = f"FLOW:e2e:{rp}::{dm.group(1)[:50]}"
                        self.run_query("MERGE (tf:ArchNode:TestFlow {id:$id}) SET tf.name=$n, tf.source_file=$s, tf.type='TestFlow'",
                                       {"id": fid, "n": dm.group(1), "s": rp})
                        self.run_query("MATCH (tf:TestFlow {id:$fid}), (t:TestFile {path:$s}) MERGE (t)-[:DEFINES_FLOW]->(tf)", {"fid": fid, "s": rp})
                        flow_count += 1

                    lines = content.split("\n")
                    for i, line in enumerate(lines):
                        cp = re.search(r"//\s*\[Checkpoint\s+(\d+)[:\s]*([^\]]*)\]", line, re.IGNORECASE)
                        if not cp: continue
                        cp_num = int(cp.group(1)); cp_name = cp.group(2).strip()
                        sid = f"STEP:{rp}::C{cp_num}"
                        ctx = "\n".join(lines[i:min(len(lines), i+20)])
                        pages = re.findall(r"goto\(['\"]([^'\"]+)['\"]", ctx)
                        asserts = [f"{a[0]}({a[1]})" for a in re.findall(r"expect\(.*?\)\.(\w+)\(['\"]?([^'\")\n]{0,60})", ctx)[:5]]
                        statuses = re.findall(r"has-text\(['\"](\w+)['\"]\)", ctx)

                        self.run_query("MERGE (ts:ArchNode:TestStep {id:$id}) SET ts.seq=$seq, ts.name=$n, ts.assertions=$a, ts.source_file=$s, ts.type='TestStep'",
                                       {"id": sid, "seq": cp_num, "n": cp_name, "a": asserts, "s": rp})
                        self.run_query("MATCH (tf:TestFlow {source_file:$s}), (ts:TestStep {id:$sid}) MERGE (tf)-[r:HAS_STEP]->(ts) SET r.seq=$seq",
                                       {"s": rp, "sid": sid, "seq": cp_num})
                        step_count += 1
                        for pg in pages:
                            if pg.startswith("/"):
                                self.run_query("MATCH (ts:TestStep {id:$sid}), (pg:Page {path:$p}) MERGE (ts)-[:NAVIGATES_TO_PAGE]->(pg)", {"sid": sid, "p": pg})
                        for sv in statuses:
                            self.run_query("MATCH (ts:TestStep {id:$sid}), (s:EntityState) WHERE toLower(s.value)=$v MERGE (ts)-[:ASSERTS_STATE]->(s)",
                                           {"sid": sid, "v": sv.lower()})
                except Exception as e:
                    logger.warning(f"Failed to parse E2E flow from {spec_file.name}: {e}")
        logger.info(f"✅ Indexed {flow_count} E2E flows with {step_count} checkpoints.")

    # ─── API Schema Extraction ───────────────────────────────────────────────

    def index_api_schemas(self):
        """Parse api.generated.ts to extract request/response schemas."""
        logger.info("📋 Indexing API schemas from OpenAPI types...")
        api_file = BASE_DIR / "frontend" / "src" / "types" / "api.generated.ts"
        if not api_file.exists():
            logger.warning("api.generated.ts not found."); return
        try:
            with open(api_file, "r", encoding="utf-8") as f:
                content = f.read()
            schemas_start = content.find("schemas: {")
            if schemas_start == -1: schemas_start = content.find('"schemas"')
            if schemas_start == -1: return
            schemas_section = content[schemas_start:]

            schema_count = 0
            schema_pattern = re.compile(r'(?:\/\*\*\s*([^*]*?)\s*\*\/\s*)?(\w+):\s*\{([^}]*(?:\{[^}]*\}[^}]*)*)\}', re.DOTALL)
            field_pattern = re.compile(r'(?:\/\*\*\s*(.*?)\s*\*\/\s*)?(\w+)(\??):\s*([^;]+);', re.DOTALL)

            for m in schema_pattern.finditer(schemas_section):
                doc = (m.group(1) or "").strip()
                name = m.group(2).strip()
                body = m.group(3).strip()
                if name.startswith("ApiResponse_") or not name[0].isupper(): continue

                fields = []
                for fm in field_pattern.finditer(body):
                    fd = (fm.group(1) or "").strip().replace("\n"," ").replace("*","").strip()
                    fn = fm.group(2); ft = re.sub(r'\s+', ' ', fm.group(4).strip())[:100]
                    fields.append({"name": fn, "type": ft, "optional": fm.group(3)=="?", "desc": fd[:200]})
                if not fields: continue

                sid = f"SCHEMA:{name}"
                self.run_query("MERGE (s:ArchNode:APISchema {id:$id}) SET s.name=$n, s.description=$d, s.field_count=$fc, s.type='APISchema'",
                               {"id": sid, "n": name, "d": doc[:200], "fc": len(fields)})
                schema_count += 1

                if len(fields) <= 20:
                    for field in fields:
                        fid = f"{sid}::{field['name']}"
                        self.run_query("""
                            MERGE (f:ArchNode:SchemaField {id:$id}) SET f.name=$n, f.field_type=$ft, f.is_optional=$opt, f.description=$d, f.type='SchemaField'
                            WITH f MATCH (s:APISchema {id:$sid}) MERGE (s)-[:HAS_FIELD]->(f)
                        """, {"id": fid, "n": field["name"], "ft": field["type"], "opt": field["optional"], "d": field["desc"], "sid": sid})

            # Link schemas to endpoints
            for pm in re.finditer(r'"(/api/v1/[^"]+)":\s*\{(.*?)\n    \}', content, re.DOTALL):
                api_path = pm.group(1).rstrip("/")
                block = pm.group(2)
                for om in re.finditer(r'(post|get|put|delete|patch):\s*operations\["([^"]+)"\]', block):
                    method = om.group(1).upper(); op_name = om.group(2)
                    op_def = re.search(rf'{re.escape(op_name)}:\s*\{{(.*?)\n    \}}', content, re.DOTALL)
                    if not op_def: continue
                    ob = op_def.group(1)
                    req = re.search(r'requestBody.*?schemas\["(\w+)"\]', ob, re.DOTALL)
                    if req and not req.group(1).startswith("ApiResponse"):
                        self.run_query("MATCH (ep:APIEndpoint) WHERE ep.path=$p AND ep.method=$m MATCH (s:APISchema {name:$s}) MERGE (ep)-[:REQUEST_SCHEMA]->(s)",
                                       {"p": api_path, "m": method, "s": req.group(1)})
                    resp = re.search(r'responses.*?200.*?schemas\["(\w+)"\]', ob, re.DOTALL)
                    if resp:
                        inner = re.search(r'ApiResponse_(\w+?)_', resp.group(1))
                        actual = inner.group(1) if inner else resp.group(1)
                        if actual and not actual.startswith("ApiResponse"):
                            self.run_query("MATCH (ep:APIEndpoint) WHERE ep.path=$p AND ep.method=$m MATCH (s:APISchema {name:$s}) MERGE (ep)-[:RESPONSE_SCHEMA]->(s)",
                                           {"p": api_path, "m": method, "s": actual})

            logger.info(f"✅ Indexed {schema_count} API schemas.")
        except Exception as e:
            logger.warning(f"Failed to parse api.generated.ts: {e}")

    # ─── Flow Definition Import ──────────────────────────────────────────────

    def index_flow_definitions(self):
        """
        Import APPROVED flow YAML files from docs/flows/ into the graph.

        Creates:
          (:FlowDef) — business flow definition
          (:FlowStep) — individual step with assertions and preconditions
          (:ErrorPath) — error/exception scenario
          FlowDef -[:HAS_STEP {seq}]-> FlowStep
          FlowDef -[:HAS_ERROR_PATH]-> ErrorPath
          FlowStep -[:CALLS_ENDPOINT]-> APIEndpoint
          FlowStep -[:WRITES_TABLE]-> DBTable
          FlowStep -[:EXPECTS_TRANSITION]-> EntityState (via TRANSITIONS_TO)
          FlowStep -[:FIRES_EVENT]-> EventType
          FlowStep -[:REQUIRES_PERM]-> GateRule
          FlowDef -[:ON_PAGE]-> Page
        """
        import yaml as _yaml
        logger.info("📦 Importing flow definitions from docs/flows/...")

        flows_dir = BASE_DIR / "docs" / "flows"
        if not flows_dir.exists():
            logger.warning("docs/flows/ not found.")
            return

        # Clear old flow data for clean re-import
        self.run_query("MATCH (n) WHERE n:FlowDef OR n:FlowStep OR n:ErrorPath DETACH DELETE n")

        flow_count = 0
        step_count = 0
        error_count = 0

        for yaml_file in sorted(flows_dir.glob("*.yaml")):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    content = f.read()
                # Skip comment lines before YAML
                yaml_content = "\n".join(
                    line for line in content.split("\n")
                    if not line.strip().startswith("#") or line.strip().startswith("#")
                )
                data = _yaml.safe_load(yaml_content)
                if not data or data.get("review_status") != "APPROVED":
                    continue

                flow_id = data["id"]
                flow_name = data.get("name", flow_id)
                module = data.get("module", "")
                page = data.get("page", "")
                description = data.get("description", "")

                # Create FlowDef node
                self.run_query("""
                    MERGE (fd:ArchNode:FlowDef {id: $id})
                    SET fd.name = $name, fd.module = $module, fd.page = $page,
                        fd.description = $description, fd.type = 'FlowDef',
                        fd.source_file = $source
                """, {"id": flow_id, "name": flow_name, "module": module,
                      "page": page, "description": description[:500],
                      "source": str(yaml_file.relative_to(BASE_DIR)).replace("\\", "/")})
                flow_count += 1

                # Link to Page
                if page:
                    self.run_query("""
                        MATCH (fd:FlowDef {id: $fid}), (pg:Page {path: $path})
                        MERGE (fd)-[:ON_PAGE]->(pg)
                    """, {"fid": flow_id, "path": page})

                # Import steps
                for step in data.get("steps", []):
                    seq = step.get("seq", 0)
                    step_name = step.get("name", f"Step {seq}")
                    step_id = f"{flow_id}::step::{seq}"
                    step_type = step.get("type", "action")
                    api_str = step.get("api", "")
                    handler = step.get("handler", "")
                    precondition = step.get("precondition", "")

                    # Extract assertions
                    assertions = []
                    resp = step.get("response", {})
                    if isinstance(resp, dict):
                        assertions = resp.get("assert", [])
                    if step.get("assert"):
                        a = step["assert"]
                        assertions = a if isinstance(a, list) else [a]

                    self.run_query("""
                        MERGE (fs:ArchNode:FlowStep {id: $id})
                        SET fs.seq = $seq, fs.name = $name, fs.step_type = $stype,
                            fs.api = $api, fs.handler = $handler,
                            fs.precondition = $precondition,
                            fs.assertions = $assertions,
                            fs.type = 'FlowStep'
                        WITH fs
                        MATCH (fd:FlowDef {id: $fid})
                        MERGE (fd)-[r:HAS_STEP]->(fs)
                        SET r.seq = $seq
                    """, {"id": step_id, "seq": seq, "name": step_name, "stype": step_type,
                          "api": api_str, "handler": handler, "precondition": precondition,
                          "assertions": assertions if isinstance(assertions, list) else [],
                          "fid": flow_id})
                    step_count += 1

                    # Link to APIEndpoint
                    if api_str:
                        parts = api_str.split(" ", 1)
                        if len(parts) == 2:
                            method, path = parts[0], parts[1]
                            self.run_query("""
                                MATCH (fs:FlowStep {id: $sid})
                                MATCH (ep:APIEndpoint) WHERE ep.method = $method AND ep.path = $path
                                MERGE (fs)-[:CALLS_ENDPOINT]->(ep)
                            """, {"sid": step_id, "method": method, "path": path})

                    # Also handle 'apis' list (for verification steps)
                    for api_item in step.get("apis", []):
                        parts = api_item.split(" ", 1)
                        if len(parts) == 2:
                            self.run_query("""
                                MATCH (fs:FlowStep {id: $sid})
                                MATCH (ep:APIEndpoint) WHERE ep.method = $m AND ep.path = $p
                                MERGE (fs)-[:CALLS_ENDPOINT]->(ep)
                            """, {"sid": step_id, "m": parts[0], "p": parts[1]})

                    # Link to DB tables
                    for dw in step.get("db_writes", []):
                        table = dw.get("table")
                        if table:
                            self.run_query("""
                                MATCH (fs:FlowStep {id: $sid}), (t:DBTable {table_name: $table})
                                MERGE (fs)-[r:WRITES_TABLE]->(t)
                                SET r.assert = $assert_text
                            """, {"sid": step_id, "table": table,
                                  "assert_text": dw.get("assert", "")})

                    # Link to state transitions
                    for st in step.get("state_transitions", []):
                        entity = st.get("entity", "")
                        from_state = st.get("from", "")
                        to_state = st.get("to", "")
                        if entity and from_state and to_state:
                            self.run_query("""
                                MATCH (fs:FlowStep {id: $sid})
                                MATCH (sm:StateMachine {entity: $entity})-[:HAS_STATE]->(s1:EntityState {value: $from})
                                MATCH (s1)-[tr:TRANSITIONS_TO]->(s2:EntityState {value: $to})
                                MERGE (fs)-[:EXPECTS_TRANSITION]->(tr)
                            """, {"sid": step_id, "entity": entity,
                                  "from": from_state, "to": to_state})

                    # Link to events
                    for evt in step.get("events", []):
                        evt_type = evt.get("type")
                        if evt_type:
                            self.run_query("""
                                MATCH (fs:FlowStep {id: $sid}), (e:EventType {name: $etype})
                                MERGE (fs)-[:FIRES_EVENT]->(e)
                            """, {"sid": step_id, "etype": evt_type})

                    # Link to permissions
                    for perm in step.get("permissions", []):
                        self.run_query("""
                            MATCH (fs:FlowStep {id: $sid}), (g:GateRule {value: $perm})
                            MERGE (fs)-[:REQUIRES_PERM]->(g)
                        """, {"sid": step_id, "perm": perm})

                    # Link to page navigation
                    step_page = step.get("page")
                    if step_page:
                        self.run_query("""
                            MATCH (fs:FlowStep {id: $sid}), (pg:Page {path: $path})
                            MERGE (fs)-[:ON_PAGE]->(pg)
                        """, {"sid": step_id, "path": step_page})

                # Import error paths
                for ep in data.get("error_paths", []):
                    ep_name = ep.get("name", "Unknown Error")
                    ep_id = f"{flow_id}::error::{ep_name[:40]}"
                    at_step = ep.get("at_step", "")
                    trigger = ep.get("trigger", "")
                    expected = ep.get("expected", "")
                    recovery = ep.get("recovery", "")
                    if isinstance(recovery, list):
                        recovery = "; ".join(recovery)

                    self.run_query("""
                        MERGE (err:ArchNode:ErrorPath {id: $id})
                        SET err.name = $name, err.at_step = $at_step,
                            err.trigger = $trigger, err.expected = $expected,
                            err.recovery = $recovery, err.type = 'ErrorPath'
                        WITH err
                        MATCH (fd:FlowDef {id: $fid})
                        MERGE (fd)-[:HAS_ERROR_PATH]->(err)
                    """, {"id": ep_id, "name": ep_name, "at_step": str(at_step),
                          "trigger": trigger, "expected": expected,
                          "recovery": str(recovery)[:500], "fid": flow_id})
                    error_count += 1

                # Import events at flow level
                for evt in data.get("events", []):
                    evt_type = evt.get("event_type")
                    triggered_at = evt.get("triggered_at_step", evt.get("triggered_at", ""))
                    if evt_type:
                        self.run_query("""
                            MATCH (fd:FlowDef {id: $fid}), (e:EventType {name: $etype})
                            MERGE (fd)-[r:TRIGGERS_EVENT]->(e)
                            SET r.at_step = $at_step
                        """, {"fid": flow_id, "etype": evt_type, "at_step": str(triggered_at)})

            except Exception as e:
                logger.warning(f"Failed to import flow {yaml_file.name}: {e}")

        logger.info(f"✅ Imported {flow_count} flows, {step_count} steps, {error_count} error paths.")

    # ─── Tech Debt / Mock Detection ──────────────────────────────────────────

    def index_tech_debt(self):
        """
        Scan codebase for mock implementations, stubs, TODOs, and unimplemented features.
        Creates TechDebt nodes linked to affected files, APIs, and flows.
        """
        import ast as _ast
        logger.info("🚧 Scanning for tech debt (mocks, stubs, TODOs)...")

        # Predefined known debts from code audit
        known_debts = [
            {"id": "DEBT:mock:learning_subscriptions", "name": "学习订阅管理是 Mock 数据",
             "severity": "high", "category": "mock_data",
             "description": "订阅列表是内存中的硬编码 list (_mock_subscriptions)，增删改不持久化，重启丢失",
             "file": "backend/app/services/learning_service.py", "module": "learning",
             "effort": "medium", "fix": "创建 subscriptions 表，用 SQLModel 持久化"},
            {"id": "DEBT:mock:learning_discoveries", "name": "技术发现列表是 Mock 数据",
             "severity": "high", "category": "mock_data",
             "description": "发现列表也是内存 list (_mock_discoveries)，重启丢失",
             "file": "backend/app/services/learning_service.py", "module": "learning",
             "effort": "medium", "fix": "创建 discoveries 表持久化"},
            {"id": "DEBT:mock:web_search", "name": "Web 搜索工具返回硬编码结果",
             "severity": "high", "category": "mock_implementation",
             "description": "web_search() 返回 'Mock result' 字符串，未接入任何搜索 API (Tavily/Serper)",
             "file": "backend/app/agents/tools.py", "module": "agents",
             "effort": "low", "fix": "接入 Tavily 或 Serper API"},
            {"id": "DEBT:mock:learning_reflection", "name": "反馈反思是 Mock 的",
             "severity": "medium", "category": "mock_implementation",
             "description": "_mock_reflection() 没有真正调 LLM，用硬编码逻辑替代",
             "file": "backend/app/services/learning_service.py", "module": "learning",
             "effort": "low", "fix": "替换为真实 LLM 调用"},
            {"id": "DEBT:mock:auth_mock_user", "name": "前端开发模式使用 Mock 用户",
             "severity": "medium", "category": "mock_auth",
             "description": "VITE_USE_MOCK=true 时跳过真实登录，使用 mock-user-001",
             "file": "frontend/src/stores/authStore.ts", "module": "auth",
             "effort": "low", "fix": "生产环境确保 VITE_USE_MOCK=false"},
            {"id": "DEBT:stub:minio_storage", "name": "MinIO 对象存储未实现",
             "severity": "high", "category": "not_implemented",
             "description": "4 个方法全部 raise NotImplementedError，文件上传用本地磁盘",
             "file": "backend/app/core/storage.py", "module": "storage",
             "effort": "high", "fix": "实现 MinIO SDK 集成"},
            {"id": "DEBT:stub:llm_router_v2", "name": "LLM Router v2 未实现",
             "severity": "low", "category": "not_implemented",
             "description": "llm/router.py 的 route() 方法 raise NotImplementedError，实际用旧版",
             "file": "backend/app/llm/router.py", "module": "llm",
             "effort": "medium", "fix": "完成新版路由器或删除死代码"},
            {"id": "DEBT:stub:shared_memory", "name": "SharedMemoryManager 5 个方法是空壳",
             "severity": "high", "category": "stub",
             "description": "store_episode/recall_episodes/learn/recall_knowledge/decay_old_memories 全部 pass 或 return []",
             "file": "backend/app/agents/memory.py", "module": "agents",
             "effort": "high", "fix": "接入 ChromaDB 或 PostgreSQL 实现持久化记忆"},
            {"id": "DEBT:stub:injection_detection", "name": "安全注入检测是占位符",
             "severity": "medium", "category": "stub",
             "description": "注释: Placeholder for complex AST-based injection detection (Phase 3)",
             "file": "backend/app/services/security/sanitizer.py", "module": "security",
             "effort": "high", "fix": "实现 AST 级别的注入检测"},
            {"id": "DEBT:stub:mineru_parser", "name": "MinerU 文档解析器是 Mock",
             "severity": "medium", "category": "mock_implementation",
             "description": "返回 'Mocked content from MinerU'，未接入真实 MinerU SDK",
             "file": "backend/app/batch/plugins/mineru_parser.py", "module": "ingestion",
             "effort": "medium", "fix": "集成 MinerU SDK"},
            {"id": "DEBT:stub:agent_reflection_recovery", "name": "Agent 反思错误恢复是空壳",
             "severity": "medium", "category": "stub",
             "description": "反思失败时直接 pass，注释: Full recovery required for Phase 5",
             "file": "backend/app/services/agents/worker.py", "module": "agents",
             "effort": "medium", "fix": "实现反思失败的重试/降级逻辑"},
            {"id": "DEBT:limit:audit_log_persistence", "name": "审计日志未持久化到数据库",
             "severity": "high", "category": "incomplete",
             "description": "只写 loguru 日志，注释: TODO 持久化到 audit_logs 表",
             "file": "backend/app/audit/logger.py", "module": "audit",
             "effort": "low", "fix": "在 audit_log() 中写入 audit_logs 表"},
            {"id": "DEBT:limit:python_sandbox", "name": "Python 沙箱用 exec() 不安全",
             "severity": "high", "category": "security_risk",
             "description": "注释: In production, should be replaced by E2B/Modal secure sandbox",
             "file": "backend/app/agents/tools.py", "module": "agents",
             "effort": "medium", "fix": "替换为 E2B 或 Modal 沙箱"},
            {"id": "DEBT:limit:rate_limiter_memory", "name": "限流器是内存版，不支持多实例",
             "severity": "medium", "category": "incomplete",
             "description": "注释: 生产环境应替换为 Redis 实现",
             "file": "backend/app/audit/rate_limiter.py", "module": "audit",
             "effort": "low", "fix": "用 Redis 替换内存 dict"},
            {"id": "DEBT:limit:vector_cleanup", "name": "知识库生命周期清理未触发向量删除",
             "severity": "medium", "category": "incomplete",
             "description": "注释: In a real system, this would trigger a background task for vector db cleanup",
             "file": "backend/app/services/knowledge/lifecycle.py", "module": "knowledge",
             "effort": "medium", "fix": "在 purge 时调用 vector_store.delete_documents()"},
        ]

        debt_count = 0
        for debt in known_debts:
            self.run_query("""
                MERGE (d:ArchNode:TechDebt {id: $id})
                SET d.name = $name, d.severity = $severity, d.category = $category,
                    d.description = $description, d.module = $module,
                    d.effort = $effort, d.fix_suggestion = $fix,
                    d.type = 'TechDebt'
                WITH d
                OPTIONAL MATCH (f:File {id: $file})
                FOREACH (_ IN CASE WHEN f IS NOT NULL THEN [1] ELSE [] END |
                    MERGE (f)-[:HAS_DEBT]->(d)
                )
            """, debt)
            debt_count += 1

            # Link to affected API endpoints
            if debt.get("module"):
                self.run_query("""
                    MATCH (d:TechDebt {id: $did})
                    MATCH (ep:APIEndpoint {module: $module})
                    MERGE (ep)-[:AFFECTED_BY_DEBT]->(d)
                """, {"did": debt["id"], "module": debt["module"]})

            # Link to affected business flows
            if debt.get("module"):
                self.run_query("""
                    MATCH (d:TechDebt {id: $did})
                    MATCH (fd:FlowDef {module: $module})
                    MERGE (fd)-[:AFFECTED_BY_DEBT]->(d)
                """, {"did": debt["id"], "module": debt["module"]})

        # Also scan for TODO/FIXME comments in code and create lightweight debt nodes
        scan_count = 0
        backend_dir = BASE_DIR / "backend" / "app"
        for py_file in backend_dir.rglob("*.py"):
            if any(x in str(py_file) for x in [".venv", "__pycache__", ".agent"]):
                continue
            try:
                with open(py_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line_no, line in enumerate(f, 1):
                        for marker in ["TODO:", "FIXME:", "HACK:", "XXX:"]:
                            if marker in line:
                                comment = line.split(marker, 1)[1].strip()[:100]
                                if not comment or len(comment) < 5:
                                    continue
                                rp = str(py_file.relative_to(BASE_DIR)).replace("\\", "/")
                                todo_id = f"DEBT:todo:{rp}:{line_no}"
                                self.run_query("""
                                    MERGE (d:ArchNode:TechDebt {id: $id})
                                    SET d.name = $comment, d.severity = 'low', d.category = 'todo_comment',
                                        d.line_number = $line, d.type = 'TechDebt'
                                    WITH d
                                    MATCH (f:File {id: $fpath})
                                    MERGE (f)-[:HAS_DEBT]->(d)
                                """, {"id": todo_id, "comment": comment, "line": line_no, "fpath": rp})
                                scan_count += 1
            except Exception:
                pass

        logger.info(f"✅ Indexed {debt_count} known debts + {scan_count} TODO/FIXME comments.")


def main():
    # Load env for Neo4j
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / "backend" / ".env")
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "neo4j123")
    
    indexer = ArchitectureIndexer(uri, user, password)

    # Phase 1: Structural Indexing
    indexer.clear_graph()
    indexer.index_requirements()
    indexer.index_designs()
    indexer.index_source_code()
    indexer.index_dependencies()
    indexer.index_skills()
    indexer.link_files_to_skills()
    indexer.index_tests()

    # Phase 2: Engineering Process Indexing
    indexer.index_github_prs()
    indexer.index_github_releases()

    # Phase 3: Derived Intelligence (Skipped for performance in this run)
    # indexer.index_code_similarity()
    # indexer.build_developer_profiles()

    # Phase 4: Business Flow Graph
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

    # Phase 11: Business Flow Definitions (from YAML)
    indexer.index_flow_definitions()

    # Phase 12: Tech Debt Detection
    indexer.index_tech_debt()

    indexer.close()
    logger.success("Architectural Mapping Complete!")

if __name__ == "__main__":
    main()
