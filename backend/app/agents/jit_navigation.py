"""
KB-aware Just-in-Time (JIT) Context Navigation tools.

These tools let an Agent surgically expand context around a known
document or chunk **without** re-running the full RAG pipeline. This
matches Anthropic's JIT pattern: prefer ``glob`` / ``grep`` / ``head``
on already-located resources over brute-force re-retrieval.

Surface (LangChain ``@tool`` decorated callables):
- ``kb_doc_head``         — read the first N chunks of a document
- ``kb_doc_chunk_range``  — read a window ``[start, end]`` of chunks
- ``kb_doc_grep``         — case-insensitive substring search inside
                              one document's chunks
- ``kb_list_documents``   — glob-style list of documents in a KB

All tools return compact LLM-friendly markdown and refuse to dump more
than a hard cap of characters per call.
"""

from __future__ import annotations

import re
from typing import List, Optional

from langchain_core.tools import tool
from loguru import logger
from sqlmodel import select

from app.services.semantic_id_mapper import get_semantic_id_mapper

# Hard cap on characters per tool response so a single navigation call
# cannot blow up an Agent's context window.
_MAX_RESPONSE_CHARS = 6000


def _resolve_doc_id(document_id: str) -> str:
    """Translate a semantic alias (e.g. ``doc-rfc2119-1``) to the raw UUID.

    Pass-through if the value is already a raw id (or unknown alias).
    """
    return get_semantic_id_mapper().resolve(document_id)


def _truncate(text: str, limit: int = _MAX_RESPONSE_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n…[truncated, {len(text) - limit} chars omitted]"


async def _load_chunks(
    document_id: str,
    *,
    start: Optional[int] = None,
    end: Optional[int] = None,
) -> list:
    from app.core.database import async_session_factory
    from app.models.knowledge import DocumentChunk

    async with async_session_factory() as session:
        stmt = select(DocumentChunk).where(DocumentChunk.document_id == document_id)
        if start is not None:
            stmt = stmt.where(DocumentChunk.chunk_index >= start)
        if end is not None:
            stmt = stmt.where(DocumentChunk.chunk_index <= end)
        stmt = stmt.order_by(DocumentChunk.chunk_index)
        result = await session.execute(stmt)
        return result.scalars().all()


def _format_chunks(chunks, document_id: str) -> str:
    if not chunks:
        return f"No chunks for document `{document_id}`."
    blocks = []
    for c in chunks:
        blocks.append(f"### chunk {c.chunk_index}\n{c.content.strip()}")
    return _truncate("\n\n".join(blocks))


@tool
async def kb_doc_head(document_id: str, n: int = 3) -> str:
    """Read the first ``n`` chunks of a document (default 3, max 20).

    Use this right after a RAG citation to inspect the document's
    introduction without re-running retrieval.
    """
    n = max(1, min(int(n), 20))
    document_id = _resolve_doc_id(document_id)
    try:
        chunks = await _load_chunks(document_id, start=0, end=n - 1)
        return _format_chunks(chunks, document_id)
    except Exception as e:  # noqa: BLE001
        logger.error(f"kb_doc_head failed: {e}")
        return f"Error: {e}"


@tool
async def kb_doc_chunk_range(
    document_id: str, start: int = 0, end: int = 5
) -> str:
    """Read chunks ``[start, end]`` (inclusive) of a document.

    Use this to expand context around a specific chunk you already
    cited. ``end - start`` is capped at 20.
    """
    start = max(0, int(start))
    end = max(start, int(end))
    if end - start > 20:
        end = start + 20
    document_id = _resolve_doc_id(document_id)
    try:
        chunks = await _load_chunks(document_id, start=start, end=end)
        return _format_chunks(chunks, document_id)
    except Exception as e:  # noqa: BLE001
        logger.error(f"kb_doc_chunk_range failed: {e}")
        return f"Error: {e}"


@tool
async def kb_doc_grep(
    document_id: str,
    pattern: str,
    case_sensitive: bool = False,
    context_lines: int = 1,
) -> str:
    """Substring/regex search inside one document's chunks.

    Returns matching chunk indices and the matching content blocks.
    ``pattern`` is treated as a regex; ``re.escape`` it on the caller
    side if you need a literal search.
    """
    if not pattern:
        return "Error: empty pattern."
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return f"Error: invalid regex `{pattern}`: {e}"

    document_id = _resolve_doc_id(document_id)
    try:
        chunks = await _load_chunks(document_id)
    except Exception as e:  # noqa: BLE001
        return f"Error: {e}"

    hits = []
    indexed = {c.chunk_index: c for c in chunks}
    for c in chunks:
        if regex.search(c.content or ""):
            window: List[str] = []
            for offset in range(-context_lines, context_lines + 1):
                neighbour = indexed.get(c.chunk_index + offset)
                if not neighbour:
                    continue
                marker = "→" if offset == 0 else " "
                window.append(
                    f"{marker} chunk {neighbour.chunk_index}: "
                    f"{neighbour.content.strip()[:300]}"
                )
            hits.append("\n".join(window))

    if not hits:
        return f"No match for `{pattern}` in document `{document_id}`."
    return _truncate(
        f"Found {len(hits)} matching chunk(s):\n\n" + "\n\n---\n\n".join(hits)
    )


@tool
async def kb_list_documents(kb_id: str, name_glob: str = "*", limit: int = 25) -> str:
    """List documents in a knowledge base, optionally filtered by filename glob.

    Use this to discover what is available before requesting full RAG.
    """
    import fnmatch

    from app.core.database import async_session_factory
    from app.models.knowledge import Document, KnowledgeBaseDocumentLink

    limit = max(1, min(int(limit), 100))
    try:
        async with async_session_factory() as session:
            stmt = (
                select(Document)
                .join(
                    KnowledgeBaseDocumentLink,
                    KnowledgeBaseDocumentLink.document_id == Document.id,
                )
                .where(KnowledgeBaseDocumentLink.kb_id == kb_id)
                .order_by(Document.created_at.desc())
            )
            result = await session.execute(stmt)
            docs = result.scalars().all()
    except Exception as e:  # noqa: BLE001
        return f"Error: {e}"

    matched = [
        d for d in docs if fnmatch.fnmatch(d.filename or "", name_glob)
    ][:limit]
    if not matched:
        return f"No documents in KB `{kb_id}` matching `{name_glob}`."
    mapper = get_semantic_id_mapper()
    rows = []
    for d in matched:
        alias = mapper.alias_for(str(d.id), kind="doc", hint=d.filename)
        rows.append(
            f"- `{alias}` · {d.filename} · {d.file_type} · {d.chunk_count} chunks · {d.status}"
        )
    footer = (
        "\n\n_Pass the alias (e.g. `doc-foo-1`) back to any kb_doc_* tool — "
        "it resolves to the underlying document.\n_"
    )
    return f"{len(matched)} document(s):\n" + "\n".join(rows) + footer


# Public surface — exported alongside the existing filesystem search tools.
KB_JIT_TOOLS = [kb_doc_head, kb_doc_chunk_range, kb_doc_grep, kb_list_documents]
