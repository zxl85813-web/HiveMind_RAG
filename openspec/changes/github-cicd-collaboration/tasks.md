# Tasks: CI/CD and Comprehensive Engineering Workflow

## 1. Establish Architecture Review Process (ADR)
- [x] Create directory `docs/architecture/decisions/`.
- [x] Create `docs/architecture/decisions/0000-use-madr.md` as the template and first baseline decision.
- [x] Update OpenSpec `config.yaml` to document the ADR requirement in project context.

## 2. Upgrade Repository Configuration & Testing Tools
- [x] **Backend:** Add `pytest-cov` and `black` to backend dev requirements.
- [x] **Backend:** Update `pyproject.toml` to enforce `mypy` strictness, set ruff strict rules, and set `pytest-cov` minimum coverage to 80%.
- [x] **Frontend:** Add `typecheck`, `test:unit`, `format:check` scripts to `package.json`.
- [x] **Frontend:** Confirm `tsconfig.app.json` strict mode is fully on.

## 3. Setup Strict CI/CD Pipelines
- [x] Create `.github/workflows/backend-ci.yml`:
  - Checkout -> Setup Python -> Install dependencies.
  - Run `ruff check .` and `black --check .`.
  - Run `mypy app/`.
  - Run `pytest --cov=app --cov-fail-under=80`.
- [x] Create `.github/workflows/frontend-ci.yml`:
  - Checkout -> Setup Node.js -> `npm ci`.
  - Run `npm run lint`.
  - Run `tsc --noEmit`.
  - Run `vitest run --coverage`.

## 4. Establish Collaboration & Code Review Templates
- [x] Create `.github/PULL_REQUEST_TEMPLATE.md` with:
  - Description of changes.
  - Links to related OpenSpec/ADR.
  - Testing checklist (Did you write tests?).
  - Architecture gate (Does this modify Core/DB?).
- [x] Create `.github/ISSUE_TEMPLATE/bug_report.md`.
- [x] Create `.github/ISSUE_TEMPLATE/feature_request.md`.
- [x] Create `.github/ISSUE_TEMPLATE/architecture_proposal.md` for ADR discussions.
- [x] Create `.github/workflows/pr-labeler.yml` to automatically add `needs-architecture-review` label.

## 5. Branch Strategy Documentation
- [x] Create `CONTRIBUTING.md` in the root.
- [x] Define the Branching Strategy (`main`, `feature/*`, `fix/*`).
- [x] Define the Code Review rules (Max 500 lines, 1 approving review required).
- [x] Define the Conventional Commits format.
- [x] Document the complete development lifecycle (from idea to merge).
