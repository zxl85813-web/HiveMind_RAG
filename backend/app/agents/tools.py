"""
Native tools for the Agent Swarm.
"""

from loguru import logger

from app.agents.memory import SharedMemoryManager
from app.agents.tool_types import InterruptBehavior, hive_tool
from app.models.agents import ReflectionEntry, ReflectionSignalType, ReflectionType, TodoItem, TodoPriority

# Singleton for tools to share
_memory = SharedMemoryManager()


@hive_tool(
    is_read_only=False,
    is_concurrency_safe=False,
    search_hint="add a follow-up task to the shared todo list",
    always_load=True
)
async def add_collective_todo(
    title: str, description: str = "", priority: str = "medium", agent_name: str = "unknown"
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
            "urgent": TodoPriority.CRITICAL,
        }

        item = TodoItem(
            title=title,
            description=description,
            priority=p_map.get(priority.lower(), TodoPriority.MEDIUM),
            created_by=agent_name,
        )
        await _memory.add_todo(item)
        return f"Successfully added TODO: {title}"
    except Exception as e:
        logger.error(f"Error in add_collective_todo: {e}")
        return f"Failed to add TODO: {e!s}"


@hive_tool(
    is_read_only=False,
    is_concurrency_safe=False,
    search_hint="record an insight or correction to collective memory",
    always_load=True
)
async def record_reflection(
    content: str,
    reflection_type: str = "insight",
    agent_name: str = "unknown",
    topic: str = "",
    match_key: str = "",
) -> str:
    """
    Record an insight or self-reflection into the collective memory.
    Use this when you learn something important about the user or your own process.
    reflection_type should be one of: insight, correction, strategy, preference.
    """
    try:
        type_map = {
            "insight": ReflectionType.PERIODIC_REVIEW,
            "correction": ReflectionType.ERROR_CORRECTION,
            "strategy": ReflectionType.SELF_EVAL,
            "preference": ReflectionType.USER_INTERVENTION,
            "gap": ReflectionType.KNOWLEDGE_GAP,
            "issue": ReflectionType.ERROR_CORRECTION,
        }
        signal_map = {
            "insight": ReflectionSignalType.INSIGHT,
            "correction": ReflectionSignalType.ISSUE,
            "strategy": ReflectionSignalType.INSIGHT,
            "preference": ReflectionSignalType.INSIGHT,
            "gap": ReflectionSignalType.GAP,
            "issue": ReflectionSignalType.ISSUE,
        }

        normalized = reflection_type.lower()

        entry = ReflectionEntry(
            type=type_map.get(normalized, ReflectionType.PERIODIC_REVIEW),
            signal_type=signal_map.get(normalized, ReflectionSignalType.INSIGHT),
            agent_name=agent_name,
            topic=topic,
            match_key=match_key,
            summary=content,
            details={"raw_reflection_type": normalized},
            action_taken="recorded",
        )
        await _memory.add_reflection(entry)
        return "Reflection recorded successfully."
    except Exception as e:
        logger.error(f"Error in record_reflection: {e}")
        return f"Failed to record reflection: {e!s}"


@hive_tool(
    is_read_only=True,
    is_concurrency_safe=True,
    search_hint="search vector store for technical details",
    always_load=True
)
async def search_knowledge_base(query: str, top_k: int = 3) -> str:
    """
    Search the deep knowledge base (Vector Store) for specific technical details.
    Use this if the initial context provided is insufficient.
    """
    try:
        from app.services.retrieval import get_retrieval_service

        retriever = get_retrieval_service()
        # RetrievalPipeline returns (docs, trace_log)
        docs, _ = await retriever.run(query, collection_names=[], top_k=top_k)
        if not docs:
            return "No matching documents found in deep storage."

        results = []
        for d in docs:
            results.append(f"SOURCE: {d.metadata.get('source', 'Unknown')}\nCONTENT: {d.page_content}")
        return "\n\n---\n\n".join(results)
    except Exception as e:
        logger.error(f"Error in search_knowledge_base: {e}")
        return f"Retrieval error: {e!s}"


@hive_tool(
    is_read_only=True,
    is_concurrency_safe=True,
    search_hint="development RAG for code and docs with graph support",
    always_load=True
)
async def search_dev_knowledge(
    query: str,
    kb_ids: str = "",
    top_k: int = 5,
    include_graph: bool = True,
    strategy: str = "hybrid",
) -> str:
    """
    Development RAG retrieval for code/docs knowledge.
    kb_ids should be a comma-separated list, e.g. "kb-code,kb-docs".
    """
    try:
        from app.services.rag_gateway import RAGGateway

        parsed_kb_ids = [item.strip() for item in kb_ids.split(",") if item.strip()]
        gateway = RAGGateway()
        result = await gateway.retrieve_for_development(
            query=query,
            kb_ids=parsed_kb_ids,
            top_k=top_k,
            strategy=strategy,
            include_graph=include_graph,
        )

        if not result.fragments:
            warning_text = " | ".join(result.warnings) if result.warnings else "No evidence returned."
            return f"No development knowledge found. {warning_text}"

        lines = []
        for frag in result.fragments:
            source = frag.metadata.get("source", "vector")
            lines.append(f"[{source}] score={frag.score:.2f} kb={frag.kb_id} :: {frag.content}")

        if result.warnings:
            lines.append(f"Warnings: {' | '.join(result.warnings)}")

        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error in search_dev_knowledge: {e}")
        return f"Development retrieval error: {e!s}"


