"""
Safe Execution Environment using RestrictedPython.
Provides a hardened sub-environment for agent-generated orchestration scripts.
"""

import asyncio
import json
import math
import sys
from typing import Any, Dict

from loguru import logger
from RestrictedPython import compile_restricted, safe_globals
from RestrictedPython.Eval import default_guarded_getitem, default_guarded_getiter
from RestrictedPython.Guards import guarded_iter_unpack_sequence, safe_builtins

from app.core.config import settings


def guarded_getattr(obj: Any, name: str) -> Any:
    """Restricts access to sensitive attributes (e.g., __class__, __subclasses__)."""
    if name.startswith("_"):
        raise AttributeError(f"Denied access to private attribute: {name}")
    return getattr(obj, name)


class SafeEnvironment:
    """
    A wrapper around RestrictedPython that provides a safe global execution scope.
    Included builtins and modules are strictly whitelisted.
    """

    def __init__(self, platform_bridge: Any = None):
        self.platform_bridge = platform_bridge
        self.globals = self._create_globals()

    def _create_globals(self) -> Dict[str, Any]:
        """Initialize the global execution scope with whitelisted modules and builtins."""
        # 1. Start with safe defaults from RestrictedPython
        my_globals = safe_globals.copy()

        # 2. Add safe builtins (print, range, len, int, str, etc.)
        my_globals["__builtins__"] = safe_builtins.copy()
        
        # 3. Add necessary bridges and modules
        my_globals["platform"] = self.platform_bridge
        my_globals["json"] = json
        my_globals["math"] = math
        my_globals["asyncio"] = asyncio
        my_globals["logger"] = logger

        # 4. Mandatory RestrictedPython guards
        my_globals["_getattr_"] = guarded_getattr
        my_globals["_getitem_"] = default_guarded_getitem
        my_globals["_getiter_"] = default_guarded_getiter
        my_globals["_iter_unpack_sequence_"] = guarded_iter_unpack_sequence

        return my_globals

    async def execute(self, code: str, timeout: float | None = None) -> Any:
        """
        Compiles and executes the provided Python code in the safe environment.
        Supports async orchestration scripts.
        """
        timeout = timeout or settings.SANDBOX_TIMEOUT_SEC
        old_recursion = sys.getrecursionlimit()
        try:
            # Set recursion limit (P0 Hardening)
            sys.setrecursionlimit(settings.SANDBOX_MAX_RECURSION)
            
            # Step 1: Restricted compilation
            # We wrap the code in a function to support 'await' syntax if needed
            indented_code = "\n".join([f"    {line}" for line in code.splitlines()])
            wrapped_code = f"async def _run_script():\n{indented_code}\n"
            
            byte_code = compile_restricted(wrapped_code, filename="<agent_script>", mode="exec")
            
            # Step 2: Execution in safe scope
            local_scope: Dict[str, Any] = {}
            exec(byte_code, self.globals, local_scope)
            
            run_func = local_scope.get("_run_script")
            if not run_func:
                return "Error: Script did not define a runnable execution path."

            # Step 3: Run with timeout
            logger.info("🛡️ [Sandbox] Starting restricted execution...")
            result = await asyncio.wait_for(run_func(), timeout=timeout)
            
            return result

        except asyncio.TimeoutError:
            logger.error("❌ [Sandbox] Execution timed out after {}s", timeout)
            return f"Error: Script execution exceeded the timeout of {timeout}s."
        except Exception as e:
            logger.error("❌ [Sandbox] Execution failed: {}", str(e))
            return f"Error inside Sandbox: {str(e)}"
        finally:
            # Restore system recursion limit
            sys.setrecursionlimit(old_recursion)
