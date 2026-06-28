---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase_i5_pin_unpin_contract_and_preflight
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - I-5B apply behavior changes
  - Pin / Unpin retrieval-ranking policy changes
  - SOUL Lab Pin / Unpin API or UI changes
relaylm_related_authority:
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4_primary_mem_forget_hide_contract.md
  - phase_i4b_primary_current_state_shared_fence.md
  - phase_i4d_primary_retrieval_exclusion.md
  - phase_i5b_pin_unpin_apply.md
  - wave6_cross_slice_convergence_audit.md
---
# Phase I-5 Pin / Unpin Contract and Read-Only Preflight

## Status and boundary

I-5A defines the Pin / Unpin governance contract and read-only preflight boundary. I-5B is implemented as the apply/API/UI/ranking continuation. The current runtime apply details live in [Phase I-5B Pin / Unpin apply and ranking behavior](phase_i5b_pin_unpin_apply.md).

I-5A itself remains the token and preflight contract authority. It proves the bounded read-only shape:

```text
real current active Primary MEM
  -> current-state resolver reread
  -> shared mutation fence check
  -> read-only Pin or Unpin preflight
  -> bounded effect preview
  -> short-lived apply-token shaped contract
  -> no mutation in I-5A
```

I-5B consumes this contract to perform explicit token-confirmed apply, durable content-free Pin / Unpin evidence, loopback SOUL Lab API/UI, and deterministic ranking-hint behavior.

## Canonical terminology

- **Pin**: governance operation that marks one current active Primary MEM as pinned.
- **Unpin**: governance operation that removes that pinned marker.
- **pinned**: Pin state that may inform a priority-hint contract.
- **unpinned**: Pin state after Unpin, or the assumed starting state for Pin preflight.
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
retrieval_eligible: true before any Pin policy is considered
```

The resolver must reread current state through the shared Primary current-state authority. A stale revision is rejected with a bounded `stale_revision` code. Hidden current state is rejected as `target_not_active`. Corrupt, ambiguous, unsafe, or invalid targets are rejected as `target_corrupt`. Prepared and recovery-required mutation states fail closed with `operation_conflict` or `recovery_required`.

## Shared mutation fence and concurrency

Pin / Unpin are governance mutations. Their preflight, token validation, and I-5B apply path respect the same per-memory operation fence used by Correct and Forget.

Expected concurrency outcomes:

```text
Correct preflight at N, Pin preflight at N:
  both read-only tokens may exist; the first apply wins through the shared fence.

Forget applies before Pin apply:
  Pin token validation fails as stale_revision or target_not_active.

Pin preflight then Correct applies:
  Pin token validation fails as stale_revision.

Hidden target:
  Pin/Unpin preflight fails as target_not_active.
```

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
current_pin_state = unpinned | pinned
target_pin_state = pinned | unpinned
effects
apply_token
expires_at
```

Pin and Unpin previews do not promise hidden-memory retrieval, semantic content changes, physical deletion, or lifecycle eligibility changes.

## I-5B apply continuation

I-5B preserves this contract by:

- using the same current-state resolver and shared mutation fence;
- validating the exact I-5A token bindings;
- writing runtime-private audit evidence without semantic content leakage;
- keeping Pin state orthogonal to lifecycle;
- never making hidden memories retrievable;
- never bypassing character/namespace isolation;
- defining deterministic retrieval-ranking behavior before M2 priority changes are introduced.

## Non-goals

I-5A/I-5B do not implement hidden memory retrieval, Forget override or restore/unhide behavior, semantic memory content creation, physical deletion, Merge / Supersession, Secondary MEM consolidation, RelaySOUL mutation, or new queue, worker, scheduler, or durable-finalization authority.
