# RelaySOUL Rollback Execution Gate Design

## Scope

This document defines a future gate design for moving from rollback execution preflight dry-run to actual rollback.

- docs-only design
- no implementation in this phase

## Current state

- rollback execution preflight exists
- storage writer preflight exists
- persistence execution preflight exists
- `rollback_execution_allowed` is currently `false`
- `persistence_execution_allowed` is currently `false`

## Gate inputs

- approval decision artifact
- apply plan dry-run artifact
- rollback plan dry-run artifact
- storage envelope
- storage path plan
- storage index plan
- rollback execution preflight
- storage writer preflight
- persistence execution preflight

## Required gate conditions

- all artifacts must have `content_free = true`
- all statuses must be `ready` / `ok`
- no `blocking_reasons`
- ID/path consistency across all artifacts
- `artifact_kind` / `artifact_id` / `parent_artifact_id` / `character_id` must match
- rollback plan must point to the apply plan it reverses
- rollback preflight must match rollback plan and storage path/index artifacts
- forbidden content keys must be absent
- nested index record forbidden keys must be absent
- unsafe identity must be rejected
- explicit user/operator approval is required
- dry-run chain must be reproducible before actual rollback

## Rollback gate output concept

- `artifact_type: relaysoul_rollback_execution_gate_decision`
- `gate_status: blocked | ready`
- `rollback_execution_allowed: false` by default
- `rollback_execution_allowed` may become true only in a future implementation after explicit approval
- `content_free: true`
- `reasons` / `blocking_reasons` are metadata-only

## Non-goals

- no actual rollback execution
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
- rollback/apply lineage mismatch -> blocked

## Relationship to apply

- apply execution gate is separate
- rollback readiness is required before actual apply can be considered safe
- rollback approval is not implied by apply approval
- rollback gate must be independently approved before actual rollback

## Next phase

- storage writer gate design docs
- gate dry-run CLI only after docs are stable
- actual rollback only after explicit approval and fail-closed checks
- real apply / persistence remain separate gate phases
