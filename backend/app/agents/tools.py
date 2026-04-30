"""
Native tools for the Agent Swarm.
"""

import json
from typing import Any, Optional
from langchain_core.tools import tool
from loguru import logger

from app.agents.memory import SharedMemoryManager
from app.models.agents import TodoItem, TodoPriority, ReflectionEntry, ReflectionType

# Singleton for tools to share
_memory = SharedMemoryManager()

@tool
async def add_collective_todo(
    title: str,
    description: str = "",
    priority: str = "medium",
    agent_name: str = "unknown"
) -> str:
    """
    Add a task to the swarm's collective TODO list.
    Use this when you identify a follow-up task that needs to be tracked.
    Priority should be one of: low, medium, high, urgent.
    """
    try:
        # Map priority string to enum
        p_map = {
            "low": TodoPriority.LOW,
            "medium": TodoPriority.MEDIUM,
            "high": TodoPriority.HIGH,
            "urgent": TodoPriority.URGENT
        }
        
        item = TodoItem(
            title=title,
            description=description,
            priority=p_map.get(priority.lower(), TodoPriority.MEDIUM),
            created_by=agent_name
        )
        await _memory.add_todo(item)
        return f"Successfully added TODO: {title}"
    except Exception as e:
        logger.error(f"Error in add_collective_todo: {e}")
        return f"Failed to add TODO: {str(e)}"

@tool
async def record_reflection(
    content: str,
    reflection_type: str = "insight",
    agent_name: str = "unknown"
) -> str:
    """
    Record an insight or self-reflection into the collective memory.
    Use this when you learn something important about the user or your own process.
    reflection_type should be one of: insight, correction, strategy, preference.
    """
    try:
        t_map = {
            "insight": ReflectionType.INSIGHT,
            "correction": ReflectionType.CORRECTION,
            "strategy": ReflectionType.STRATEGY,
            "preference": ReflectionType.PREFERENCE
        }
        
        entry = ReflectionEntry(
            content=content,
            type=t_map.get(reflection_type.lower(), ReflectionType.INSIGHT),
            agent_name=agent_name
        )
        await _memory.add_reflection(entry)
        return "Reflection recorded successfully."
    except Exception as e:
        logger.error(f"Error in record_reflection: {e}")
        return f"Failed to record reflection: {str(e)}"

@tool
async def search_knowledge_base(
    query: str,
    top_k: int = 3,
    kb_ids: Optional[list[str]] = None,
) -> str:
    """Search the unified knowledge gateway for relevant chunks.

    Args:
        query: Natural-language question.
        top_k: How many top fragments to return (1-10).
        kb_ids: Optional explicit knowledge base ids; omit to search all.

    Returns a markdown block where every chunk is prefixed with a
    ``[^citation_id]`` tag. The same ids are listed in a "Sources"
    section at the bottom so the LLM can produce citation-aware answers
    without inventing references.
    """
    try:
        from app.services.rag_gateway import get_rag_gateway

        gateway = get_rag_gateway()
        # If no explicit kb_ids, treat as "search all collections" — the
        # gateway tolerates an empty list by returning a clear warning.
        target_kbs = kb_ids or []
        if not target_kbs:
            try:
                from app.services.retrieval.routing import KnowledgeBaseSelector
                selected = await KnowledgeBaseSelector().select_kbs(query)
                # Note: selector returns DB KB objects; their `vector_collection`
                # is what the pipeline actually queries.
                target_kbs = [
                    kb.vector_collection
                    for kb in selected
                    if getattr(kb, "vector_collection", None)
                ]
            except Exception as routing_err:  # noqa: BLE001
                logger.warning(f"KB routing fallback: {routing_err}")
                target_kbs = []

        response = await gateway.retrieve(
            query=query,
            kb_ids=target_kbs,
            top_k=max(1, min(top_k, 10)),
            strategy="hybrid",
        )

        if not response.fragments:
            note = "; ".join(response.warnings) if response.warnings else ""
            return f"No matching documents found in deep storage. {note}".strip()

        body = response.to_prompt_context(max_chars=4000)
        sources = "\n".join(
            f"- [^{c.citation_id}] {c.document_title or c.source_id}"
            + (f" (p.{c.page})" if c.page else "")
            for c in response.top_sources(limit=top_k)
        )
        confidence_pct = round(response.confidence * 100)
        return (
            f"{body}\n\n--- Sources (confidence ~{confidence_pct}%) ---\n{sources}"
        )
    except Exception as e:
        logger.error(f"Error in search_knowledge_base: {e}")
        return f"Retrieval error: {str(e)}"

