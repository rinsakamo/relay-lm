# RelaySOUL Apply Execution Gate Design

## Scope

This document defines a future gate design for moving from apply execution preflight dry-run to actual apply.

- docs-only design
- no implementation in this phase

## Current state

- apply execution preflight exists
- storage writer preflight exists
- persistence execution preflight exists
- `apply_execution_allowed` is currently `false`
- `persistence_execution_allowed` is currently `false`

## Gate inputs

- approval decision artifact
- apply plan dry-run artifact
- storage envelope
- storage path plan
- storage index plan
- apply execution preflight
- storage writer preflight
- persistence execution preflight

## Required gate conditions

- all artifacts must have `content_free = true`
- all statuses must be `ready` / `ok`
- no `blocking_reasons`
- ID/path consistency across all artifacts
- `artifact_kind` / `artifact_id` / `parent_artifact_id` / `character_id` must match
- forbidden content keys must be absent
- nested index record forbidden keys must be absent
- unsafe identity must be rejected
- explicit user/operator approval is required
- dry-run chain must be reproducible before actual apply

## Apply gate output concept

- `artifact_type: relaysoul_apply_execution_gate_decision`
- `gate_status: blocked | ready`
- `apply_execution_allowed: false` by default
- `apply_execution_allowed` may become true only in a future implementation after explicit approval
- `content_free: true`
- `reasons` / `blocking_reasons` are metadata-only

## Non-goals

- no actual patch apply
- no revision apply
- no persona source mutation
- no file write
- no DB write
- no model API call
- no runtime behavior change

## Fail-closed policy

- missing artifact -> blocked
- any `content_free = false` -> blocked
- any mismatch -> blocked
- any forbidden key -> blocked
- ambiguous approval -> blocked
- stale preflight -> blocked

## Relationship to rollback

- rollback execution gate must be separate
- apply gate must require rollback plan/preflight availability before actual apply
- rollback readiness is a prerequisite but not a substitute for apply approval

## Next phase

- rollback execution gate design docs
- storage writer gate design docs
- future gate dry-run CLI only after docs are stable
- actual apply only after explicit approval and fail-closed checks
