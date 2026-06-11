# RelaySOUL Artifact Persistence Contract

This contract defines a content-free dry-run validator for artifact persistence readiness.

## Terminology boundaries

- RelaySOUL artifact: versioned persona-source governance artifact used for preflight/storage contracts.
- runtime compiled context: per-request RelayCTX output prompt payload (not a RelaySOUL artifact).
- memory record: RelayMEM-side memory datum/candidate (not a RelaySOUL artifact).
- RAG document: retrieval corpus unit (not a RelaySOUL artifact).
- trace log: observability/debug record (not a RelaySOUL artifact).
- `STABLE_MEMORY_SUMMARY.md`: profile-facing summary artifact consumed by persona/context assembly; not the underlying memory DB.
- content-free artifact: artifact constrained to metadata/lineage/status fields only, with no persona/memory/patch body payload content.

RelaySOUL versions persona-source artifacts. RelaySOUL does not store runtime compiled prompts as canonical SOUL artifacts.

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

## Stage term separation

- approval: decision artifact about whether a candidate may proceed.
- preflight: dry-run verification stage before any real execution.
- gate: explicit allow/deny control point for apply/rollback execution.
- apply: real mutation path (out of scope in this dry-run contract).
- rollback: real reversal path (out of scope in this dry-run contract).


## Storage envelope dry-run helper

`build_relaysoul_storage_envelope_dry_run(...)` is a dry-run helper that wraps existing content-free artifacts into a storage envelope dictionary for validation before any real persistence implementation.

- no file write
- no DB write
- no path creation
- no runtime mutation

The helper fail-closes when payload content-free assertions are violated.
