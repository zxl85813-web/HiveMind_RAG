# Design: Comprehensive Engineering Workflow

## Architecture / Approach

1.  **The Design Document Mechanism (ADR/RFC)**
    *   **Structure:** We will introduce a `/docs/architecture/decisions/` folder based on the MADR (Markdown Architectural Decision Records) format.
    *   **Trigger:** Any change classified as "Architecture" (e.g., new databases, major routing changes, new core dependencies) must start with an ADR PR.
    *   **Review:** ADRs must be approved by the lead architect/maintainer before the actual code OpenSpec is proposed.

2.  **Continuous Integration (CI) Automation**
    *   **Backend (`.github/workflows/backend-ci.yml`)**:
        *   Linters: `ruff` (with strict rule sets), `black`, `mypy` (for strict static typing).
        *   Testing: `pytest` executed with `pytest-cov`.
        *   Gate: Fail the build if test coverage drops below 80%.
    *   **Frontend (`.github/workflows/frontend-ci.yml`)**:
        *   Linters: `ESLint` (strict rules), `Prettier`.
        *   Typecheck: `tsc --noEmit` to strictly enforce TypeScript rules.
        *   Testing: `Vitest` for Unit Tests and `Playwright` for E2E. Fail if coverage < 80%.

3.  **Code Review (CR) Rules & PR Gates**
    *   **Automated Gates:** Branch protection rules on `main` will require:
        1. All CI checks (Backend/Frontend) to pass.
        2. At least 1 approving code review.
        3. 0 unresolved comment threads.
    *   **PR Template (`.github/PULL_REQUEST_TEMPLATE.md`):** Will include dynamic checklists:
        *   *Standard:* Lint, Unit Tests added, OpenSpec updated.
        *   *Architecture:* Does this change the DB? Requires Architecture Review label and sign-off.

4.  **Architecture-Level Review Rules**
    *   Introduced via GitHub Labels: `needs-architecture-review`.
    *   Triggered automatically if files in `backend/alembic/`, `backend/app/models/`, `backend/app/core/`, or `docs/architecture/` are modified.
    *   Requires a specialized review looking at Big-O complexity, security boundaries, and scalability, separate from logic nitpicks.

## Data Model / Configurations
- Github repository branch protection rules (applied manually or via terraform/gh cli).
- YAML definitions for Actions.
- Updates to `pyproject.toml` (for `pytest-cov`, `mypy` rules).
- Updates to `package.json` / `eslint.config.js`.
