"""
Contextual BM25 + RRF fusion step.

Why this exists
---------------
Pure dense retrieval misses exact-keyword and ID-style hits ("RFC-2119",
"GAAP", error codes, function names) — embeddings smear them into nearby
neighbours. Anthropic's "Contextual Retrieval" recipe pairs dense vectors
with BM25 over the *same* recall pool, then fuses the two rankings.

This step:

1. Runs cheaply over ``ctx.candidates`` already produced by
   ``HybridRetrievalStep`` (no extra IO — BM25 is in-memory).
2. Tokenises each candidate's ``page_content`` plus any optional
   ``metadata['contextual_summary']`` (leaves room for ingestion-side
   contextual prefixes — the "contextual" half of Contextual BM25).
3. Scores against the user's keywords + rewritten query.
4. Fuses the dense rank with the BM25 ranking. We use **weighted
   normalized score fusion** rather than vanilla RRF: with the small
   recall pools we typically operate on (5–150 docs) RRF can't tell a
   strong unique sparse hit from a tied tail, so a single exact-keyword
   match (e.g. "RFC-2119") never overtakes the dense top. Linear
   normalization with a sparse weight > dense weight keeps that signal.
5. Reorders ``ctx.candidates`` and stamps per-doc scores into metadata
   so the reranker / trace can inspect them.

The implementation is a small Okapi-BM25 (k1=1.5, b=0.75) so we don't
take on a new dependency. Tokeniser splits on word boundaries and emits
character bigrams for CJK text so Chinese queries get *some* lexical
signal even without jieba.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Iterable, List, Sequence

from app.core.vector_store import VectorDocument
from .protocol import RetrievalContext
from .steps import BaseRetrievalStep


_WORD_RE = re.compile(r"[A-Za-z0-9_]+", re.UNICODE)
_CJK_RE = re.compile(r"[\u3400-\u9fff]")

# Reasonable defaults from Robertson et al.
BM25_K1 = 1.5
BM25_B = 0.75

# Score-fusion weights. Sparse gets a slight edge so a clean exact-keyword
# hit (the whole reason we run BM25) can overtake a tepid dense neighbour.
DENSE_WEIGHT = 0.4
SPARSE_WEIGHT = 0.6


def _tokenize(text: str) -> List[str]:
    """Word tokens + CJK bigrams, lowercased."""
    if not text:
        return []
    text = text.lower()
    tokens: List[str] = _WORD_RE.findall(text)
    cjk_chars = _CJK_RE.findall(text)
    if len(cjk_chars) >= 2:
        tokens.extend(
            cjk_chars[i] + cjk_chars[i + 1] for i in range(len(cjk_chars) - 1)
        )
    elif cjk_chars:
        tokens.extend(cjk_chars)
    return tokens


def _doc_text(doc: VectorDocument) -> str:
    """Join page_content with any ingestion-side contextual prefix."""
    summary = ""
    if doc.metadata:
        summary = (
            doc.metadata.get("contextual_summary")
            or doc.metadata.get("context_prefix")
            or ""
        )
    return (summary + "\n" + doc.page_content) if summary else doc.page_content


class _BM25Index:
    """Minimal Okapi BM25 over a fixed candidate list."""

    def __init__(self, docs_tokens: Sequence[List[str]]):
        self.N = len(docs_tokens)
        self.doc_len = [len(t) for t in docs_tokens]
        self.avgdl = (sum(self.doc_len) / self.N) if self.N else 0.0
        self.tfs: List[Counter] = [Counter(t) for t in docs_tokens]

        df: Counter = Counter()
        for tf in self.tfs:
            df.update(tf.keys())
        self.idf = {
            term: math.log(1 + (self.N - n + 0.5) / (n + 0.5))
            for term, n in df.items()
        }

    def score(self, query_tokens: Iterable[str]) -> List[float]:
        scores = [0.0] * self.N
        if self.N == 0 or self.avgdl == 0:
            return scores
        # Dedup query tokens; idf weighting handles repetition.
        unique_q = set(query_tokens)
        for term in unique_q:
            idf = self.idf.get(term)
            if idf is None:
                continue
            for i, tf in enumerate(self.tfs):
                f = tf.get(term)
                if not f:
                    continue
                dl = self.doc_len[i]
                denom = f + BM25_K1 * (1 - BM25_B + BM25_B * dl / self.avgdl)
                scores[i] += idf * (f * (BM25_K1 + 1) / denom)
        return scores


def _rrf(rank_lists: Iterable[List[int]], n: int, k: int = 60) -> List[float]:
    """Reciprocal Rank Fusion (kept available for callers that want it)."""
    fused = [0.0] * n
    for ranking in rank_lists:
        for rank, idx in enumerate(ranking):
            fused[idx] += 1.0 / (k + rank + 1)
    return fused


class ContextualBM25Step(BaseRetrievalStep):
    """Sparse-augmented re-ordering of the dense recall pool.

    Runs *after* ``HybridRetrievalStep`` and *before* ``RerankingStep``:
    we don't replace either, we just give the cross-encoder a better
    pool and a fairer ranking to start from.
    """

    def __init__(
        self,
        *,
        dense_weight: float = DENSE_WEIGHT,
        sparse_weight: float = SPARSE_WEIGHT,
    ):
        self.dense_weight = dense_weight
        self.sparse_weight = sparse_weight

    async def execute(self, ctx: RetrievalContext):
        candidates = ctx.candidates
        n = len(candidates)
        if n < 2:
            ctx.log("BM25", f"skip — only {n} candidate(s)")
            return

        # Build the query: rewritten + original + extracted keywords.
        query_parts: List[str] = []
        if ctx.rewritten_query:
            query_parts.append(ctx.rewritten_query)
        query_parts.append(ctx.query)
        if ctx.keywords:
            query_parts.append(" ".join(ctx.keywords))
        q_tokens = _tokenize(" ".join(query_parts))
        if not q_tokens:
            ctx.log("BM25", "skip — empty query tokens")
            return

        docs_tokens = [_tokenize(_doc_text(d)) for d in candidates]
        index = _BM25Index(docs_tokens)
        sparse_scores = index.score(q_tokens)

        # Normalise scores into [0, 1].
        max_sparse = max(sparse_scores) or 1.0
        sparse_norm = [s / max_sparse for s in sparse_scores]
        # Dense "score" derived from the recall order (no raw scores survive
        # the dedup in HybridRetrievalStep). Linear in [0, 1].
        dense_norm = [(n - i) / n for i in range(n)]

        fused = [
            self.dense_weight * dn + self.sparse_weight * sn
            for dn, sn in zip(dense_norm, sparse_norm)
        ]

        for doc, s, f in zip(candidates, sparse_scores, fused):
            doc.metadata["sparse_score"] = round(s, 4)
            doc.metadata["sparse_score_norm"] = round(s / max_sparse, 4)
            doc.metadata["fusion_score"] = round(f, 6)

        order = sorted(range(n), key=lambda i: fused[i], reverse=True)
        ctx.candidates = [candidates[i] for i in order]

        nonzero = sum(1 for s in sparse_scores if s > 0)
        sparse_top_idx = max(range(n), key=lambda i: sparse_scores[i])
        ctx.log(
            "BM25",
            f"sparse_hits={nonzero}/{n} "
            f"top_sparse={sparse_scores[sparse_top_idx]:.3f} "
            f"fusion=weighted(dense={self.dense_weight},sparse={self.sparse_weight}) "
            f"reordered=true",
        )
