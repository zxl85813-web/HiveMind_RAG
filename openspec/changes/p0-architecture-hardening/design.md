# Design: P0 Architecture Hardening

> **Status**: Draft  
> **Author**: Antigravity  
> **Milestone**: M7.3 (Architecture Resilience)

## 1. Concept

This change implements two core "Harness" components for the HiveMind system:
1. **Secure Execution Environment**: A sandbox wrapper that uses AST-level restriction (`RestrictedPython`) to prevent unsafe code execution.
2. **Context Governance Service**: A centralized token counting and budgeting tool to ensure prompt stability.

## 2. Technical Specs

### 2.1 Sandbox Hardening (P0-1)

#### 2.1.1 Implementation Detail
- **RestrictedPython Integration**:
  - `compile_restricted` for scripts before execution.
  - Custom `safe_globals` based on `RestrictedPython.safe_globals`.
  - Override `__builtins__` to whitelist only: `print`, `json`, `math`, `asyncio`, `range`, `len`, `int`, `float`, `str`, `list`, `dict`, `set`, `tuple`, `Exception`.
- **Platform Bridge**:
  - A `platform` object injected into the sandbox.
  - `platform.call(tool_name, **kwargs)` maps to `ToolRegistry.ainvoke(tool_name, **params)`.
- **Async Timeout Orchestrator**:
  - Execution occurs inside `asyncio.wait_for(..., timeout=5.0)`.
- **Memory/Runtime Limit**: Simple `sys.setrecursionlimit(500)` to prevent recursion depth attacks.

### 2.2 Token Management System (P0-2)

#### 2.2.1 Data Model
- **Budget Vector**:
  - `SYSTEM_PROMPT_BUDGET`: 3,200
  - `ROLE_MEMORY_BUDGET`: 4,800
  - `RAG_CONTEXT_BUDGET`: 14,400
  - `CHAT_HISTORY_BUDGET`: 6,400
  - `OUTPUT_BUFFER`: 3,200 (for max_tokens)
- **Total Reference**: 32,768 (standard 32K window).

#### 2.2.2 TokenService API
- `count_tokens(text: str, model_id: str = "gpt-4o") -> int`: Basic count via `tiktoken`.
- `truncate_context(text: str, budget: int, mode: "line" | "char" = "line") -> str`: Truncates if above budget.
- `calculate_usage(messages: list[BaseMessage]) -> dict[str, int]`: Breaks down current turn's usage.

## 3. Integration Plan

- **SwarmOrchestrator**:
  - Integrate `TokenService` in the `_prepare_payload` phase.
  - Integrate restricted `ToolSandbox` for `CodeAgent` tool calls.
- **API Response**:
  - X-Trace-Tokens header in HTTP responses (BE).

## 4. Verification

- **Security Suite**: `backend/tests/security/test_sandbox_evasion.py` to attempt common `exec()` escapes.
- **Budget Suite**: `backend/tests/unit/core/test_token_service.py` with multi-language strings.
- **Performance**: Count tokens for a 128K context document under 200ms.
