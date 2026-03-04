"""
Native tools for the Agent Swarm.
"""

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
    top_k: int = 3
) -> str:
    """
    Search the deep knowledge base (Vector Store) for specific technical details.
    Use this if the initial context provided is insufficient.
    """
    try:
        from app.services.retrieval import get_retrieval_service
        retriever = get_retrieval_service()
        docs = await retriever.retrieve(query, top_k=top_k)
        if not docs:
            return "No matching documents found in deep storage."
        
        results = []
        for d in docs:
            results.append(f"SOURCE: {d.metadata.get('source', 'Unknown')}\nCONTENT: {d.page_content}")
        return "\n\n---\n\n".join(results)
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

# Export tools
NATIVE_TOOLS = [add_collective_todo, record_reflection, search_knowledge_base, web_search]
