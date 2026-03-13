# Service Governance Topology (Phase 5 / TASK-SG-001)

## 1. Scope

This document defines the deployment topology and gray rollout switch for:

- Retrieval path (low-latency read)
- Ingestion path (heavy IO / async write)

Goal: keep API contracts unchanged while enabling monolith/split runtime switch and safe rollback.

## 2. Runtime Modes

### 2.1 Monolith Mode (default)

- `SERVICE_TOPOLOGY_MODE=monolith`
- All requests run in current single-process path.
- Gray percent is ignored.

### 2.2 Split Mode (gray)

- `SERVICE_TOPOLOGY_MODE=split`
- `SERVICE_GOVERNANCE_GRAY_PERCENT=0..100`
- Stable hash routing by `user_id + query` decides path:
  - `split` path when bucket `< gray_percent`
  - fallback `monolith` otherwise

## 3. Config Contract

From `backend/app/core/config.py`:

- `SERVICE_TOPOLOGY_MODE`: `monolith | split`
- `SERVICE_GOVERNANCE_GRAY_PERCENT`: integer `0..100`
- `RETRIEVAL_SERVICE_URL`: reserved endpoint for future dedicated retrieval service
- `INGESTION_SERVICE_URL`: reserved endpoint for future dedicated ingestion service

## 4. Operational Visibility

Observability API:

- `GET /api/v1/observability/service-governance`

Example payload fields:

- `topology_mode`
- `gray_percent`
- `is_split_enabled`
- `retrieval_service_url`
- `ingestion_service_url`

## 5. Rollback Procedure

1. Set `SERVICE_TOPOLOGY_MODE=monolith`
2. (Optional) set `SERVICE_GOVERNANCE_GRAY_PERCENT=0`
3. Restart application
4. Verify with `GET /api/v1/observability/service-governance`

Rollback does not require API changes and can be completed within one deployment window.

## 6. Acceptance Mapping (TASK-SG-001)

- "Topology boundary + config switch": completed by mode config + governance selector.
- "No API contract changes": existing retrieval APIs remain unchanged.
- "Scriptable rollback": environment variable rollback path documented above.
