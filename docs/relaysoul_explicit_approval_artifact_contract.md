# RelaySOUL Explicit Approval Artifact Contract

## Scope

This document defines a future content-free approval artifact used by apply / rollback / storage writer / persistence execution gates.

- docs-only contract
- no implementation in this phase

## Current state

- gate design docs exist
- all allowed flags remain `false` by default
- actual persistence / apply / rollback are not implemented
- explicit approval artifact format is still future work until this contract

## Approval artifact purpose

- represent explicit user/operator approval as metadata
- bind approval to a specific gate target
- bind approval to a specific artifact chain / lineage
- avoid embedding persona / memory / patch / prompt / model response body

## Suggested artifact shape

- `artifact_type: relaysoul_explicit_approval_artifact`
- `schema_version: mvp-soul-0`
- `content_free: true`
- `approval_status: approved | blocked`
- `approval_scope: apply_execution | rollback_execution | storage_writer | persistence_execution`
- `approval_id`
- `approver_kind: user | operator | system_test`
- `approved_at`
- `target_gate_artifact_type`
- `target_artifact_kind`
- `target_artifact_id`
- `parent_artifact_id`
- `character_id`
- `execution_preflight_type: apply | rollback | null`
- `referenced_preflight_ids`
- `referenced_gate_ids`
- `approval_reason_codes`
- `blocking_reasons`
- `warnings`

## Required content-free constraints

- no persona text
- no memory text
- no patch text
- no prompt text
- no model request / response body
- no raw file content
- no user free-text body unless separately classified as metadata-only

## Required gate checks

- approval artifact `content_free` must be true
- `approval_status` must be `approved`
- `approval_scope` must match target gate
- `approval_id` must be non-empty
- `character_id` / `artifact_id` / `parent_artifact_id` must match target chain
- referenced preflight/gate IDs must match expected chain
- approval must not be stale
- `blocking_reasons` must be empty
- forbidden content keys must be absent

## Fail-closed policy

- missing approval -> blocked
- `approval_status != approved` -> blocked
- scope mismatch -> blocked
- id/path/lineage mismatch -> blocked
- stale approval -> blocked
- ambiguous approver -> blocked
- `content_free = false` -> blocked
- forbidden key present -> blocked

## Relationship to gate docs

- apply gate requires apply-scoped approval
- rollback gate requires rollback-scoped approval
- storage writer gate requires writer-scoped approval
- persistence execution gate requires persistence-scoped approval
- approval for one gate does not imply approval for another gate

## Non-goals

- no actual approval UI
- no authentication implementation
- no persistence write
- no apply / rollback execution
- no runtime behavior change
- no backend forwarding payload change

## Next phase

- stale preflight / lineage freshness policy docs
- gate dry-run CLI design
- future approval artifact dry-run generator
- real persistence / apply / rollback only after explicit approval and fail-closed checks
