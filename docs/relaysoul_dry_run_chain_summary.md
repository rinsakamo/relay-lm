# RelaySOUL Dry-Run Chain Summary

## Scope

This document summarizes the current RelaySOUL dry-run chain before real apply/rollback.

- Focus: persona source calibration pipeline
- Output: content-free artifacts and metadata-only safety gates
- Boundary: dry-run and contract validation only

## Pipeline

```text
feedback examples / user calibration
  -> patch prompt dry-run
  -> patch candidate parser dry-run
  -> temporary revision compile dry-run
  -> revision history store dry-run
  -> approval package dry-run
  -> approval package persistence dry-run linkage
  -> future approval decision / apply / rollback (not implemented)
```

## Implemented scripts and artifact support

- `scripts/relaylm_relaysoul_patch_prompt_dry_run.py`
- `scripts/relaylm_relaysoul_patch_candidate_dry_run.py`
- `scripts/relaylm_relaysoul_temp_revision_compile_dry_run.py`
- `scripts/relaylm_relaysoul_revision_history_store_dry_run.py`
- `scripts/relaylm_relaysoul_approval_package_dry_run.py`
- `relaylm/relaysoul_persistence.py` (includes `approval_package` support)

## Safety invariants

- no model API call inside these dry-runs
- no real persona file mutation
- no patch apply
- no rollback execution
- no actual persistence / DB write
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

- approval decision dry-run
- apply plan dry-run
- rollback plan dry-run
- artifact persistence storage design
- UI-facing approval summary
- later only: real apply/rollback with explicit approval
