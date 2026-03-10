# Collaborative Learning Metrics Guide

## Scope

This guide defines CL-3 metric formulas, data sources, and weekly reporting rules for the collaborative learning system.

Related docs:

- `docs/COLLABORATIVE_LEARNING.md`
- `docs/learning/weekly/WEEKLY_LEARNING_REPORT_TEMPLATE.md`

## Metric Definitions

### 1) Self-Reflection Activity

Definition:

- Number of reflection entries generated in one week per active agent.

Formula:

- `self_reflection_activity = weekly_reflections / active_agents`

Data source:

- `swarm_reflections` table (`created_at`, `agent_name`)

Target:

- `>= 3.0 entries/agent/week`

### 2) Mutual Learning Coverage

Definition:

- Ratio of PRs that contain at least 2 substantial review comments.

Formula:

- `mutual_learning_coverage = reviewed_prs_ge_2 / total_prs`

Data source:

- GitHub PR review data (manual input first, API automation later)

Target:

- `>= 60%`

### 3) Knowledge Crystallization Rate

Definition:

- Number of newly added or updated reusable knowledge assets per month.

Formula:

- `knowledge_crystallization_rate = skill_updates + registry_updates`

Data source:

- `skills/` updates and `REGISTRY.md` updates

Target:

- `>= 1 item/month`

### 4) Gap Closure Rate

Definition:

- Ratio of previous-week GAP items closed this week.

Formula:

- `gap_closure_rate = closed_gaps / total_gaps`

Data source:

- `swarm_reflections` GAP items + weekly closure tracking (manual status first)

Target:

- `>= 50%`

### 5) Flywheel Conversion Rate

Definition:

- Ratio of positive feedback converted into reusable evaluation assets.

Formula:

- `flywheel_conversion_rate = promoted_feedback_items / liked_feedback_items`

Data source:

- Feedback and evaluation promotion stats (manual input first)

Target:

- Upward trend week-over-week

## Weekly Reporting Rules

- Reporting cadence: once per week (recommended Monday morning).
- Baseline period: last 7 days.
- If one metric cannot be auto-collected, report it with `manual` source tag.
- Every metric row must include: value, formula, source, owner, next action.
- If value is below target, add one concrete action with deadline.

## Data Source Tags

Use one of the following tags in reports:

- `auto_db`: automatically collected from database.
- `auto_file`: automatically collected from repository files.
- `manual`: manually entered by reviewer.
- `mixed`: auto + manual mixed source.

## Ownership

- Governance owner: maintains metric definitions and thresholds.
- Reflection owner: verifies reflection and gap closure quality.
- Team lead: approves weekly actions and tracks completion.
