# Doc Hygiene Review - 2026-03-09

## Scope

- Target: `docs/**/*.md`
- Goal: identify stale or unreferenced docs and broken links

## Automated Checks

- Broken local markdown links: `0`
- Notes: three previously broken links were fixed during this pass

## Candidate Trash Docs (Need Owner Decision)

These are not confirmed trash yet. They are candidates because they are stage-specific, weakly linked, or overlap with governance docs.

### High Suspicion

- `docs/TEAM_TASK_GUIDE_M7.md`
- `docs/team_collaboration_guide.md`
- `docs/github_advanced_integrations.md`

Reason:
- Mostly operational guidance and time-bound process notes
- Significant overlap with `docs/DEV_GOVERNANCE.md` and collaboration workflow notes
- Not part of core L0-L4 path

### Medium Suspicion

- `docs/design/*.md` (topic design docs not directly linked by file in index)
- `docs/requirements/REQ-001..012` (directory linked, but file-level visibility is low)
- `docs/changelog/devlog/*.md` (historical entries not always referenced)

Reason:
- Likely valid but discoverability is weak
- Some files look archival instead of active reference docs

## Keep / Archive / Delete Policy

Use this policy for each candidate file:

1. Keep if used in current quarter and has clear owner.
2. Archive if historical but still useful.
3. Delete if fully superseded and no owner can justify retention.

## Recommended Actions

1. Add metadata header to stage docs: `status`, `owner`, `last_reviewed`.
2. Create `docs/archive/` for completed milestone guides.
3. Merge overlapping collaboration guides into one canonical file.
4. Link active `requirements` and `design` docs by file from index pages if they are still in use.

## Proposed Initial Archive Batch (Safe)

These can be archived first with low risk, pending your confirmation:

- `docs/TEAM_TASK_GUIDE_M7.md`
- `docs/team_collaboration_guide.md`

## Command Notes

- Link scan included all markdown files under repository.
- Directory-level links were treated as valid references for navigation.
