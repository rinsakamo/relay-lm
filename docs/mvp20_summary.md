# MVP-20 Summary

## Completed scope

- Added RelaySOUL storage envelope blocked-reason propagation follow-up (`#133`).
- Top-level storage envelope dry-run `warning_reasons` and `blocking_reasons` now include persistence dry-run reasons.
- Blocked envelope results now expose blockers such as `missing_artifact_id` at top level, without requiring callers to inspect only embedded envelope fields.
- Added RelaySOUL storage envelope CLI dry-run (`#135`).
- CLI now wraps content-free artifacts into storage envelope dry-run output.
- Added apply-plan and rollback-plan envelope CLI validation paths.
- Added negative validation for non-content-free payloads and unsupported artifact kinds.

## Design intent

- Make envelope dry-run outputs audit/UX friendly at top level.
- Expose explicit reason fields before any actual persistence exists.
- Provide a small CLI boundary for future persistence-writer integration.
- Keep storage envelope creation separate from actual persistence.

## Runtime safety

MVP-20 remains dry-run-only and contract-only.

- no actual persistence
- no file write / DB write beyond requested output JSON
- no storage path creation
- no patch apply
- no rollback execution
- no persona source mutation
- no model call
- no runtime behavior change
- no backend forwarding change
- content-free artifact boundary remains enforced

## Main validation

- `python -m compileall relaylm`
- `python scripts/relaylm_relaysoul_persistence_smoke.py`
- `python -m compileall relaylm scripts/relaylm_relaysoul_storage_envelope_dry_run.py`
- storage envelope CLI dry-run for apply plan artifacts
- storage envelope CLI dry-run for rollback plan artifacts
- content-free validation
- negative validation for non-content-free payloads and unsupported artifact kinds

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
  -> persistence classification
  -> storage envelope CLI dry-run
  -> future actual persistence / apply / rollback (not implemented)
```

## Next phase

- apply execution dry-run preflight
- rollback execution dry-run preflight
- actual persistence writer dry-run / path planner
- storage index dry-run
- only later: real persistence and real apply/rollback with explicit approval and fail-closed checks