@tool
async def web_search(
    query: str
) -> str:
    """
    Search the internet for real-time information or external documentation.
    Use this when you need facts or news that might not be in the internal knowledge base.
    """
    # Mock for now - in production, integrate with Tavily or Serper
    logger.info(f"🌐 Mock Web Search for: {query}")
    return f"Default search result for '{query}': (Mock result) DeepSeek-V3 and GPT-4o are current state-of-the-art models as of February 2026."

@tool
async def search_available_tools(query: str) -> str:
    """Search the SkillRegistry catalogue for tools matching ``query``.

    This is the Tier 1 step of progressive disclosure: returns only
    name + summary + tags, so the Agent can decide whether to drill in
    via ``inspect_skill``.
    """
    try:
        from app.skills.registry import get_skill_registry

        registry = get_skill_registry()
        if not registry.list_skills():
            await registry.load_all()
        rows = registry.catalog(query=query, limit=8)
        if not rows:
            return f"No skills match '{query}'."
        lines = []
        for r in rows:
            tags = f" #{' #'.join(r['tags'])}" if r.get("tags") else ""
            lines.append(
                f"- **{r['name']}** (v{r['version']}, {r['tool_count']} tools){tags}\n"
                f"  {r['summary']}"
            )
        return "Found candidate skills:\n" + "\n".join(lines)
    except Exception as e:  # noqa: BLE001
        logger.error(f"search_available_tools failed: {e}")
        return f"Skill catalog error: {e}"


@tool
async def inspect_skill(name: str) -> str:
    """Tier 2 progressive disclosure: read the full SKILL.md + tool list.

    Call this only after ``search_available_tools`` identifies a
    candidate. Returns markdown documentation describing how to invoke
    each tool the skill ships.
    """
    try:
        from app.skills.registry import get_skill_registry

        registry = get_skill_registry()
        if not registry.list_skills():
            await registry.load_all()
        detail = registry.inspect(name)
        if not detail:
            return f"Skill `{name}` not found."
        tools_md = "\n".join(
            f"- `{t['name']}` — {t.get('description', '')}" for t in detail["tools"]
        ) or "(no tools)"
        body = (detail.get("details") or "").strip()
        if len(body) > 4000:
            body = body[:4000] + "\n…[truncated]"
        return (
            f"# {detail['name']} (v{detail['version']})\n"
            f"{detail['summary']}\n\n"
            f"## Tools\n{tools_md}\n\n"
            f"## Documentation\n{body}"
        )
    except Exception as e:  # noqa: BLE001
        logger.error(f"inspect_skill failed: {e}")
        return f"Inspect error: {e}"

@tool
async def python_interpreter(
    code: str,
    timeout_seconds: float = 5.0,
) -> str:
    """Execute Python in a sandboxed runtime — Anthropic Code Mode.

    Use this to filter / aggregate large tool returns (CSV rows, JSON
    arrays, search hits) **without** dragging the raw payload through
    your context window. The runtime:

    - allows `json`, `re`, `math`, `statistics` and pure builtins;
    - blocks `import`, `open`, `eval`, `exec`, file IO and dunder
      access (validated via AST before running);
    - captures `print()` output and the value of the trailing
      expression (REPL-style);
    - enforces a wall-clock timeout (default 5s, max 30s).

    Returns a brief markdown report with stdout, the trailing value,
    and elapsed time.
    """
    from app.services.sandbox import get_code_mode_runner

    timeout = max(0.5, min(float(timeout_seconds), 30.0))
    logger.info(f"🐍 [CodeMode] Running snippet (timeout={timeout:g}s)...")
    result = get_code_mode_runner().run(code, timeout_s=timeout)
    if not result.ok:
        logger.warning(f"🐍 [CodeMode] {result.error}")
    return result.to_text()

@tool
async def think(
    thought: str,
    target_goal: Optional[str] = None
) -> str:
    """
    Perform explicit reasoning or step-by-step planning.
    Use this BEFORE calling complex tool chains to ensure your strategy is sound.
    Explain WHAT you are going to do and WHY.
    """
    logger.info(f"🧠 [Think] {thought}")
    if target_goal:
        logger.info(f"🎯 [Goal] {target_goal}")
    return "Thought recorded. You may now proceed with your planned actions."

# Export tools
from app.agents.jit_navigation import KB_JIT_TOOLS
from app.agents.search_subagents import spawn_search_subagents

NATIVE_TOOLS = [
    add_collective_todo,
    record_reflection,
    search_knowledge_base,
    web_search,
    think,
    search_available_tools,
    inspect_skill,
    python_interpreter,
    spawn_search_subagents,
    *KB_JIT_TOOLS,
]
