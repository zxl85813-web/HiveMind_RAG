"""
SmartGrepService v2 — Multi-strategy memory search engine.

Three search modes (can be combined):
  1. BM25:       Classic information retrieval algorithm (pure math, no LLM).
  2. Fuzzy:      Trigram + Levenshtein distance for typo tolerance (pure algorithm).
  3. LLM Expand: LLM-powered keyword expansion for maximum semantic reach.

Usage:
    service = get_smart_grep_service()
    # Ultra-fast pure algorithm search (~15ms)
    results = await service.search("database optimization", mode="bm25")
    # Fuzzy typo-tolerant search (~20ms)
    results = await service.search("Mcroservce resiliance", mode="fuzzy")
    # LLM-expanded search (~2s but highest recall)
    results = await service.search("how to make system reliable", mode="llm")
    # Auto mode: BM25 first, fallback to fuzzy if too few results (~20ms avg)
    results = await service.search("database tuning", mode="auto")
"""

import os
import re
import time
from typing import Any, Literal

from loguru import logger
from pydantic import BaseModel
from rank_bm25 import BM25Okapi
from rapidfuzz import fuzz
from rapidfuzz import process as rf_process

from app.services.governance.prompt_service import prompt_service

# ── Data Models ──────────────────────────────────────────────────────

# ── Data Models ──────────────────────────────────────────────────────

class GrepResult(BaseModel):
    filename: str
    line_number: int
    content: str
    context: str
    score: float
    method: str = ""  # "bm25" | "fuzzy" | "llm"
    metadata: dict[str, Any] = {}


class _IndexItem(BaseModel):
    """Internal cache item for a specific directory's index."""
    index: Any  # BM25Okapi
    docs: list[dict[str, Any]]
    timestamp: float
    dir_path: str


# ── Synonym / Stemming Table (Zero-Cost Expansion) ──────────────────
# ── Synonym / Stemming Table (Zero-Cost Expansion) ──────────────────
# This replaces the LLM call for common technical terms.
_SYNONYM_MAP: dict[str, list[str]] = {
    "database": ["db", "postgresql", "postgres", "mysql", "sqlite", "sql", "rdbms"],
    "optimization": ["optimize", "optimizing", "tuning", "performance", "speedup", "fast"],
    "frontend": ["front-end", "ui", "react", "vue", "angular", "javascript", "typescript"],
    "backend": ["back-end", "server", "api", "fastapi", "flask", "django"],
    "testing": ["test", "tests", "unittest", "pytest", "e2e", "playwright", "jest"],
    "deployment": ["deploy", "deploying", "ci", "cd", "vercel", "docker", "kubernetes"],
    "microservice": ["microservices", "micro-service", "service mesh", "distributed"],
    "resilience": ["resilient", "fault tolerance", "circuit breaker", "fallback", "retry"],
    "memory": ["ram", "cache", "caching", "redis", "in-memory", "memoization"],
    "search": ["query", "retrieval", "lookup", "find", "grep", "index"],
    "graph": ["neo4j", "cypher", "knowledge graph", "node", "relationship"],
    "vector": ["embedding", "embeddings", "vectordb", "chroma", "qdrant", "milvus"],
    "governance": ["governance", "lint", "biome", "eslint", "prettier", "code quality"],
    "monitoring": ["observability", "metrics", "logging", "tracing", "dashboard"],
}


def _expand_with_synonyms(query: str) -> list[str]:
    """Zero-cost synonym expansion using a static lookup table."""
    tokens = re.findall(r'\w+', query.lower())
    expanded = set(tokens)
    for token in tokens:
        if token in _SYNONYM_MAP:
            expanded.update(_SYNONYM_MAP[token])
        # Also check if token is a value in the synonym map
        for key, synonyms in _SYNONYM_MAP.items():
            if token in synonyms:
                expanded.add(key)
                expanded.update(synonyms)
    return list(expanded)


