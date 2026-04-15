"""
auto_link_requirements.py — 架构漂移自愈引擎 (Semantic Auto-Linker)

两阶段策略:
  Phase 1: 启发式规则匹配 (基于路径/文件名/关键词)
  Phase 2: LLM 语义判定 (处理 Phase 1 无法确定的模糊案例)

运行后会在 Neo4j 中创建 (Requirement)-[:IMPLEMENTED_BY]->(File) 关系。
"""
import os
import re
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger
from neo4j import GraphDatabase

# 同目录下可访问 app
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
load_dotenv(Path(__file__).parent.parent.parent / "backend" / ".env")

# ──────────────────────────────────────────────
# 启发式关键词映射表 (REQ-ID → 关键词集合)
# ──────────────────────────────────────────────
HEURISTIC_MAP = {
    "REQ-001": ["agent", "swarm", "supervisor", "langgraph", "orchestrat", "multi_agent"],
    "REQ-002": ["memory", "vector", "embedding", "chroma", "recall", "retrieval", "knowledge"],
    "REQ-003": ["learn", "evolv", "experience", "self_learn", "distill", "golden_trace"],
    "REQ-004": ["llm", "model", "router", "provider", "openai", "claude", "deepseek", "silicon"],
    "REQ-005": ["skill", "tool", "mcp", "registry", "plugin"],
    "REQ-006": ["chat", "stream", "websocket", "sse", "message", "conversation"],
    "REQ-007": ["governance", "audit", "compliance", "rule", "incident", "contract"],
    "REQ-008": ["rag", "pipeline", "retriev", "rerank", "compress", "generat", "quality"],
    "REQ-009": ["graphrag", "graph_index", "neo4j", "cypher", "knowledge_graph"],
    "REQ-010": ["desensit", "pii", "privacy", "mask", "redact", "acl", "permiss"],
    "REQ-011": ["changelog", "history", "version", "timeline"],
    "REQ-012": ["code", "ast", "parse", "vault", "index_architect", "code_entity"],
    "REQ-013": ["auth", "jwt", "login", "user", "profile", "session", "token"],
    "REQ-014": ["sandbox", "budget", "token_service", "hardening", "security"],
    "REQ-015": ["todo", "task", "sync_gov", "graph_sync", "governance_task"],
    "REQ-027": ["digital_twin", "observ", "metric", "dashboard", "monitor", "telemetry"],
}

# 路径前缀匹配 (最高确信度)
PATH_MAP = {
    "REQ-001": ["agents/swarm", "agents/supervisor", "agents/worker"],
    "REQ-002": ["sdk/memory", "services/knowledge", "vector", "embedding"],
    "REQ-004": ["services/llm", "api/routes/llm", "core/llm"],
    "REQ-005": ["skills/registry", "tools.py", "mcp"],
    "REQ-006": ["api/routes/chat", "api/routes/websocket", "stores/chatStore", "hooks/usechat"],
    "REQ-007": ["api/routes/governance", "audit/", "governance"],
    "REQ-008": ["pipeline", "rag", "steps.py", "retriev"],
    "REQ-009": ["graph_store", "graph_index", "graphrag", "knowledge/G6"],
    "REQ-013": ["api/routes/auth", "stores/authStore", "hooks/useAuth", "core/auth"],
    "REQ-027": ["observability", "monitor", "telemetry", "StatCard", "Dashboard"],
}


