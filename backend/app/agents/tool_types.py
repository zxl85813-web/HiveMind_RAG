"""
HiveMind Tool Types & Metadata System.
Inspired by Claude Code's fail-closed tool architecture.
"""

from collections.abc import Callable
from enum import StrEnum
from typing import Protocol, runtime_checkable

from langchain_core.tools import BaseTool
from langchain_core.tools import tool as langchain_tool
from pydantic import BaseModel, ConfigDict, Field


class InterruptBehavior(StrEnum):
    CANCEL = "cancel"   # Stop the tool immediately on user interrupt
    BLOCK = "block"     # Complete the tool execution even if interrupted

class ToolMetadata(BaseModel):
    """
    CC-inspired metadata for safety, orchestration, and discovery.
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str = Field(description="Internal tool identifier")
    description: str = Field(description="Model-facing description of tool capability")

    # --- Safety & Side-effects (Fail-closed defaults) ---
    is_read_only: bool = Field(default=False, description="If True, tool performs no writes/mutations")
    is_concurrency_safe: bool = False  # Default to False: assume sequential execution
    is_destructive: bool = False       # If True, triggers manual confirmation in strict mode
    is_enabled: bool = True
    interrupt_behavior: InterruptBehavior = InterruptBehavior.BLOCK

    # --- Auth & Permissions (Phase 7 Guard) ---
    requires_auth: bool = False
    required_permissions: list[str] = Field(default_factory=list)

    # --- Discovery & Optimization ---
    search_hint: str = Field(default="", description="Search keywords for ToolSearch optimization")
    always_load: bool = Field(default=False, description="If True, tool skips ToolSearch and appears on turn 1")
    should_defer: bool = False         # If True, tool is hidden until explicitly searched

    # --- Output Limits ---
    max_result_size_chars: int = 50_000

@runtime_checkable
class HiveTool(Protocol):
    """Protocol for tools wrapped with HiveMind metadata."""
    _hive_meta: ToolMetadata
    __call__: Callable
    # This ensures compatibility with LangChain tools
    name: str
    description: str

def hive_tool(
    is_read_only: bool = False,
    is_concurrency_safe: bool = False,
    is_destructive: bool = False,
    interrupt_behavior: InterruptBehavior = InterruptBehavior.BLOCK,
    search_hint: str = "",
    always_load: bool = False,
    should_defer: bool = False,
    requires_auth: bool = False,
    required_permissions: list[str] = None,
):
    """
    Decorator to wrap a function as a LangChain tool with HiveMind metadata.
    Follows CC's buildTool pattern.
    """
    def decorator(func: Callable) -> BaseTool:
        if func is None:
            # Handle potential None from failed imports or circularity
            from loguru import logger
            logger.error("🚫 hive_tool received None as function target")
            raise ValueError("hive_tool cannot wrap None")

        # 1. Create the LangChain tool first
        lc_tool = langchain_tool(func)

        # 2. Build the metadata
        # Fallback to func properties if lc_tool is still being initialized
        t_name = getattr(lc_tool, "name", func.__name__)
        t_desc = getattr(lc_tool, "description", func.__doc__ or "")

        meta = ToolMetadata(
            name=t_name,
            description=t_desc,
            is_read_only=is_read_only,
            is_concurrency_safe=is_concurrency_safe,
            is_destructive=is_destructive,
            interrupt_behavior=interrupt_behavior,
            search_hint=search_hint or t_desc[:100],
            always_load=always_load,
            should_defer=should_defer,
            requires_auth=requires_auth,
            required_permissions=required_permissions or []
        )

        # 3. Attach metadata to the tool instance (Monkey-patching for LC compatibility)
        lc_tool._hive_meta = meta
        return lc_tool

    return decorator
