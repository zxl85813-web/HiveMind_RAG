"""
MCP Code Mode Bridge (Anthropic 2.1I).

Why a "Code Mode" bridge?
-------------------------
Tool calls return *whatever the tool returns* — sometimes that is 1k
rows of CSV, a 50-page document dump, or a giant JSON blob. Letting
the agent reason over that raw payload in its context window is
expensive and slow. Anthropic's "Code Mode" pattern says: give the
agent a small, sandboxed Python runtime and let it filter / aggregate
the payload programmatically, returning only the answer.

This module replaces the old unsafe ``python_interpreter`` (which did
``exec(code, {"logger": logger, "json": json})`` with no caps) with:

- **AST allowlist** — rejects ``import``, ``exec``, ``eval``,
  attribute access on dunders, raw file IO, etc. The validator runs
  before execution, so unsafe code never reaches ``exec``.
- **Builtins allowlist** — only pure / non-IO builtins (``len``,
  ``range``, ``sum``, ``sorted``, ``min``, ``max``, ``map``,
  ``filter``, ``json``, ``re``, ``math``, ``statistics``, ...).
- **stdout capture** — ``print()`` output is captured and returned
  to the agent.
- **Timeout** — a wall-clock cap (default 5s) using a worker thread.
- **Optional ``data`` injection** — the caller can hand in the
  large tool payload as a Python object exposed to the snippet as
  ``data``. The agent never sees the raw payload in its context;
  only its derived answer.
- **Hard output cap** — captured stdout is truncated so a runaway
  ``print(huge_blob)`` cannot blow up the agent's window.
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import math
import re
import statistics
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------------
# Safety policy
# --------------------------------------------------------------------------
_FORBIDDEN_NODES: tuple = (
    ast.Import,
    ast.ImportFrom,
    ast.Global,
    ast.Nonlocal,
    ast.Lambda,           # closures with surprising capture
    ast.ClassDef,         # don't need user classes for data crunching
    ast.AsyncFunctionDef,
    ast.AsyncFor,
    ast.AsyncWith,
    ast.Await,
    ast.Yield,
    ast.YieldFrom,
)

_FORBIDDEN_NAMES: frozenset = frozenset({
    "exec", "eval", "compile", "open", "input", "__import__",
    "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "breakpoint", "exit", "quit",
})

# Names blocked in attribute access — block any dunder access entirely.
_DUNDER_RE = re.compile(r"^__.+__$")

_OUTPUT_CAP = 4000  # max chars of captured stdout / repr(result)
_DEFAULT_TIMEOUT_S = 5.0


def _validate(tree: ast.AST) -> Optional[str]:
    """Walk the AST and return an error string if anything looks unsafe."""
    for node in ast.walk(tree):
        if isinstance(node, _FORBIDDEN_NODES):
            return f"forbidden syntax: {type(node).__name__}"
        if isinstance(node, ast.Attribute):
            if _DUNDER_RE.match(node.attr):
                return f"dunder attribute access blocked: {node.attr}"
        if isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
            return f"forbidden name: {node.id}"
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in _FORBIDDEN_NAMES:
                return f"forbidden call: {func.id}()"
    return None


def _safe_builtins() -> Dict[str, Any]:
    """Allowlist of safe builtins exposed to the snippet."""
    import builtins as _b

    allowed = {
        "len", "range", "sum", "min", "max", "abs", "round",
        "sorted", "reversed", "enumerate", "zip", "map", "filter",
        "all", "any", "list", "dict", "set", "tuple", "str", "int",
        "float", "bool", "print", "repr", "isinstance", "type",
        "hasattr",  # safe (read-only check)
    }
    return {k: getattr(_b, k) for k in allowed if hasattr(_b, k)}


# --------------------------------------------------------------------------
# Result envelope
# --------------------------------------------------------------------------
@dataclass
class CodeRunResult:
    ok: bool
    stdout: str = ""
    value: Optional[str] = None  # repr of the last expression, if any
    error: Optional[str] = None
    elapsed_ms: float = 0.0
    truncated: bool = False

    def to_text(self) -> str:
        if not self.ok:
            return f"Error: {self.error}"
        parts = []
        if self.stdout:
            parts.append(f"--- stdout ---\n{self.stdout}")
        if self.value is not None:
            parts.append(f"--- value ---\n{self.value}")
        if self.truncated:
            parts.append("[output truncated to fit agent context]")
        if not parts:
            parts.append("(executed; no output)")
        parts.append(f"[elapsed {self.elapsed_ms:.0f}ms]")
        return "\n".join(parts)


# --------------------------------------------------------------------------
# Runner
# --------------------------------------------------------------------------
class CodeModeRunner:
    """AST-validated, sandboxed code runner with timeout + stdout capture."""

    def __init__(self, *, timeout_s: float = _DEFAULT_TIMEOUT_S):
        self.timeout_s = timeout_s

    @staticmethod
    def _async_raise(thread: threading.Thread, exc_type: type) -> None:
        """Asynchronously raise ``exc_type`` inside ``thread``.

        Uses the CPython internal ``PyThreadState_SetAsyncExc`` to break
        an otherwise unkillable runaway snippet. No-op on non-CPython.
        """
        import ctypes

        tid = thread.ident
        if tid is None:
            return
        try:
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
                ctypes.c_ulong(tid), ctypes.py_object(exc_type)
            )
            if res > 1:
                # If more than one thread was affected we must clear it.
                ctypes.pythonapi.PyThreadState_SetAsyncExc(
                    ctypes.c_ulong(tid), ctypes.c_long(0)
                )
        except Exception:  # noqa: BLE001
            # ctypes path failing is non-fatal; the timeout error is still returned.
            pass

    def run(
        self,
        code: str,
        *,
        data: Any = None,
        timeout_s: Optional[float] = None,
    ) -> CodeRunResult:
        if not code or not code.strip():
            return CodeRunResult(ok=False, error="empty code")

        # Parse & validate.
        try:
            tree = ast.parse(code, mode="exec")
        except SyntaxError as e:
            return CodeRunResult(ok=False, error=f"SyntaxError: {e.msg}")

        problem = _validate(tree)
        if problem:
            return CodeRunResult(ok=False, error=f"sandbox veto: {problem}")

        # Split off the trailing expression so we can return its value
        # the way a REPL would, without forcing the agent to print().
        last_expr_value_holder: List[Any] = []
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            last_expr = tree.body.pop()
            assign = ast.Assign(
                targets=[ast.Name(id="__last_expr_value__", ctx=ast.Store())],
                value=last_expr.value,
            )
            ast.copy_location(assign, last_expr)
            tree.body.append(assign)
            ast.fix_missing_locations(tree)

        safe_globals: Dict[str, Any] = {
            "__builtins__": _safe_builtins(),
            "json": json,
            "re": re,
            "math": math,
            "statistics": statistics,
            "data": data,
        }
        safe_locals: Dict[str, Any] = {}

        captured = io.StringIO()
        result_holder: Dict[str, Any] = {}

        def _runner() -> None:
            try:
                with contextlib.redirect_stdout(captured):
                    exec(compile(tree, "<code-mode>", "exec"), safe_globals, safe_locals)
                result_holder["ok"] = True
            except Exception as e:  # noqa: BLE001
                result_holder["ok"] = False
                result_holder["error"] = f"{type(e).__name__}: {e}"

        import time

        start = time.time()
        thread = threading.Thread(target=_runner, daemon=True)
        thread.start()
        thread.join(timeout_s if timeout_s is not None else self.timeout_s)
        elapsed_ms = (time.time() - start) * 1000

        if thread.is_alive():
            # Pure Python can't kill threads, but ctypes can asynchronously
            # raise an exception inside one. We use SystemExit so the
            # interpreter unwinds cleanly. Without this, a tight loop like
            # ``while True: pass`` would hold the GIL forever and DOS the
            # whole process.
            self._async_raise(thread, SystemExit)
            # Give the interpreter a beat to actually unwind.
            thread.join(1.0)
            return CodeRunResult(
                ok=False,
                error=f"timeout after {timeout_s or self.timeout_s:g}s",
                elapsed_ms=elapsed_ms,
            )

        ok = bool(result_holder.get("ok"))
        if not ok:
            return CodeRunResult(
                ok=False,
                error=result_holder.get("error", "unknown error"),
                elapsed_ms=elapsed_ms,
                stdout=captured.getvalue()[:_OUTPUT_CAP],
            )

        stdout = captured.getvalue()
        truncated = len(stdout) > _OUTPUT_CAP
        if truncated:
            stdout = stdout[:_OUTPUT_CAP]

        value_obj = safe_locals.get("__last_expr_value__")
        value_repr = None
        if value_obj is not None:
            try:
                value_repr = repr(value_obj)
            except Exception:  # noqa: BLE001
                value_repr = "<unrepresentable value>"
            if len(value_repr) > _OUTPUT_CAP:
                value_repr = value_repr[:_OUTPUT_CAP]
                truncated = True

        return CodeRunResult(
            ok=True,
            stdout=stdout,
            value=value_repr,
            elapsed_ms=elapsed_ms,
            truncated=truncated,
        )


# --------------------------------------------------------------------------
# Singleton
# --------------------------------------------------------------------------
_runner: Optional[CodeModeRunner] = None


def get_code_mode_runner() -> CodeModeRunner:
    global _runner
    if _runner is None:
        _runner = CodeModeRunner()
    return _runner
