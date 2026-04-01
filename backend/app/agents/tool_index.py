"""
Tool Index — manages discovery and lazy-loading of HiveMind tools.
Inspired by Claude Code's ToolSearch mechanism.
"""

from typing import Any


class ToolIndex:
    """
    Central index for all available tools in the swarm.
    Provides semantic search over tool metadata.
    """

    def __init__(self, tools: list[Any]):
        self._tools = tools
        self._index = {}
        for t in tools:
            name = getattr(t, "name", str(t))
            self._index[name] = t

    def get_initial_tools(self) -> list[Any]:
        """Get tools that should appear in the initial system prompt."""
        return [
            t for t in self._tools
            if getattr(t, "_hive_meta", None) and t._hive_meta.always_load
        ]

    def search(self, query: str, limit: int = 5) -> list[Any]:
        """Semantic search over tool names, descriptions, and hints."""
        query_lower = query.lower()
        scored = []

        for name, t in self._index.items():
            meta = getattr(t, "_hive_meta", None)
            if not meta:
                continue

            text = f"{meta.name} {meta.description} {meta.search_hint}".lower()
            # Simple keyword overlap for MVP
            score = sum(1 for word in query_lower.split() if word in text)

            if score > 0:
                scored.append((score, t))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [t for s, t in scored[:limit]]

# Global singleton will be initialized in SwarmOrchestrator
_global_index: ToolIndex = None

def get_tool_index() -> ToolIndex:
    global _global_index
    return _global_index

def set_tool_index(index: ToolIndex):
    global _global_index
    _global_index = index
