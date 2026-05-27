# RelaySOUL Gate Dry-Run CLI Design

## Scope

This document defines a future CLI design for producing metadata-only gate decision artifacts.

- apply execution gate
- rollback execution gate
- storage writer gate
- persistence execution gate
- docs-only design; no implementation

## Current state

- preflight dry-run chain exists through persistence execution preflight
- gate design docs exist
- explicit approval artifact contract exists
- lineage freshness policy exists
- actual persistence / apply / rollback are not implemented

## Gate dry-run purpose

- evaluate gate readiness without executing actual persistence/apply/rollback
- combine preflight artifacts, approval artifact, and freshness status
- emit content-free gate decision artifacts
- keep all execution allowed flags false by default

## Proposed CLI scripts

- `scripts/relaylm_relaysoul_apply_execution_gate_dry_run.py`
- `scripts/relaylm_relaysoul_rollback_execution_gate_dry_run.py`
- `scripts/relaylm_relaysoul_storage_writer_gate_dry_run.py`
- `scripts/relaylm_relaysoul_persistence_execution_gate_dry_run.py`

## Shared inputs

- explicit approval artifact
- relevant preflight artifact
- storage envelope
- storage path plan
- storage index plan
- freshness metadata or freshness checker output
- `--output`

## Gate-specific inputs

- apply gate:
  - apply plan dry-run
  - apply execution preflight
  - rollback readiness/preflight reference
- rollback gate:
  - rollback plan dry-run
  - rollback execution preflight
  - apply plan lineage reference
- storage writer gate:
  - storage writer preflight
  - apply or rollback execution preflight
- persistence gate:
  - persistence execution preflight
  - storage writer gate decision
  - apply or rollback gate decision based on `execution_preflight_type`

## Shared validation rules

- all inputs `content_free = true`
- statuses must be `ready` / `ok`
- no `blocking_reasons`
- `approval_status = approved`
- `approval_scope` matches target gate
- `lineage_freshness_status = fresh`
- `artifact_kind` / `target_artifact_id` / `parent_artifact_id` / `character_id` match
- `artifact_path` / `artifact_index_path` / `lineage_index_path` match expected values
- forbidden content keys absent
- nested forbidden keys absent
- unsafe identity rejected

## Proposed output artifacts

- `relaysoul_apply_execution_gate_decision`
- `relaysoul_rollback_execution_gate_decision`
- `relaysoul_storage_writer_gate_decision`
- `relaysoul_persistence_execution_gate_decision`

## Shared output fields

- `artifact_type`
- `schema_version: mvp-soul-0`
- `content_free: true`
- `gate_status: blocked|ready`
- `gate_scope`
- `approval_id`
- `lineage_freshness_status`
- `target_artifact_kind`
- `target_artifact_id`
- `parent_artifact_id`
- `character_id`
- `execution_preflight_type`
- `referenced_preflight_ids`
- `referenced_gate_ids`
- `reasons`
- `blocking_reasons`
- `warnings`

## Allowed flag policy

- `apply_execution_allowed = false` by default
- `rollback_execution_allowed = false` by default
- `writer_execution_allowed = false` by default
- `persistence_execution_allowed = false` by default
- `true` remains future-only and requires explicit implementation approval

## Fail-closed policy

- missing input -> blocked
- invalid approval -> blocked
- stale lineage -> blocked
- mismatch -> blocked
- forbidden key -> blocked
- ambiguous `execution_preflight_type` -> blocked
- missing rollback readiness for apply -> blocked
- missing gate dependency for persistence -> blocked

## Non-goals

- no actual persistence
- no file write / DB write
- no directory creation
- no index append
- no patch apply / revision apply
- no rollback execution
- no persona source mutation
- no model API call
- no runtime behavior change
- no backend forwarding payload change

## Suggested implementation order

1. approval artifact dry-run generator
2. freshness checker dry-run
3. apply gate dry-run
4. rollback gate dry-run
5. storage writer gate dry-run
6. persistence execution gate dry-run
7. summary docs update

## Next phase

- approval artifact dry-run generator design or implementation
- freshness checker dry-run design or implementation
- then gate dry-run CLI implementation in small PRs
