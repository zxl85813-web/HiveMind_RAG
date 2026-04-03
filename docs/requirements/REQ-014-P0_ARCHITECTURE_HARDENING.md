# REQ-014 — P0 Architecture Hardening (Sandbox & Token)

> **Objective**: Mitigate critical security risks and implement context window budget management to ensure system stability and cost-efficiency.

---

## 1. Context & Rationale

During the architecture review of the HiveMind Intelligence Swarm, two critical P0 (highest priority) gaps were identified:
1. **Security Vulnerability**: The current `tool_sandbox.py` uses `exec()` with minimal safeguards, posing a high risk of Remote Code Execution (RCE) or resource exhaustion.
2. **Context Instability**: The system lacks formal Token tracking and budgeting, leading to "context explosion," increased latency, and potential model crashes via "Lost in the Middle" syndrome.

## 2. Requirements

### 2.1 P0-1: 核心沙箱安全加固 (Sandbox Hardening)
- **Constraint**: No direct use of `exec()` without compiled code restrictions.
- **Dependency**: Introduce `RestrictedPython` to provide a safe sub-environment.
- **Resource Limits**: 
    - Implement a strict timeout (e.g., 5 seconds) for any orchestrated script.
    - Prevent access to non-whitelisted modules (os, subprocess, etc.).
- **Audit**: Log every execution attempt, its success, and any security violations.

### 2.2 P0-2: TokenService & 32K 预算系统 (Token Management)
- **Dependency**: Implement `TokenService` using `tiktoken` (standardized on OpenAI-compatible counts).
- **Budget Distribution (32K Reference)**:
    - **System Rules**: 10% (3,200)
    - **Memory (Role/Personal)**: 15% (4,800)
    - **RAG Context**: 45% (14,400)
    - **Chat History**: 20% (6,400)
    - **Output/Buffer**: 10% (3,200)
- **Auto-Truncation**: If a segment exceeds its budget, the service must provide a truncation utility that respects semantic boundaries where possible (line-based).
- **Observability**: Metrics on token usage per-conversation must be emitted to `UnifiedLog`.

## 3. Success Criteria

1. **Security**: An attempt to import `os` or read root files in the sandbox must be blocked and logged as a security alert.
2. **Stability**: A script with `while True: pass` must time out without crashing the backend.
3. **Budget**: Agent prompts must be pre-evaluated for token usage, and truncated if over budget, preventing API errors for "context overflow."

---

> **Status**: Draft / Needs PR  
> **Milestone**: M7.3 (Architecture Resilience)
