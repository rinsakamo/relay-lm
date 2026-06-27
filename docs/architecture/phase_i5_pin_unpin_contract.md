---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase_i5_pin_unpin_contract_and_read_only_preflight
relaylm_status: i5a_contract_preflight_complete_after_pr
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - I-5B apply lands
  - Pin / Unpin retrieval-ranking policy lands
  - SOUL Lab Pin / Unpin API or UI lands
relaylm_related_authority:
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4_primary_mem_forget_hide_contract.md
  - phase_i4b_primary_current_state_shared_fence.md
  - phase_i4c1_primary_forget_hidden_successor.md
  - phase_i4c2_primary_forget_recovery_finalization.md
  - phase_i4d_primary_retrieval_exclusion.md
  - wave3_cross_slice_convergence_audit.md
  - post_i3_evaluation_work_roadmap.md
---
# Phase I-5 Pin / Unpin Contract and Read-Only Preflight

## Status and boundary

Phase I-5A defines the Pin / Unpin governance contract and adds a runtime read-only preflight boundary. It is complete only at the contract/preflight/token-validation boundary after the I-5A PR lands.

I-5A does **not** implement Pin apply, Unpin apply, SOUL Lab API, SOUL Lab UI, M2 ranking changes, retrieval priority changes, physical page mutation, index/log mutation, hidden successor creation, tombstone creation, or durable Pin state. Apply remains unimplemented and is intentionally handed to later I-5B+ work.

The bounded I-5A path is:

```text
real current active Primary MEM
  -> current-state resolver reread
  -> shared mutation fence check
  -> read-only Pin or Unpin preflight
  -> bounded effect preview
  -> short-lived apply-token shaped contract
  -> zero-item read-only history projection
  -> no mutation
```

## Canonical terminology

- **Pin**: a future governance operation that marks one current active Primary MEM as pinned.
- **Unpin**: a future governance operation that removes that pinned marker.
- **pinned**: target Pin state that may later inform a priority-hint contract.
- **unpinned**: target Pin state after Unpin, or the assumed starting state for Pin preflight.
- **Pin state is orthogonal to lifecycle**: lifecycle determines retrieval eligibility before Pin state can have any effect.

## State model

```text
lifecycle_state:
  active | hidden

mutation_state:
  none | prepared | recovery_required | corrupt

pin_state:
  unpinned | pinned | unknown

retrieval_eligible:
  governed by lifecycle/current-state gates
```

I-5A has no durable Pin state reader. Therefore Pin preflight treats the operation as a contract from `unpinned -> pinned`, and Unpin preflight treats the operation as a contract from `pinned -> unpinned`. Both results explicitly report `pin_state_contract_only: true`.

Pin state never overrides lifecycle state. Hidden, prepared, recovery-required, corrupt, ambiguous, cross-scope, prior physical revision, stale revision, and non-current targets fail closed.

## Identity and revision requirements

A Pin or Unpin preflight target must be exactly:

```text
character_id: exact caller-provided character scope
namespace: exact RelayMEM namespace
memory_id: logical Primary MEM id
expected_revision: current physical revision
lifecycle_state: active
mutation_state: none
controls/page: valid
retrieval_eligible: true before any future Pin policy is considered
```

The resolver must reread current state through the shared Primary current-state authority. A stale revision is rejected with a bounded `stale_revision` code. Hidden current state is rejected as `target_not_active`. Corrupt, ambiguous, unsafe, or invalid targets are rejected as `target_corrupt`. Prepared and recovery-required mutation states fail closed with `operation_conflict` or `recovery_required`.

## Shared mutation fence and concurrency

Pin / Unpin are governance mutations even though I-5A does not apply them. Their preflight and token validation must respect the same per-memory operation fence used by Correct and Forget.

I-5A checks the shared mutation coordinator inspection and rejects:

- corrupt mutation directories;
- a pending Correct or Forget operation;
- reuse of an existing Correct or Forget operation id;
- any conflicting operation evidence for the same memory.

Expected concurrency outcomes:

