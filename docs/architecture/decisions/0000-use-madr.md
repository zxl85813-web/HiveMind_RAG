# ADR-0000: Use MADR (Markdown Architectural Decision Records)

## Status

Accepted

## Date

2026-03-04

## Context

As the HiveMind RAG project grows in complexity — with multiple AI agents, a knowledge graph, configurable pipelines, and an AI-first frontend — we need a structured mechanism to document significant architectural decisions **before** implementation begins.

Without such a mechanism:
- Architectural choices are buried in chat history or TODO.md entries.
- New contributors have no way to understand **why** a decision was made.
- Conflicting implementations emerge when different contributors take different approaches.

## Decision

We will use **Markdown Architectural Decision Records (MADR)** to document all significant architecture decisions.

### Rules

1. **Scope:** An ADR is required for any change that:
   - Introduces a new database table or modifies existing schemas (`backend/app/models/`).
   - Adds a new external dependency or integration (e.g., new LLM provider, new vector store).
   - Changes inter-module communication patterns (e.g., `agents/` ↔ `services/`).
   - Alters the core infrastructure (`backend/app/core/`).
   - Introduces a new top-level directory or fundamentally restructures existing ones.

2. **Format:** Each ADR must follow this template:
   ```
   # ADR-NNNN: <Title>
   ## Status        (Proposed | Accepted | Deprecated | Superseded by ADR-XXXX)
   ## Date          (YYYY-MM-DD)
   ## Context       (What is the problem? Why is this decision needed?)
   ## Decision      (What did we decide? Be specific.)
   ## Consequences  (What are the trade-offs? What becomes easier/harder?)
   ## Alternatives  (What other options were considered and why rejected?)
   ```

3. **Lifecycle:**
   - An ADR starts as a **Pull Request** with status `Proposed`.
   - After review and approval by the maintainer, status changes to `Accepted`.
   - Code implementation may **only begin after** the ADR PR is merged.
   - If a decision is later reversed, the old ADR is marked `Deprecated` or `Superseded by ADR-XXXX`.

4. **Numbering:** ADRs are numbered sequentially: `0001`, `0002`, etc.

5. **Location:** All ADRs live in `docs/architecture/decisions/`.

## Consequences

- **Positive:** Architecture decisions are transparent, reviewable, and searchable.
- **Positive:** New contributors can onboard by reading the ADR history.
- **Positive:** OpenSpec proposals can reference ADRs for deeper architectural context.
- **Negative:** Adds a small overhead to the development process for major changes (but this is intentional).

## Alternatives

| Alternative | Why Rejected |
|-------------|-------------|
| Wiki pages | Not version-controlled; easy to fall out of sync with code. |
| Inline code comments | Too scattered; not reviewable as a cohesive decision. |
| Verbal decisions in meetings | Not recorded; knowledge is lost when team members change. |