# ── Core Service ─────────────────────────────────────────────────────

class SmartGrepService:
    """Multi-strategy memory search engine with BM25, Fuzzy, and LLM modes."""

    def __init__(self, base_data_dir: str = "data/memories"):
        self.base_data_dir = base_data_dir
        os.makedirs(self.base_data_dir, exist_ok=True)
        # Multi-user Index Cache: {dir_path: _IndexItem}
        self._indices: dict[str, _IndexItem] = {}
        self._cache_limit = 10  # Maximum number of directory indices to keep in memory

    def _get_user_logs_dir(self, user_id: str) -> str:
        """Safe path resolve for user logs."""
        # Ensure user_id is alphanumeric to prevent path traversal
        safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '', user_id)
        path = os.path.join(self.base_data_dir, safe_id, "logs")
        os.makedirs(path, exist_ok=True)
        return path

    # ── Index Builder ────────────────────────────────────────────────

    def _build_bm25_index(self, data_dir: str) -> _IndexItem | None:
        """Build or retrieve a cached BM25 index for a directory."""
        # 1. Check cache
        if data_dir in self._indices:
            item = self._indices[data_dir]
            item.timestamp = time.time()  # Update LRU
            return item

        # 2. Evict old cache if limit reached
        if len(self._indices) >= self._cache_limit:
            oldest_key = min(self._indices.keys(), key=lambda k: self._indices[k].timestamp)
            del self._indices[oldest_key]

        # 3. Build new index
        start = time.perf_counter()
        docs = []
        corpus_tokens: list[list[str]] = []

        if not os.path.exists(data_dir):
            return None

        # Check if directory is empty
        files = [f for f in os.listdir(data_dir) if f.endswith(".md")]
        if not files:
            return None

        for filename in files:
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()
                full_text = "".join(lines)
                tokens = re.findall(r'\w+', full_text.lower())
                if tokens:
                    corpus_tokens.append(tokens)
                    docs.append({
                        "filename": filename,
                        "content": full_text[:500],
                        "context": full_text[:800],
                        "lines": lines,
                    })
            except Exception:
                continue

        if not corpus_tokens:
            return None

        item = _IndexItem(
            index=BM25Okapi(corpus_tokens),
            docs=docs,
            timestamp=time.time(),
            dir_path=data_dir
        )
        self._indices[data_dir] = item

        elapsed = (time.perf_counter() - start) * 1000
        logger.info(f"📚 [SmartGrep] Built index for {data_dir} ({len(docs)} docs) in {elapsed:.1f}ms")
        return item

    # ── Search Strategies ────────────────────────────────────────────

    def _search_bm25(self, query: str, data_dir: str, limit: int) -> list[GrepResult]:
        """BM25 search with synonym expansion. Pure algorithm, ~10ms."""
        item = self._build_bm25_index(data_dir)
        if not item:
            return []

        expanded_tokens = _expand_with_synonyms(query)
        scores = item.index.get_scores(expanded_tokens)

        scored_docs = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in scored_docs[:limit]:
            if score <= 0.1:
                break
            doc = item.docs[idx]
            results.append(GrepResult(
                filename=doc["filename"],
                line_number=1,
                content=doc["content"][:200],
                context=doc["context"],
                score=round(float(score), 4),
                method="bm25",
            ))
        return results

    def _search_fuzzy(self, query: str, data_dir: str, limit: int) -> list[GrepResult]:
        """RapidFuzz trigram search. Handles typos, ~15ms for 100 docs."""
        item = self._build_bm25_index(data_dir)
        if not item or not item.docs:
            return []

        # Build choices: filename + first 200 chars
        choices = [f"{d['filename']} {d['content'][:200]}" for d in item.docs]

        matches = rf_process.extract(
            query, choices,
            scorer=fuzz.token_set_ratio,
            limit=limit,
            score_cutoff=40,
        )

        results = []
        for match_str, score, idx in matches:
            doc = item.docs[idx]
            results.append(GrepResult(
                filename=doc["filename"],
                line_number=1,
                content=doc["content"][:200],
                context=doc["context"],
                score=round(float(score), 2),
                method="fuzzy",
            ))
        return results

    async def _search_llm_expand(self, query: str, data_dir: str, limit: int) -> list[GrepResult]:
        """LLM-powered keyword expansion + regex scan. Slowest but highest recall."""
        try:
            llm = get_llm_service()
            # 🛰️ [PromptGov]: Fetch from registry
            raw_prompt = await prompt_service.get_prompt("smart_grep_expansion")
            if not raw_prompt:
                 # Last resort fallback if DB is empty and seeder hasn't run
                 raw_prompt = "You are a search keyword expander. Query: {query} Output:"
                 
            prompt = raw_prompt.format(query=query)
            resp = await llm.chat_complete([{"role": "user", "content": prompt}], temperature=0.1)
            keywords = [k.strip() for k in resp.replace("`", "").split(",") if k.strip()]
            if not keywords:
                keywords = re.findall(r'\w+', query)
        except Exception as e:
            logger.error(f"[SmartGrep] LLM expansion failed: {e}")
            keywords = re.findall(r'\w+', query)

        escaped = [re.escape(k) for k in keywords]
        pattern_str = "|".join(escaped)
        try:
            pattern = re.compile(pattern_str, re.IGNORECASE)
        except re.error:
            pattern = re.compile(re.escape(query), re.IGNORECASE)

        # Scan files
        results = []
        if not os.path.exists(data_dir):
            return []

        for filename in os.listdir(data_dir):
            if not filename.endswith(".md"):
                continue
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath, encoding="utf-8", errors="replace") as f:
                    text = f.read()
                hits = len(pattern.findall(text))
                if hits > 0:
                    results.append(GrepResult(
                        filename=filename,
                        line_number=1,
                        content=text[:200],
                        context=text[:800],
                        score=float(hits),
                        method="llm",
                    ))
            except Exception:
                continue

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    # ── Main Entry Point ─────────────────────────────────────────────

    async def search(
        self,
        query: str,
        limit: int = 5,
        user_id: str | None = None,
        data_dir: str | None = None,
        mode: Literal["bm25", "fuzzy", "llm", "auto"] = "auto",
    ) -> list[GrepResult]:
        """
        Multi-strategy search with User Isolation.
        
        Args:
            query: The search term.
            limit: Max results.
            user_id: If provided, use "data/memories/{user_id}/logs".
            data_dir: Manual override for directory.
            mode: Search strategy.
        """
        start_time = time.perf_counter()

        # Determine target directory
        if user_id:
            target_dir = self._get_user_logs_dir(user_id)
        else:
            target_dir = data_dir or os.path.join(self.base_data_dir, "default", "logs")

        if mode == "bm25":
            results = self._search_bm25(query, target_dir, limit)
        elif mode == "fuzzy":
            results = self._search_fuzzy(query, target_dir, limit)
        elif mode == "llm":
            results = await self._search_llm_expand(query, target_dir, limit)
        else:  # auto
            results = self._search_bm25(query, target_dir, limit)
            if len(results) < limit:
                fuzzy_results = self._search_fuzzy(query, target_dir, limit - len(results))
                seen = {r.filename for r in results}
                for fr in fuzzy_results:
                    if fr.filename not in seen:
                        results.append(fr)
                        seen.add(fr.filename)

        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(
            f"✨ [SmartGrep] user={user_id or 'anon'} mode={mode} hits={len(results)} time={elapsed:.1f}ms"
        )
        return results[:limit]



# ── Singleton ────────────────────────────────────────────────────────

_smart_grep_service = None

def get_smart_grep_service() -> SmartGrepService:
    global _smart_grep_service
    if not _smart_grep_service:
        _smart_grep_service = SmartGrepService()
    return _smart_grep_service