```text
Correct preflight at N, Pin preflight at N:
  both read-only tokens may exist; the first future apply wins through the shared fence.

Forget applies before Pin apply:
  Pin token validation fails as stale_revision or target_not_active.

Pin preflight then Correct applies:
  Pin token validation fails as stale_revision.

Hidden target:
  Pin/Unpin preflight fails as target_not_active.

Prepared or recovery_required target:
  Pin/Unpin preflight fails as operation_conflict or recovery_required.

Corrupt or ambiguous target:
  Pin/Unpin preflight fails as target_corrupt.

Cross-scope target:
  Pin/Unpin preflight fails as target_not_found or target_not_found_or_wrong_scope at the API translation boundary.
```

Because I-5A has no apply route, these outcomes are proven by read-only preflight and read-only token validation only.

## Schema anchors

Pin request / response / apply-target / history:

```text
relaylm.lab.memory_pin_preflight_request.v0
relaylm.lab.memory_pin_preflight.v0
relaylm.lab.memory_pin_apply_request.v0
relaylm.lab.memory_pin_history.v0
relaylm.primary_pin_apply_token.v0
```

Unpin request / response / apply-target / history:

```text
relaylm.lab.memory_unpin_preflight_request.v0
relaylm.lab.memory_unpin_preflight.v0
relaylm.lab.memory_unpin_apply_request.v0
relaylm.lab.memory_unpin_history.v0
relaylm.primary_unpin_apply_token.v0
```

The `*_apply_request.v0` anchors are target contracts only. I-5A does not expose or implement apply routes.

## Preflight response shape

The I-5A runtime boundary returns a public, content-bounded shape:

```text
schema
status = ready
operation_kind = pin | unpin
read_only = true
memory_id
current_revision
current_lifecycle_state = active
current_mutation_state = none
current_pin_state = unpinned | pinned     # contract assumption
target_pin_state = pinned | unpinned
pin_state_contract_only = true
effects
apply_token
expires_at
```

Pin effect preview:

```text
ordinary_retrieval_deleted: false
ordinary_retrieval_excluded: false
future_priority_hint_contract: true
semantic_content_changed: false
physical_deletion: false
audit_evidence_retained: true
```

Unpin effect preview:

```text
ordinary_retrieval_deleted: false
ordinary_retrieval_excluded: false
future_priority_hint_removed_contract: true
semantic_content_changed: false
physical_deletion: false
audit_evidence_retained: true
```

These previews do not promise an actual M2 ranking change in I-5A.

## Apply-token shaped contract

I-5A issues short-lived opaque Pin / Unpin apply-token shaped artifacts. They are runtime-private validation contracts, not durable apply evidence. Token validation is read-only and rechecks exact character id, namespace, logical memory id, current revision, operation id, operation kind, reason digest binding without exposing reason text, active lifecycle, `none` mutation state, shared mutation fence availability, and token expiry.

The public token payload must not expose token claims such as physical id or binding digest. Public validation output must not expose reason text, namespace private value, physical id, store path, page digest, prepared artifacts, tombstones, queue/job/dispatch/claim identity, or raw exceptions.

## History projection

I-5A history is read-only and zero-item until a later apply phase defines durable Pin / Unpin artifacts:

```text
schema = relaylm.lab.memory_pin_history.v0 | relaylm.lab.memory_unpin_history.v0
source = relaylm_runtime
read_only = true
memory_id
current_revision
current_lifecycle_state
pin_state_contract_only = true
pin_count | unpin_count = 0
items = []
```

## Later apply handoff

I-5B+ may implement Pin / Unpin apply only if it preserves this contract:

- use the same current-state resolver and shared mutation fence;
- validate the exact I-5A token bindings;
- write runtime-private audit evidence without semantic content leakage;
- keep Pin state orthogonal to lifecycle;
- never make hidden memories retrievable;
- never bypass character/namespace isolation;
- define explicit retrieval-ranking behavior before M2 priority changes are introduced.

## Non-goals

I-5A explicitly does not implement Pin apply, Unpin apply, SOUL Lab Pin / Unpin API, SOUL Lab Pin / Unpin UI, durable Pin state persistence, M2 ranking changes, hidden memory retrieval, Forget override or restore/unhide behavior, semantic memory content creation, physical deletion, or new queue, worker, scheduler, or durable-finalization authority.
