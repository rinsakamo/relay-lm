# MVP-19 Summary

## Completed scope

- Added RelaySOUL approval decision dry-run (`#120`).
- Added RelaySOUL apply plan dry-run (`#122`).
- Added RelaySOUL rollback plan dry-run (`#125`).
- Kept storage envelope dry-run in place and integrated in dry-run flow (`#123`).
- Added persistence dry-run classification support for `apply_plan` and `rollback_plan` artifacts (`#128`).
- Added lineage mapping for plan artifacts:
  - `apply_plan_id` -> `artifact_id`
  - `approval_decision_id` -> `parent_artifact_id`
  - `rollback_plan_id` -> `artifact_id`
  - `apply_plan_id` -> `parent_artifact_id`
- Added blocked/non-ready plan handling and content-free plan/envelope validation.

## Design intent

- Move from approval package metadata to explicit user decision metadata.
- Convert approved decisions into apply plans without real apply execution.
- Convert ready apply plans into rollback plans without rollback execution.
- Keep apply/rollback plans audit-visible via persistence/envelope dry-runs before actual persistence exists.

## Runtime safety

MVP-19 remains dry-run-only and contract-only.

- no actual persistence
- no file write / DB write / path creation beyond requested output artifacts in scripts
- no patch apply
- no rollback execution
- no persona source mutation
- no model call
- no runtime behavior change
- no backend forwarding change
- no persona/memory/patch/prompt body content in metadata artifacts

## Main validation

- `python -m compileall relaylm`
- `python scripts/relaylm_relaysoul_persistence_smoke.py`
- Relevant script-level validations cover:
  - approval decision dry-run
  - apply plan dry-run
  - rollback plan dry-run
  - content-free validations
  - negative validations for denied/deferred decisions, non-ready apply plans, and rollback unavailable

## Current chain

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
  -> storage envelope / persistence dry-run linkage
  -> future actual persistence / apply / rollback (not implemented)
```

## Next phase

- approval/apply/rollback storage envelope CLI
- apply execution dry-run preflight
- rollback execution dry-run preflight
- actual persistence implementation after storage constraints
- real apply/rollback only after explicit user approval and fail-closed checks
