# RelaySOUL Artifact Persistence Contract

This contract defines a content-free dry-run validator for artifact persistence readiness.

## Goal

Before any persistence implementation, RelaySOUL should validate artifact lineage and status fields in a consistent, auditable way.

## Supported artifact kinds

- `patch_dry_run`
- `patch_compile_dry_run`
- `rollback_summary`
- `approval_summary`

## Artifact ID and parent ID extraction

- `patch_dry_run`
  - `artifact_id`: `artifact.candidate.candidate_id`
  - `parent_artifact_id`: `None`
- `patch_compile_dry_run`
  - `artifact_id`: `artifact.patch_candidate_id`
  - `parent_artifact_id`: `artifact.patch_candidate_id`
  - missing/empty `patch_candidate_id` emits `missing_artifact_id` blocking and `missing_parent_artifact_id` warning
- `rollback_summary`
  - `artifact_id`: `artifact.revision.revision_id`
  - `parent_artifact_id`: `artifact.revision.parent_revision_id`
  - missing/empty `parent_revision_id` emits `missing_parent_artifact_id` warning
- `approval_summary`
  - `artifact_id`: `artifact.revision_id` if present, else `artifact.patch_candidate_id`
  - `parent_artifact_id`: `artifact.patch_candidate_id`
  - missing/empty `patch_candidate_id` emits `missing_parent_artifact_id` warning

## Status handling

Blocked or warning source artifacts (including `compile_dry_run_status`) can still be marked persistence-ready for audit if no persistence-contract blocking rule is violated.

## Safety constraints

This MVP-15A contract is dry-run-only:

- no actual persistence
- no file write
- no DB write
- no patch apply
- no revision apply
- no rollback execution
- no model call
- no persona/memory/patch body content
