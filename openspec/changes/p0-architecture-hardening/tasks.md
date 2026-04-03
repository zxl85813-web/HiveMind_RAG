# Tasks: P0 Architecture Hardening

> **Status**: Ready  
> **Author**: Antigravity  
> **Context**: [REQ-014-P0_ARCHITECTURE_HARDENING](../../docs/requirements/REQ-014-P0_ARCHITECTURE_HARDENING.md)

---

## 🛠️ Implementation Tasks

### T1: Sandbox Security Hardening (P0-1)

| Task ID | Description | Deliverable | Status |
| :--- | :--- | :--- | :---: |
| **T1.1** | Add `RestrictedPython` to `pyproject.toml` | [x] Dependency Check | ✅ |
| **T1.2** | Implement `app.services.sandbox.safe_environment.SafeEnvironment` | `safe_environment.py` | ⬜ |
| **T1.3** | Refactor `tool_sandbox.py` to use `SafeEnvironment` and `asyncio.wait_for` | `tool_sandbox.py` (updated) | ⬜ |
| **T1.4** | Create security test suite `backend/tests/security/test_sandbox_security.py` | `test_sandbox_security.py` | ⬜ |
| **T1.5** | Add timeout & infinite loop unit tests | `test_sandbox_timeout.py` | ⬜ |

### T2: TokenService & 32K 预算系统 (P0-2)

| Task ID | Description | Deliverable | Status |
| :--- | :--- | :--- | :---: |
| **T2.1** | Add `tiktoken` to `pyproject.toml` | [x] Dependency Check | ✅ |
| **T2.2** | Implement `app.core.token_service.TokenService` with `truncate_context` | `token_service.py` | ⬜ |
| **T2.3** | Update `app.core.config.Settings` with budget constants | `config.py` (updated) | ⬜ |
| **T2.4** | Integrate `TokenService` into `SwarmOrchestrator` payload preparation | `swarm.py` (updated) | ⬜ |
| **T2.5** | Unit test `TokenService` coverage (100% boundary) | `test_token_service.py` | ⬜ |

### T3: Integration & Global Tracing

| Task ID | Description | Deliverable | Status |
| :--- | :--- | :--- | :---: |
| **T3.1** | Inject Token counts into `UnifiedLog` | `UnifiedLog` with Token Meta | ⬜ |
| **T3.2** | Final smoke test on `SwarmOrchestrator` with P0 Harness | `smoke_test_swarm_harness.py` | ⬜ |
| **T3.3** | Update Architecture documentation with Harness P0 details | `ARCH-HARDNESS.md` | ⬜ |

---

## 📅 Roadmap Overview

- **Now**: P1.1-P1.3 (Security)
- **Next**: P2.1-P2.3 (Token Logic)
- **Future**: M7.5 (Full MCP Standardization)
