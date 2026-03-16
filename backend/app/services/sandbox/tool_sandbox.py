"""
Unified Tool Sandbox for Programmatic Tool Calling.
Allows executing complex logic (Python) that orchestrates other system tools.
"""

import io
import sys
import json
import math
import asyncio
from typing import Any, Dict, List, Callable
from loguru import logger
from langchain_core.tools import tool

class ToolSandbox:
    """
    A controlled environment to execute orchestration scripts.
    It provides a bridge between the generated code and the platform's tools.
    """
    
    def __init__(self, available_tools: List[Any]):
        self.tools_map = {getattr(t, "name", t.__name__): t for t in available_tools if hasattr(t, "name") or hasattr(t, "__name__")}
    
    async def call_tool(self, name: str, **kwargs) -> Any:
        """Internal bridge for the script to call other tools."""
        if name not in self.tools_map:
            raise ValueError(f"Tool '{name}' not found in sandbox.")
        
        tool_obj = self.tools_map[name]
        logger.debug(f"🛠️ [Sandbox] Orchestrating tool: {name}")
        
        # Execute tool (supporting both sync and async via LangChain's ainvoke)
        if hasattr(tool_obj, "ainvoke"):
            return await tool_obj.ainvoke(kwargs)
        else:
            # Fallback for simple functions
            return tool_obj(**kwargs)

    async def run_script(self, code: str) -> str:
        """Execute Python orchestration code."""
        stdout = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout
        
        # Define the 'platform' object available to the script
        class PlatformBridge:
            def __init__(self, sandbox: 'ToolSandbox'):
                self._sandbox = sandbox
                
            def call(self, tool_name: str, **kwargs):
                # We use a helper to run async in what might look like a sync script
                # or the script itself can use 'await platform.acall(...)'
                # For simplicity in Phase 1, we provide an async method
                return self._sandbox.call_tool(tool_name, **kwargs)

        platform = PlatformBridge(self)
        
        try:
            # Restricted execution environment
            # Note: In a real production environment, use E2B or a Docker container.
            safe_globals = {
                "platform": platform,
                "logger": logger,
                "json": json,
                "math": math,
                "asyncio": asyncio,
                "__builtins__": {
                    "print": print, "range": range, "len": len, "int": int, "float": float,
                    "str": str, "list": list, "dict": dict, "set": set, "tuple": tuple,
                    "min": min, "max": max, "sum": sum, "any": any, "all": all, "bool": bool,
                    "Exception": Exception, "ValueError": ValueError, "TypeError": TypeError
                }
            }
            
            # Since we want to support 'await', we wrap the code in an async function
            wrapped_code = "async def _run_orchestration():\n"
            for line in code.splitlines():
                wrapped_code += f"    {line}\n"
            wrapped_code += "\n_loop = asyncio.get_event_loop()\n_result = _run_orchestration()"
            
            local_scope = {}
            exec(wrapped_code, safe_globals, local_scope)
            
            # Execute the generated async function
            result_val = await local_scope["_run_orchestration"]()
            
            output = stdout.getvalue()
            sys.stdout = old_stdout
            
            summary = "✅ Orchestration completed inside sandbox."
            if output:
                summary += f"\nOutput:\n{output}"
            if result_val is not None:
                summary += f"\nFinal Result: {result_val}"
                
            return summary
            
        except Exception as e:
            sys.stdout = old_stdout
            logger.error(f"❌ Sandbox Execution Error: {e}")
            return f"Error during programmatic execution: {e!s}"

@tool
async def programmatic_execute(script: str) -> str:
    """
    Execute a complex sequence of tool calls using a Python orchestration script.
    The script has access to a `platform` object.
    Example:
        result = await platform.call("search_dev_knowledge", query="Swarm architecture")
        print(f"Found: {result}")
        return "Done"
    
    Use this for multi-step tasks to reduce latency.
    """
    # Note: Tool-to-tool calling requires access to the current available toolset.
    # In the swarm.py logic, we will need to inject the tools into the sandbox.
    # For now, this tool acts as a marker for the 'Code Agent' to use.
    return "Sandbox initialized. (Implementation handled by Swarm Node)"
