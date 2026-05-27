# RelaySOUL Persistence Execution Gate Design

## Scope

This document defines a future gate design for moving from persistence execution preflight dry-run to actual persistence execution.

- docs-only design
- no implementation in this phase

## Current state

- persistence execution preflight exists
- storage writer preflight exists
- `persistence_execution_allowed` is currently `false`
- `writer_execution_allowed` is currently `false`
- actual persistence / file write / DB write / mkdir / index append are not implemented

## Gate inputs

- storage envelope
- storage path plan
- storage index plan
- apply execution preflight or rollback execution preflight
- storage writer preflight
- persistence execution preflight
- storage writer gate decision
- apply execution gate decision or rollback execution gate decision, depending on `execution_preflight_type`
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
- writer gate must be ready
- apply or rollback gate must be ready according to `execution_preflight_type`
- explicit user/operator approval is required
- dry-run chain must be reproducible before actual persistence

## Persistence gate output concept

- `artifact_type: relaysoul_persistence_execution_gate_decision`
- `gate_status: blocked | ready`
- `execution_preflight_type: apply | rollback`
- `persistence_execution_allowed: false` by default
- `persistence_execution_allowed` may become true only in a future implementation after explicit approval
- `content_free: true`
- `reasons` / `blocking_reasons` are metadata-only

## Non-goals

- no actual persistence
- no file write
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
- storage writer gate not ready -> blocked
- apply/rollback gate not ready -> blocked
- `execution_preflight_type` mismatch -> blocked

## Relationship to apply / rollback / writer gates

- persistence gate is separate from apply, rollback, and storage writer gates
- storage writer approval is required but not sufficient for persistence approval
- apply or rollback gate readiness is required depending on `execution_preflight_type`
- persistence approval is not equivalent to apply or rollback approval
- actual apply / rollback must remain separately gated

## Next phase

- apply/rollback/storage writer/persistence gate docs consistency review
- future gate dry-run CLI only after docs are stable
- actual persistence writer only after explicit approval and fail-closed checks
- real apply / rollback remain separate gate phases
