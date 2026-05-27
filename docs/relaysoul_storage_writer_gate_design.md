# RelaySOUL Storage Writer Gate Design

## Scope

This document defines a future gate design for moving from storage writer preflight dry-run to actual storage write / index append.

- docs-only design
- no implementation in this phase

## Current state

- storage writer preflight exists
- persistence execution preflight exists
- `writer_execution_allowed` is currently `false`
- `persistence_execution_allowed` is currently `false`
- actual file write / DB write / index append / mkdir are not implemented

## Gate inputs

- storage envelope
- storage path plan
- storage index plan
- apply execution preflight or rollback execution preflight
- storage writer preflight
- persistence execution preflight
- explicit user/operator approval artifact or equivalent future approval decision

## Required gate conditions

- all artifacts must have `content_free = true`
- all statuses must be `ready` / `ok`
- no `blocking_reasons`
- ID/path consistency across all artifacts
- `artifact_kind` / `artifact_id` / `parent_artifact_id` / `character_id` must match
- `artifact_path` / `artifact_index_path` / `lineage_index_path` must match expected paths
- `artifact_index_record` and `lineage_index_record` identity fields must match path plan
- forbidden content keys must be absent at top-level, payload, and nested records
- unsafe identity must be rejected
- explicit user/operator approval is required
- dry-run chain must be reproducible before actual write
- persistence execution preflight must remain ready

## Storage writer gate output concept

- `artifact_type: relaysoul_storage_writer_gate_decision`
- `gate_status: blocked | ready`
- `writer_execution_allowed: false` by default
- `writer_execution_allowed` may become true only in a future implementation after explicit approval
- `content_free: true`
- `reasons` / `blocking_reasons` are metadata-only

## Non-goals

- no actual file write
- no DB write
- no directory creation
- no index append
- no patch apply / revision apply
- no rollback execution
- no persona source mutation
- no model API call
- no runtime behavior change

## Fail-closed policy

- missing artifact -> blocked
- any `content_free = false` -> blocked
- any mismatch -> blocked
- any forbidden key -> blocked
- ambiguous approval -> blocked
- stale preflight -> blocked
- missing expected path -> blocked
- lineage/index record mismatch -> blocked

## Relationship to apply / rollback

- apply and rollback gates are separate
- storage writer gate only covers artifact persistence/write readiness
- storage writer approval is not equivalent to apply or rollback approval
- actual apply / rollback must remain separately gated

## Next phase

- persistence execution gate design docs
- apply/rollback/storage writer gate docs consistency review
- future gate dry-run CLI only after docs are stable
- actual storage writer only after explicit approval and fail-closed checks