class AutoLinker:
    def __init__(self):
        uri = os.getenv("NEO4J_URI")
        user = os.getenv("NEO4J_USER")
        password = os.getenv("NEO4J_PASSWORD")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.linked = 0
        self.skipped = 0
        self.llm_used = 0

    def get_unlinked_files(self):
        """获取所有无需求关联的核心代码文件"""
        with self.driver.session() as session:
            res = session.run("""
            MATCH (f:File)
            WHERE NOT (f)<-[:IMPLEMENTED_BY]-(:Requirement)
              AND NOT f.id CONTAINS ".agent"
              AND NOT f.id CONTAINS "tests/"
              AND NOT f.id CONTAINS "scripts/"
              AND NOT f.id CONTAINS "docs/"
              AND NOT f.id CONTAINS ".venv"
              AND NOT f.id CONTAINS "__pycache__"
              AND f.id IS NOT NULL
            RETURN f.id as path
            """)
            return [r["path"] for r in res]

    def get_requirements(self):
        """从 Neo4j 获取所有需求节点"""
        with self.driver.session() as session:
            res = session.run("MATCH (r:Requirement) RETURN r.id as rid, r.title as title")
            return {r["rid"]: r["title"] or "" for r in res}

    def create_link(self, req_id: str, file_path: str, confidence: str):
        with self.driver.session() as session:
            session.run("""
            MATCH (r:Requirement {id: $rid}), (f:File {id: $fid})
            MERGE (r)-[rel:IMPLEMENTED_BY]->(f)
            SET rel.confidence = $conf, rel.auto_linked = true
            """, rid=req_id, fid=file_path, conf=confidence)
        self.linked += 1
        logger.success(f"[{confidence}] {req_id} --> {file_path}")

    def heuristic_match(self, file_path: str) -> list[str]:
        """Phase 1: 启发式匹配，返回候选 REQ-ID 列表"""
        lower = file_path.lower().replace("\\", "/")
        matches = []

        # Path prefix (HIGH confidence)
        for req_id, prefixes in PATH_MAP.items():
            if any(p in lower for p in prefixes):
                matches.append((req_id, "HIGH"))

        if matches:
            return matches

        # Keyword match (MEDIUM confidence)
        fname = Path(file_path).stem.lower()
        for req_id, keywords in HEURISTIC_MAP.items():
            if any(kw in lower or kw in fname for kw in keywords):
                matches.append((req_id, "MEDIUM"))

        return matches

    def llm_match(self, file_path: str, requirements: dict) -> list[tuple]:
        """Phase 2: LLM 语义判定"""
        try:
            import httpx

            # 读取文件前 30 行作为上下文
            file_snippet = ""
            try:
                base_dir = Path(__file__).parent.parent.parent
                full = base_dir / file_path.replace("/", os.sep)
                if full.exists():
                    with open(full, encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()[:30]
                    file_snippet = "".join(lines)
            except Exception:
                pass

            req_list = "\n".join(
                [f"- {rid}: {title}" for rid, title in list(requirements.items())[:20]]
            )

            prompt = f"""You are an architecture analyst. Given a code file path and its first 30 lines, 
identify which of the listed requirements it implements. 
Return ONLY a JSON array of requirement IDs that this file is most relevant to. 
If unclear, return an empty array []. Return at most 2.

File path: {file_path}
File snippet:
```
{file_snippet[:800]}
```

Available requirements:
{req_list}

JSON array of matching REQ-IDs (e.g., ["REQ-001", "REQ-008"] or []):"""

            api_key = os.getenv("ARK_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("SILICONFLOW_API_KEY")
            api_base = os.getenv("ARK_BASE_URL", "https://api.openai.com/v1")
            model = os.getenv("DEFAULT_MODEL", "gpt-4o-mini")

            response = httpx.post(
                f"{api_base}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 100,
                    "temperature": 0,
                },
                timeout=15,
            )
            resp_data = response.json()
            # Support both OpenAI {choices:[...]} and direct {content:...} formats
            if "choices" in resp_data:
                content = resp_data["choices"][0]["message"]["content"].strip()
            elif "content" in resp_data:
                content = resp_data["content"].strip()
            else:
                logger.debug(f"Unknown API response format: {list(resp_data.keys())}")
                return []
            # Extract JSON array
            match = re.search(r'\[.*?\]', content)
            if match:
                ids = json.loads(match.group())
                self.llm_used += 1
                return [(rid, "LLM") for rid in ids if rid.startswith("REQ-")]
        except Exception as e:
            logger.debug(f"LLM match failed for {file_path}: {e}")
        return []

    def run(self):
        logger.info("Starting Semantic Auto-Linker...")
        files = self.get_unlinked_files()
        requirements = self.get_requirements()
        logger.info(f"Found {len(files)} unlinked files | {len(requirements)} requirements")

        for file_path in files:
            # Phase 1: Heuristic
            matches = self.heuristic_match(file_path)

            # Phase 2: LLM fallback (only if heuristic returned nothing)
            if not matches:
                matches = self.llm_match(file_path, requirements)

            if not matches:
                self.skipped += 1
                logger.debug(f"No match found for: {file_path}")
                continue

            # Deduplicate and link (pick highest confidence)
            seen = set()
            for req_id, confidence in matches:
                if req_id in seen:
                    continue
                if req_id in requirements:
                    seen.add(req_id)
                    self.create_link(req_id, file_path, confidence)

        logger.info(
            f"Auto-Linker Complete | Linked: {self.linked} | Skipped: {self.skipped} | LLM used: {self.llm_used}"
        )


if __name__ == "__main__":
    linker = AutoLinker()
    linker.run()
