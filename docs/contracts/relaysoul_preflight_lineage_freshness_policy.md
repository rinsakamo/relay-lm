# RelaySOUL Preflight Lineage Freshness Policy

## Scope

This document defines a future policy for deciding whether approval / gate decisions are fresh enough to authorize later execution.

- docs-only policy
- no implementation in this phase

## Current state

- preflight dry-run chain exists through persistence execution preflight
- gate design docs exist
- explicit approval artifact contract exists
- actual persistence / apply / rollback are not implemented

## Freshness purpose

- prevent approval reuse across changed artifact chains
- prevent stale preflight from authorizing actual execution
- bind approval to exact lineage and expected preflight/gate IDs
- preserve content-free boundary

## Lineage fields

- `approval_id`
- `approval_scope`
- `target_gate_artifact_type`
- `target_artifact_kind`
- `target_artifact_id`
- `parent_artifact_id`
- `character_id`
- `execution_preflight_type`
- `referenced_preflight_ids`
- `referenced_gate_ids`
- `artifact_path`
- `artifact_index_path`
- `lineage_index_path`

## Freshness checks

- approval references the current preflight chain
- approval target matches current gate target
- all referenced preflight artifacts are present
- all referenced gate artifacts are present when required
- `artifact_kind` / `target_artifact_id` / `parent_artifact_id` / `character_id` match
- storage path/index lineage matches current path plan
- `execution_preflight_type` matches apply or rollback chain
- no `blocking_reasons`
- all artifacts remain `content_free = true`
- forbidden content keys remain absent

## Stale conditions

- missing referenced artifact
- approval references old preflight IDs
- any `artifact_id` / `parent_artifact_id` / `character_id` mismatch
- any storage path/index mismatch
- any `execution_preflight_type` mismatch
- preflight regenerated after approval without a matching updated approval
- gate decision regenerated after approval without a matching updated approval
- `blocking_reasons` added after approval
- `content_free` changes to false
- forbidden key appears after approval

## Suggested output metadata for future gate decisions

- `lineage_freshness_status: fresh | stale | unknown`
- `freshness_checked_at`
- `referenced_preflight_ids`
- `referenced_gate_ids`
- `stale_reasons`
- `blocking_reasons`
- `content_free: true`

## Fail-closed policy

- unknown freshness -> blocked
- stale freshness -> blocked
- missing lineage field -> blocked
- ambiguous lineage -> blocked
- mismatch -> blocked
- regenerated chain without reapproval -> blocked

## Relationship to explicit approval artifact

- approval must bind to exact target chain
- approval cannot be reused for a different gate scope
- approval cannot be reused after relevant chain regeneration
- approval is necessary but not sufficient; freshness must pass separately

## Relationship to gate designs

- apply gate requires fresh apply-scoped approval
- rollback gate requires fresh rollback-scoped approval
- storage writer gate requires fresh writer-scoped approval
- persistence gate requires fresh persistence-scoped approval and matching writer/apply/rollback gate state

## Non-goals

- no timestamp trust implementation
- no signature/authentication implementation
- no actual persistence
- no file write / DB write
- no apply / rollback execution
- no runtime behavior change

## Next phase

- gate dry-run CLI design
- approval artifact dry-run generator design
- freshness checker dry-run design
- real persistence / apply / rollback only after explicit approval, freshness, and fail-closed checks