@hive_tool(
    is_read_only=True,
    is_concurrency_safe=True,
    search_hint="search the internet for real-time facts or news"
)
async def web_search(query: str) -> str:
    """
    Search the internet for real-time information or external documentation.
    Use this when you need facts or news that might not be in the internal knowledge base.
    """
    # Mock for now - in production, integrate with Tavily or Serper
    logger.info(f"🌐 Mock Web Search for: {query}")
    return (
        f"Default search result for '{query}': (Mock result) "
        "DeepSeek-V3 and GPT-4o are current state-of-the-art models as of February 2026."
    )


@hive_tool(
    is_read_only=True,
    is_concurrency_safe=True,
    search_hint="discover platform tools and skills",
    always_load=True
)
async def search_available_tools(query: str) -> str:
    """
    Search for specialized tools or skills in the platform catalog.
    Use this if NATIVE_TOOLS are insufficient for the task.
    Returns tool names and descriptions.
    """
    from app.agents.tool_index import get_tool_index

    index = get_tool_index()
    if not index:
        return "Tool indexing not yet initialized."

    logger.info(f"🔍 [ToolDiscovery] Searching for: {query}")
    results = index.search(query)

    if not results:
        return f"No specialized tools found for query: '{query}'"

    lines = ["Found relevant tools in platform catalog:"]
    for t in results:
        meta = getattr(t, "_hive_meta", None)
        desc = meta.description[:150] if meta else getattr(t, "description", "No description")
        lines.append(f"- '{t.name}': {desc}")

    return "\n".join(lines)


@hive_tool(
    is_read_only=False,
    is_concurrency_safe=False,
    interrupt_behavior=InterruptBehavior.CANCEL,
    search_hint="execute python calculations in restricted sandbox"
)
async def python_interpreter(code: str) -> str:
    """
    Execute Python code in a restricted environment.
    ⚠️ WARNING: Use this ONLY for stateless calculations or simple data processing.
    In production, this should be replaced by a secure sandbox (e.g., E2B, Modal).
    The code has access to 'logger', 'json', and 'math'.
    """
    import io
    import math
    import sys

    logger.info("🐍 [PythonExecutor] Executing code block (In-process execution)")

    # Capture stdout
    stdout = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = stdout

    try:
        # Restricted globals
        safe_globals = {
            "logger": logger,
            "json": json,
            "math": math,
            "__builtins__": {
                "print": print,
                "range": range,
                "len": len,
                "int": int,
                "float": float,
                "str": str,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "min": min,
                "max": max,
                "sum": sum,
                "abs": abs,
                "round": round,
                "enumerate": enumerate,
                "zip": zip,
                "any": any,
                "all": all,
                "bool": bool,
                "Exception": Exception,
                "ValueError": ValueError,
                "TypeError": TypeError,
                "RuntimeError": RuntimeError,
            },
        }

        # We use a clean local scope
        local_scope = {}

        # SECURITY NOTE: exec() is inherently unsafe even with restricted globals.
        # This is strictly for demonstration/MVP purposes.
        exec(code, safe_globals, local_scope)

        output = stdout.getvalue()
        sys.stdout = old_stdout

        result = "Code executed successfully."
        if output:
            result += f"\nOutput:\n{output}"
        if local_scope:
            # Filter out non-serializable or private variables
            serializable_types = int | float | str | list | dict | bool | None
            clean_locals = {
                k: v for k, v in local_scope.items() if not k.startswith("_") and isinstance(v, serializable_types)
            }
            if clean_locals:
                result += f"\nResult Variables: {json.dumps(clean_locals)}"

        return result
    except Exception as e:
        sys.stdout = old_stdout
        return f"Error executing Python: {e!s}"


@hive_tool(
    is_read_only=True,
    is_concurrency_safe=True,
    always_load=True,
    search_hint="perform explicit reasoning before acting"
)
async def think(thought: str, target_goal: str | None = None) -> str:
    """
    Perform explicit reasoning or step-by-step planning.
    Use this BEFORE calling complex tool chains to ensure your strategy is sound.
    Explain WHAT you are going to do and WHY.
    """
    logger.info(f"🧠 [Think] {thought}")
    if target_goal:
        logger.info(f"🎯 [Goal] {target_goal}")
    return "Thought recorded. You may now proceed with your planned actions."


from app.services.sandbox.tool_sandbox import programmatic_execute

# Export tools
NATIVE_TOOLS = [
    add_collective_todo,
    record_reflection,
    search_knowledge_base,
    search_dev_knowledge,
    web_search,
    think,
    search_available_tools,
    python_interpreter,
    programmatic_execute,
]
