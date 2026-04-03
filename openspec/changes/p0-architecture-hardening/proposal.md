# Proposal: P0 Architecture Hardening

> **Status**: Draft  
> **Author**: Antigravity  
> **Resolves**: [REQ-014-P0_ARCHITECTURE_HARDENING](../../docs/requirements/REQ-014-P0_ARCHITECTURE_HARDENING.md)

## 1. Summary

This change addresses two critical security and stability gaps identified in the "Chief Architect Review" (April 2026):
1. **Sandbox Security**: Moving from raw `exec()` to `RestrictedPython` with strict timeouts and module whitelists.
2. **Context Stability**: Implementing a 32K token budget system to prevent context window overflow and TTFT degradation.

## 2. Problem Statement

- **Current Sandbox**: The `tool_sandbox.py` is vulnerable to RCE and resource exhaustion via malicious or poorly written agent scripts.
- **Context Governance**: No deterministic way to measure and cap token usage in prompts, leading to unpredictable failures and "Lost in the Middle" syndrome.

## 3. Proposed Solution

### 3.1 Sandbox Hardening
- Use `RestrictedPython` to compile and execute agent-generated scripts.
- Inject a controlled `platform` object for tool interaction.
- Enforce a 5s execution timeout.
- Whitelist only safe modules (`math`, `json`, `asyncio`).

### 3.2 Token Budgeting
- Introduce `TokenService` using `tiktoken`.
- Manage a 32K context window with predefined quotas (System 10%, Memory 15%, RAG 45%, History 20%, Output 10%).
- Provide a `truncate_to_budget` utility that cuts content at line boundaries to maintain legibility.

## 4. Non-goals

- Full containerization (Docker/Firecracker) - deferred to a separate infra-heavy milestone.
- RAG Ranking optimization - this is purely about context management.

## 5. Risk Assessment

| Risk | Mitigation |
| :--- | :--- |
| Truncation losing valid facts | Use line-based truncation and log when truncation occurs. |
| RestrictedPython blocking valid code | Whitelist necessary utilities (json, math, custom bridge). |
| Latency impact of tiktoken | Cache encoding objects; token counting is O(N) but generally fast. |

## 6. Success Criteria

- Unit tests for Sandbox block `os.system` or `__import__`.
- Integration tests confirm Swarm stops infinite loops.
- Trace logs show token counts per-turn.
