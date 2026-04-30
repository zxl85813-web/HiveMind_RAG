"""
Search Subagents — Anthropic-style fan-out / fan-in for knowledge research.

Why a separate module?
- A subagent is an *isolated* worker: its own context window, its own
  short tool loop, no access to the parent's conversational history.
  This keeps the parent agent's context clean and lets us run several
  branches in parallel without cross-contamination.
- The output protocol (``SubagentReport``) is intentionally compact so
  the parent agent can absorb several reports without blowing up its
  own token budget.

Public surface:
- ``SubagentSpec`` / ``SubagentReport`` — pydantic contracts.
- ``run_search_subagents(specs, ...)`` — driver that fans out via
  ``asyncio.gather`` and aggregates structured findings.
- ``spawn_search_subagents`` — LangChain ``@tool`` exposing the driver
  to the Supervisor.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from loguru import logger
from pydantic import BaseModel, Field

from app.schemas.knowledge_protocol import Citation


# --- Hard limits to keep fan-out predictable ------------------------------
MAX_SUBAGENTS = 6
DEFAULT_TURNS = 3
DEFAULT_TIMEOUT_S = 45.0


class SubagentSpec(BaseModel):
    """One unit of research work to dispatch."""

    name: str = Field(..., description="Short label so the parent can join reports back.")
    query: str = Field(..., description="The standalone sub-question to investigate.")
    kb_ids: Optional[List[str]] = Field(
        None,
        description="Optional KB scope. If omitted, gateway auto-routes.",
    )
    max_tools_per_turn: int = Field(default=2, ge=1, le=5)


class SubagentReport(BaseModel):
    """Compact structured finding returned by a subagent."""

    name: str
    query: str
    findings: str
    citations: List[Citation] = Field(default_factory=list)
    tool_calls: int = 0
    elapsed_ms: float = 0.0
    confidence: float = 0.0
    error: Optional[str] = None

    def to_markdown(self) -> str:
        head = f"### Subagent `{self.name}` — {self.query}"
        if self.error:
            return f"{head}\n_Error_: {self.error}"
        cites = (
            "\n\nSources:\n"
            + "\n".join(
                f"- [^{c.citation_id}] {c.document_title or c.source_id}"
                for c in self.citations
            )
            if self.citations
            else ""
        )
        return (
            f"{head}\n_confidence={self.confidence:.2f}, "
            f"tools={self.tool_calls}, {self.elapsed_ms:.0f}ms_\n\n"
            f"{self.findings.strip()}{cites}"
        )


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------
async def _run_one_subagent(
    spec: SubagentSpec,
    *,
    timeout_s: float,
    turns: int,
) -> SubagentReport:
    """Drive a single subagent — short tool loop, isolated context.

    The subagent's only job is to interrogate the knowledge gateway (and
    optional KB-JIT helpers), then return a focused finding. We do *not*
    re-use the SwarmOrchestrator graph here on purpose: that graph is a
    multi-agent supervisor with reflection cycles, which would be huge
    overkill (and slow) for a leaf research task.
    """
    start = time.time()

    try:
        # Lazy imports keep the module light to import.
        from app.agents.llm_router import LLMRouter, ModelTier
        from app.agents.tools import search_knowledge_base
        from app.agents.jit_navigation import (
            kb_doc_chunk_range,
            kb_doc_grep,
            kb_doc_head,
            kb_list_documents,
        )
        from app.services.rag_gateway import get_rag_gateway

        gateway = get_rag_gateway()

        # 1. Always start with one structured retrieval call so we can
        #    return real citations even if the LLM loop fails or times out.
        baseline = await gateway.retrieve(
            query=spec.query,
            kb_ids=spec.kb_ids or [],
            top_k=4,
            strategy="hybrid",
        )

        tool_calls = 1
        findings_parts: List[str] = []
        if baseline.fragments:
            findings_parts.append(baseline.to_prompt_context(max_chars=2400))

        # 2. Light LLM loop — synthesise a focused answer over the baseline
        #    plus optional follow-up tool calls. Failure is non-fatal: the
        #    baseline retrieval already gives us something to return.
        synth = ""
        try:
            router = LLMRouter()
            llm = router.get_model(ModelTier.FAST)
            llm_with_tools = llm.bind_tools(
                [
                    search_knowledge_base,
                    kb_doc_head,
                    kb_doc_chunk_range,
                    kb_doc_grep,
                    kb_list_documents,
                ]
            )

            messages: list = [
                SystemMessage(
                    content=(
                        "You are a focused research subagent. You have an "
                        "ISOLATED context. Investigate the question using "
                        "the provided baseline context and at most "
                        f"{turns} additional tool calls. Return a tight, "
                        "self-contained answer (<= 250 words) that cites "
                        "facts as `[^citation_id]` so the parent agent "
                        "can re-use them verbatim."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Question: {spec.query}\n\n"
                        f"Baseline context (top fragments with citation tags):\n"
                        f"{baseline.to_prompt_context(max_chars=2400) or '(empty)'}"
                    )
                ),
            ]

            for _ in range(turns):
                resp = await llm_with_tools.ainvoke(messages)
                messages.append(resp)
                tool_invocations = getattr(resp, "tool_calls", []) or []
                if not tool_invocations:
                    synth = str(getattr(resp, "content", "") or "")
                    break
                # Cap fan-out per turn.
                for call in tool_invocations[: spec.max_tools_per_turn]:
                    tool_calls += 1
                    fn_name = call.get("name") if isinstance(call, dict) else getattr(
                        call, "name", None
                    )
                    args = call.get("args", {}) if isinstance(call, dict) else (
                        getattr(call, "args", {}) or {}
                    )
                    tool_fn = {
                        "search_knowledge_base": search_knowledge_base,
                        "kb_doc_head": kb_doc_head,
                        "kb_doc_chunk_range": kb_doc_chunk_range,
                        "kb_doc_grep": kb_doc_grep,
                        "kb_list_documents": kb_list_documents,
                    }.get(fn_name or "")
                    if not tool_fn:
                        continue
                    try:
                        out = await tool_fn.ainvoke(args)
                    except Exception as te:  # noqa: BLE001
                        out = f"Tool error: {te}"
                    from langchain_core.messages import ToolMessage

                    messages.append(
                        ToolMessage(
                            content=str(out)[:4000],
                            tool_call_id=(
                                call.get("id") if isinstance(call, dict)
                                else getattr(call, "id", "")
                            ) or fn_name or "tool",
                        )
                    )
        except Exception as llm_err:  # noqa: BLE001
            logger.warning(
                f"Subagent '{spec.name}' LLM loop failed, returning baseline only: {llm_err}"
            )
            synth = ""

        if synth:
            findings_parts.insert(0, synth)
        elif not findings_parts:
            findings_parts.append("(no findings)")

        return SubagentReport(
            name=spec.name,
            query=spec.query,
            findings="\n\n".join(findings_parts),
            citations=baseline.citations,
            tool_calls=tool_calls,
            elapsed_ms=(time.time() - start) * 1000,
            confidence=baseline.confidence,
        )
    except Exception as e:  # noqa: BLE001
        logger.exception(f"Subagent '{spec.name}' crashed: {e}")
        return SubagentReport(
            name=spec.name,
            query=spec.query,
            findings="",
            elapsed_ms=(time.time() - start) * 1000,
            error=str(e),
        )


async def run_search_subagents(
    specs: List[SubagentSpec],
    *,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    turns: int = DEFAULT_TURNS,
) -> List[SubagentReport]:
    """Fan out subagents in parallel and return their reports."""
    if not specs:
        return []
    if len(specs) > MAX_SUBAGENTS:
        logger.warning(
            f"Capping subagent fan-out from {len(specs)} to {MAX_SUBAGENTS}."
        )
        specs = specs[:MAX_SUBAGENTS]

    tasks = [
        asyncio.wait_for(
            _run_one_subagent(s, timeout_s=timeout_s, turns=turns),
            timeout=timeout_s,
        )
        for s in specs
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    reports: List[SubagentReport] = []
    for spec, res in zip(specs, results):
        if isinstance(res, Exception):
            reports.append(
                SubagentReport(
                    name=spec.name,
                    query=spec.query,
                    findings="",
                    error=f"{type(res).__name__}: {res}",
                )
            )
        else:
            reports.append(res)
    return reports


# --------------------------------------------------------------------------
# LangChain tool surface
# --------------------------------------------------------------------------
@tool
async def spawn_search_subagents(
    subqueries: List[str],
    kb_ids: Optional[List[str]] = None,
    turns: int = DEFAULT_TURNS,
) -> str:
    """Fan out parallel research subagents on independent sub-questions.

    Use this when a user request decomposes into 2-6 independent research
    threads (e.g. "compare A, B and C" or "summarise the design,
    implementation and risks"). Each subagent runs in its own isolated
    context so it can dig deep without polluting the parent agent.

    Args:
        subqueries: 2-6 standalone sub-questions to investigate.
        kb_ids: Optional shared KB scope; omit to let each subagent
            auto-route through the gateway.
        turns: Max tool turns per subagent (default 3, hard cap 5).

    Returns a markdown brief aggregating each subagent's findings with
    citation tags ready to be reused by the parent agent.
    """
    if not subqueries:
        return "No subqueries given."
    turns = max(1, min(int(turns), 5))
    specs = [
        SubagentSpec(
            name=f"sub{i + 1}",
            query=q.strip(),
            kb_ids=kb_ids,
        )
        for i, q in enumerate(subqueries)
        if q and q.strip()
    ]
    reports = await run_search_subagents(specs, turns=turns)
    successful = sum(1 for r in reports if not r.error)
    body = "\n\n---\n\n".join(r.to_markdown() for r in reports)
    header = (
        f"# Parallel Research Brief — {successful}/{len(reports)} subagents succeeded\n"
    )
    return header + body
