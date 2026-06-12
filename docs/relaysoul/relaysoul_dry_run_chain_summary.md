# RelaySOUL Dry-Run Chain Summary

## Scope

This document summarizes the current RelaySOUL dry-run chain before real apply/rollback.

- Focus: persona source calibration pipeline
- Output: content-free artifacts and metadata-only safety gates
- Boundary: dry-run and contract validation only

## Pipeline

```text
feedback/examples
  -> patch prompt dry-run
  -> patch candidate parser dry-run
  -> temp revision compile dry-run
  -> revision history store dry-run
  -> approval package dry-run
  -> approval decision dry-run
  -> apply plan dry-run
  -> rollback plan dry-run
  -> persistence classification
  -> storage envelope CLI dry-run
  -> storage path planner dry-run
  -> storage index dry-run
  -> apply execution preflight dry-run
  -> rollback execution preflight dry-run
  -> storage writer preflight dry-run
  -> persistence execution preflight dry-run
  -> future actual persistence / apply / rollback
```

## Implemented scripts and artifact support

- `scripts/relaylm_relaysoul_patch_prompt_dry_run.py`
- `scripts/relaylm_relaysoul_patch_candidate_dry_run.py`
- `scripts/relaylm_relaysoul_temp_revision_compile_dry_run.py`
- `scripts/relaylm_relaysoul_revision_history_store_dry_run.py`
- `scripts/relaylm_relaysoul_approval_package_dry_run.py`
- `scripts/relaylm_relaysoul_approval_decision_dry_run.py`
- `scripts/relaylm_relaysoul_apply_plan_dry_run.py`
- `scripts/relaylm_relaysoul_rollback_plan_dry_run.py`
- `scripts/relaylm_relaysoul_storage_envelope_dry_run.py`
- `scripts/relaylm_relaysoul_storage_path_plan_dry_run.py`
- `scripts/relaylm_relaysoul_storage_index_dry_run.py`
- `scripts/relaylm_relaysoul_apply_execution_preflight_dry_run.py`
- `scripts/relaylm_relaysoul_rollback_execution_preflight_dry_run.py`
- `scripts/relaylm_relaysoul_storage_writer_preflight_dry_run.py`
- `scripts/relaylm_relaysoul_persistence_execution_preflight_dry_run.py`
- `relaylm/relaysoul_persistence.py` (includes persistence classification + envelope helper support)

## Safety invariants

- no model API call inside these dry-runs
- no real persona file mutation
- no patch apply
- no rollback execution
- no actual persistence / DB write
- no storage path creation
- no storage index append
- no runtime behavior change
- no backend forwarding change
- no persona body / memory body / patch_text / prompt_text in persisted metadata artifacts
- `content_free: true` where applicable

## RelaySOUL vs RelayLM roles

- **RelaySOUL**
  - persona calibration inputs
  - patch proposal shaping and normalization
  - temporary revision metadata
  - approval package generation
- **RelayLM**
  - compiler and diagnostics surface
  - persistence contract validation helpers
  - runtime boundary enforcement

Current boundary remains dry-run and contract-only.

## Why this matters

- Supports fast persona/SOUL iteration with visible audit/rollback lineage.
- Keeps a clear path for future explicit user approval UI.
- Prevents hidden persona mutation during experimentation.
- Exposes oversized SOUL/OUTPUT_POLICY changes via compile/budget/approval/persistence gates.

## Current non-goals

- real patch apply
- automatic SOUL rewrite
- rollback execution
- DB-backed revision store
- runtime attachment
- model-call orchestration
- unsafe/adult/persona body examples

## Next phase options

- apply execution gate design
- rollback execution gate design
- storage writer gate design
- later only: real persistence writer / real apply / real rollback with explicit approval and fail-closed checks
