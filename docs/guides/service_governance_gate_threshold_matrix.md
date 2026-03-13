# Service Governance Gate Threshold Matrix (Phase 5 Step-7)

## Scope

This document defines the formal gate thresholds by pipeline profile.

Profiles:
- feature: fast PR gate (quick signal, lower strictness)
- develop: integration gate (balanced strictness)
- main: production gate (strictest)
- sg1-schedule: rolling stability evidence gate (time window)

## Threshold Matrix

| Profile | SG7 max_error_budget | SG7 max_degrade_trigger_ratio | SG7 max_mttr_sec | SG3 min_cost_reduction_ratio | SG3 max_quality_regression | SG1 window_hours | SG1 min_reports | SG1 max_global_error_budget | SG1 max_steady_block_ratio | Step7 closure sg1_min_pass_count |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| feature | 0.70 | 0.80 | 60 | 0.10 | 0.03 | 24 | 1 | 0.30 | 0.20 | N/A |
| develop | 0.65 | 0.75 | 60 | 0.10 | 0.03 | 24 | 1 | 0.28 | 0.15 | N/A |
| main | 0.60 | 0.70 | 60 | 0.12 | 0.02 | 24 | 1 | 0.25 | 0.10 | 1 |
| sg1-schedule | 0.70 | 0.80 | 60 | N/A | N/A | 24 | 4 | 0.25 | 0.10 | 4 |

## Workflow Mapping

- feature profile: .github/workflows/feature-ci.yml
- develop profile: .github/workflows/develop-ci.yml
- main profile: .github/workflows/backend-ci.yml
- sg1-schedule profile: .github/workflows/sg1-stability-window.yml

## Update Rule

When changing thresholds:
1. Update the corresponding env vars in the workflow file.
2. Keep this matrix document in sync.
3. Update TODO changelog in the same change.
4. Verify with one local dry run for scripts:
   - validate_step5_sg3_cost_quality.py
   - validate_gate_sg1_stability_window.py
   - validate_step7_governance_gates.py
   - validate_step7_closure_readiness.py

## Rationale

- feature favors fast feedback while keeping hard failures meaningful.
- develop reduces regression risk before merge to main.
- main enforces stricter cost/quality/stability standards.
- sg1-schedule accumulates rolling 24h evidence for formal stability closure.
