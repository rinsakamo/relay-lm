# MVP-17 Summary

## Completed scope

- Added `docs/relaysoul_persistence_storage_design.md` as a docs-only storage design for RelaySOUL artifact persistence.
- Fixed MVP-17A design points before implementation:
  - storage envelope concept for content-free artifacts
  - artifact lineage/index concept (`artifact_index` and `lineage_index`)
  - content-free persistence boundary and fail-closed policy
  - future implementation gates (path config, schema versioning, atomic write, corruption handling, opt-in flag)
- Kept scope aligned with current-main persistence contract and dry-run chain context.

## Design intent

MVP-17 establishes a reviewable storage-design baseline before any real persistence work.

- Define what a persistable RelaySOUL artifact record should look like.
- Preserve lineage traceability across `patch_dry_run` / `patch_compile_dry_run` / `rollback_summary` / `approval_summary` / `approval_package`.
- Keep warning/blocked artifact records auditable as future policy-controlled decisions.
- Enforce content-free-only artifact handling as a hard boundary.

## Runtime safety

This MVP remains docs-only.

- no actual persistence
- no file write
- no DB write
- no patch apply
- no revision apply
- no rollback execution
- no persona source mutation
- no model call
- no runtime behavior change
- no backend forwarding payload change
- no persona/memory/patch body content in diagnostics/artifacts

## Main validation

- `python -m compileall relaylm`
- `git diff --name-only origin/main...HEAD`

## Next phase

- implementation planning for storage path configuration and schema/version contracts
- persistence writer safety design (atomic write, fsync/tmp-rename, corruption recovery)
- index update policy and retention/pruning policy details
- opt-in guarded implementation MVP for actual persistence (separate from MVP-17)
