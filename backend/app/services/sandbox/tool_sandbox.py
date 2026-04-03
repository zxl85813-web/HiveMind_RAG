import io
import sys
from typing import Any

from loguru import logger

from app.agents.tool_types import InterruptBehavior, hive_tool
from app.services.sandbox.safe_environment import SafeEnvironment


class ToolSandbox:
    """
    A controlled environment to execute orchestration scripts.
    It provides a bridge between the generated code and the platform's tools.
    """

    def __init__(self, available_tools: list[Any]):
        self.tools_map = {getattr(t, "name", t.__name__): t for t in available_tools if hasattr(t, "name") or hasattr(t, "__name__")}
        
        # Inject standard platform bridge
        class PlatformBridge:
            def __init__(self, sandbox: 'ToolSandbox'):
                self._sandbox = sandbox

            async def call(self, tool_name: str, **kwargs):
                return await self._sandbox.call_tool(tool_name, **kwargs)

        self.bridge = PlatformBridge(self)
        self.env = SafeEnvironment(platform_bridge=self.bridge)

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
        """Execute Python orchestration code inside SafeEnvironment."""
        stdout = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout

        try:
            # Restricted execution via SafeEnvironment (P0 Hardening)
            result_val = await self.env.execute(code, timeout=5.0)

            output = stdout.getvalue()
            sys.stdout = old_stdout

            if isinstance(result_val, str) and result_val.startswith("Error"):
                summary = f"❌ {result_val}"
            else:
                summary = "✅ Orchestration completed inside SAFE sandbox."
            
            if output:
                summary += f"\nOutput:\n{output}"
            if result_val is not None and not (isinstance(result_val, str) and result_val.startswith("Error")):
                summary += f"\nFinal Result: {result_val}"

            return summary

        except Exception as e:
            sys.stdout = old_stdout
            logger.error(f"❌ Sandbox Wrapper Error: {e}")
            return f"Error during sandbox orchestration: {e!s}"

@hive_tool(
    is_read_only=False,
    is_concurrency_safe=False,
    is_destructive=True,
    interrupt_behavior=InterruptBehavior.CANCEL,
    search_hint="execute a complex sequence of tool calls using a Python orchestration script"
)
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
