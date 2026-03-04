# Specification: Engineering Workflow & Quality Gates

## Definition
This specification defines the mandatory quality gates, code review standards, and architectural design processes that must be followed for all contributions to the HiveMind RAG project.

## Requirements

### 1. Design & Architecture (ADR)
- **REQ-A1:** Any major architectural change MUST be documented as an Architecture Decision Record (ADR) in `docs/architecture/decisions/`.
- **REQ-A2:** ADRs must follow the standard syntax: Context, Decision, Consequences.
- **REQ-A3:** Code implementation cannot begin until the ADR is merged.

### 2. Code Review (CR) Standards
- **REQ-CR1:** All changes must go through a Pull Request targeting the `main` branch.
- **REQ-CR2:** PRs must not exceed 500 lines of code changes (excluding auto-generated locks/migrations) to ensure effective human review.
- **REQ-CR3:** PRs altering core schemas (`models/`) or core configurations (`core/`) MUST pass an "Architecture Review" by a designated maintainer.

### 3. Automated CI/CD Gates
- **REQ-CI1 (Backend):** The `backend-ci.yml` must run `ruff`, `black`, `mypy`, and `pytest`.
- **REQ-CI2 (Frontend):** The `frontend-ci.yml` must run `eslint`, `prettier`, `tsc`, and `vitest`/`playwright`.
- **REQ-CI3:** Branch protection MUST prevent merging if CI fails.

### 4. Unit Testing Rules
- **REQ-T1:** The CI pipeline MUST run code coverage tools (`pytest-cov` / `istanbul`).
- **REQ-T2:** Global test coverage MUST NOT drop below 80%.
- **REQ-T3:** Every new Feature/Bugfix PR MUST include corresponding unit tests.

## Acceptance Criteria
- [ ] ADR template and directory exist.
- [ ] PR Template is updated with architecture and testing checklists.
- [ ] Branch protection rules are documented or applied.
- [ ] `backend-ci.yml` runs tests and fails on coverage `< 80%`.
- [ ] `frontend-ci.yml` runs tests and typescript checks.
