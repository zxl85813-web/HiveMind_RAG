# Collaboration And Delivery Playbook

> Canonical guide for team collaboration, GitHub automation, milestone sync, and high-availability delivery tracks.
>
> 本手册是 [🧬 共学体系](../COLLABORATIVE_LEARNING.md) 中「互学循环」的操作落地——Issue 协作、Code Review、PR 知识传递的具体规则都在这里。

## Scope

This document consolidates content previously split across:

- `docs/team_collaboration_guide.md`
- `docs/github_advanced_integrations.md`
- `docs/MILESTONE_TOOL.md`
- `docs/TEAM_TASK_GUIDE_M7.md`

## 1. Team Collaboration Baseline

### 1.1 Issue-Driven Development

- Use GitHub Issues as the single task record.
- Every implementation task must map to one issue.
- Labels should include at least: type, priority, module.

Recommended board columns:

- `To Do`
- `In Progress`
- `Reviewing`
- `Done`

### 1.2 Branch And PR Rules

- Never commit directly to `main`.
- Use branch naming with issue mapping: `feature/issue-{id}-{slug}` or `fix/issue-{id}-{slug}`.
- PR description must include `Closes #ID`.
- Merge only after CI passes.

### 1.3 Review And Protection Rules

- Enable branch protection on `main`.
- Require PR before merge.
- Require at least one approval.
- Require status checks to pass.

## 2. GitHub Automation Stack

### 2.1 Dependabot

Use `.github/dependabot.yml` to schedule dependency updates for backend and frontend.

### 2.2 GitHub Projects V2

Use one project board for all active milestones.

Recommended fields:

- Owner
- Status
- Priority
- Milestone
- Target Date

### 2.3 Copilot In PR Workflow

- Generate PR summary for large changes.
- Use AI-assisted review as a second-pass checker, not a replacement for human review.

### 2.4 Preview Deployments

For frontend-heavy PRs, enable preview environment (for example Vercel/Netlify) so reviewers can validate UI without local checkout.

### 2.5 Auto Label And Auto Assign

Set automation rules by changed paths.

Example:

- `backend/app/schemas/**` -> add `api-change` label and assign backend reviewer.
- `frontend/src/**` -> add `frontend` label and assign frontend reviewer.

## 3. Milestone Sync Tool (TODO -> GitHub)

Script:

- `backend/scripts/create_github_milestone_from_todo.py`

Purpose:

- Parse tasks from a TODO section.
- Create or reuse a GitHub milestone.
- Optionally create issues and bind them to the milestone.

### 3.1 Prerequisites

- `GITHUB_TOKEN` with repo scope.
- target repository `owner/name`.

### 3.2 Typical Commands

Dry-run:

```powershell
C:/Users/linkage/Desktop/aiproject/.venv/Scripts/python.exe backend/scripts/create_github_milestone_from_todo.py
```

Apply milestone:

```powershell
C:/Users/linkage/Desktop/aiproject/.venv/Scripts/python.exe backend/scripts/create_github_milestone_from_todo.py \
  --apply \
  --repo zxl85813-web/HiveMind_RAG \
  --milestone-title "M7 Agent TODO Sprint" \
  --due-on 2026-03-31
```

Apply milestone with issue creation:

```powershell
C:/Users/linkage/Desktop/aiproject/.venv/Scripts/python.exe backend/scripts/create_github_milestone_from_todo.py \
  --apply \
  --repo zxl85813-web/HiveMind_RAG \
  --milestone-title "M7 Agent TODO Sprint" \
  --create-issues \
  --labels "todo-sync,agent,planning"
```

## 4. High-Availability Delivery Tracks (M7 Template)

Use this as a reusable template for milestone planning.

### Track A: LLM Routing + Circuit Breaker

Goals:

- route requests by complexity and cost tier
- graceful fallback when premium providers fail

Suggested topics:

- semantic routing
- circuit breaker states: closed/open/half-open

### Track B: CQRS + Async Ingestion

Goals:

- separate user query path from heavy ingestion workloads
- move write-heavy tasks to worker queue

Suggested topics:

- CQRS
- Celery/ARQ
- queue-based status tracking

### Track C: Frontend Resilience

Goals:

- avoid full-page crash on component failure
- reduce unnecessary rerenders under streaming updates

Suggested topics:

- error boundaries
- state segmentation
- debounce/throttle for streaming UI

### Track D: Code Vault Knowledge Assets

Goals:

- prevent duplicate wheel-building
- surface reusable code assets before generation

Suggested topics:

- AST parsing
- graph modeling (Neo4j)
- similarity deduplication (hash/minhash)

## 5. Adoption Checklist

- [ ] Team uses issue-driven workflow for all feature work.
- [ ] Branch protection enabled on `main`.
- [ ] CI checks required before merge.
- [ ] Milestone sync tool used for sprint planning.
- [ ] At least one automation from section 2 enabled.
- [ ] Current milestone uses at least one track from section 4.

## Related Docs

- `docs/DEV_GOVERNANCE.md`
- `docs/architecture/branch-strategy.md`
- `docs/LEARNING_PATH.md`
- `docs/ROADMAP.md`
