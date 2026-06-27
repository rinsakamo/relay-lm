---
relaylm_doc_type: contract
relaylm_authority: phase_i4_primary_mem_forget_hide
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_soul_lab_integration
relaylm_update_trigger:
  - Primary MEM lifecycle or current-state resolution changes
  - Forget preflight apply or history schema changes
  - correction and Forget mutation fencing changes
  - M2 retrieval eligibility or historical used-memory projection changes
  - Phase I-4E/I-4F product surface or validation status changes
relaylm_not_authoritative_for:
  - repository-wide current Forget runtime availability
  - non-retrieval archival policy
  - Pin Merge Held Secondary MEM or RelaySOUL mutation contracts
  - queue scheduling worker supervision or I1-G durability
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4b_primary_current_state_shared_fence.md
  - phase_i4c1_primary_forget_hidden_successor.md
  - phase_i4c2_primary_forget_recovery_finalization.md
  - phase_i4d_primary_retrieval_exclusion.md
  - phase_i4e_forget_api_ui.md
  - phase_i4f_forget_validation.md
  - memory_lifecycle_design.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_current_target.md
  - pipeline_implementation_plan.md
  - post_i3_evaluation_work_roadmap.md
  - wave3_cross_slice_convergence_audit.md
  - wave4_cross_slice_convergence_audit.md
  - wave5_cross_slice_convergence_audit.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i2_real_soul_lab_observation.md
---
# Phase I-4A: Auditable Primary MEM Forget / Hide Contract

Last reviewed: 2026-06-27 JST

## 1. Status

**Current master contract. Phase I-4 is complete through I-4F.** Repository-wide implementation status lives in [Project Status](../PROJECT_STATUS.md). This document owns the stable lifecycle, identity, persistence, concurrency, API, audit, recovery, and retrieval-exclusion contract for Forget / Hide; it is not the single current completion tracker for each downstream sub-slice.

Implemented Phase I-4 sub-slices:

```text
I-4B  canonical read-only current-state resolver, shared mutation fence,
      read-only Forget preflight, five-minute token validation, bounded history
I-4C1 exact intent preparation, shared revision claim, deterministic hidden
      successor publication through M3e, canonical reread
I-4C2 exact prepared resume, operation-scoped M3f/M3g convergence,
      response-loss replay, tombstone finalization
I-4D  ordinary M2/RelayCTX lifecycle and prior-revision exclusion plus
      historical lifecycle overlay
I-4E  loopback-only Forget API and SOUL Lab Forget UI
I-4F  crash/race/security/fresh-conversation validation and product-completion proof
```

Phase I-3 Correct remains the implemented mutation baseline. Phase I-4 must not introduce a weaker scope check, revision fence, token, idempotency, persistence, recovery, or mutation-access boundary.

## 2. Purpose

Phase I-4 lets a user explicitly stop one current active formed Primary MEM from participating in normal future retrieval while preserving durable audit and historical evidence:

```text
real current active Primary MEM
  -> read-only Forget preflight
  -> bounded effect preview
  -> explicit short-lived-token confirmation
  -> revision-fenced authoritative lifecycle transition
  -> page/index/log and retrieval-exclusion convergence
  -> immutable Forget tombstone
  -> later fresh ordinary managed turn
  -> existing M2 excludes the logical memory
  -> RelayCTX receives no representation of it
```

The contract guarantees that a forgotten memory is retrieval-ineligible, prior physical revisions cannot reappear as candidates, past used-memory evidence remains truthful, and character/namespace boundaries do not change.

## 3. Current foundation

The implementation provides exact character, namespace, physical identity, and revision validation; read-only preflight separated from explicit token-gated apply; per-memory lock, pending-operation fence, and operation-level idempotency; M3e publication plus M3f/M3g index-before-log convergence; immutable historical Phase I-2 used-memory evidence; I-4D ordinary M2/RelayCTX lifecycle filtering before snippet and backend-bound construction; I-4E loopback API/UI; and I-4F validation of crash, race, security, and fresh-conversation behavior.

## 4. Scope

In scope: one current active formed Primary MEM, one explicit user-facing Forget operation, one immutable hidden successor revision, one runtime-private prepared artifact, one immutable Forget tombstone, one shared current-state resolver, exact preflight/apply/history schemas, crash-safe convergence, normal M2 and RelayCTX exclusion, and historical used-memory integrity.

Out of scope: restore/unhide, purge, batch mutation, cross-character mutation, Secondary MEM consolidation, RelaySOUL mutation, queue scheduling, worker supervision, and I1-G durability semantics.

## 5. Canonical terminology

| Term | Canonical meaning |
|---|---|
| **Forget** | Explicit user operation targeting one exact current active logical memory. |
| **`hidden`** | Durable current lifecycle state produced by successful Forget. Hidden memory is not retrieval-eligible. |
| **Forget tombstone** | Immutable runtime-private audit/recovery artifact proving the exact active-to-hidden transition and convergence. |
| **`active`** | Canonical lifecycle state eligible for ordinary retrieval when all other M2 gates pass. |
| **prepared** | Runtime-private operation state after exact intent is durable but before full convergence. |

“Hide” may remain in the phase nickname, but it is not a second operation.

## 6. Lifecycle state machine

The canonical resolver returns orthogonal lifecycle and mutation dimensions:

```text
schema: relaylm.mem.primary_current_state.v0
lifecycle_state: active | hidden
mutation_state: none | prepared | recovery_required | corrupt
retrieval_eligible: true | false
```

Normal transition:

```text
revision N active / none / eligible
  -> read-only preflight
  -> exact prepared operation; revision N quarantined
  -> revision N+1 hidden successor published through M3e
  -> index applied / log pending when interrupted
  -> index/log converged and exclusion verified
  -> Forget tombstone finalized
  -> hidden / none / ineligible
```

The hidden-successor publication is the lifecycle commit point. A valid prepared operation is fail-closed. A hidden lifecycle commit never rolls back to active because tombstone finalization or HTTP response delivery failed.

| Condition | Resolver result | Retrieval behavior | Required action |
|---|---|---|---|
| preflight only | `active / none` | eligible | no recovery |
| prepared artifact only | `active / prepared` | excluded | resume exact operation or bounded conflict |
| hidden successor published | `hidden / recovery_required` | excluded | resume M3f/M3g convergence |
| index applied, log pending | `hidden / recovery_required` | excluded | apply only the missing log step and then finalize tombstone |
| controls converged, tombstone missing | `hidden / recovery_required` | excluded | verify exclusion and finalize tombstone |
| tombstone finalized | `hidden / none` | excluded | return applied result |
| invalid or ambiguous chain | `unknown-or-hidden / corrupt` | excluded | fail closed |

Repeated Forget outcomes are distinct: exact replay returns the original applied result, a different operation targeting canonical hidden state returns `already_hidden`, and changed revision/physical identity/lifecycle/reason/binding returns `stale_revision` or `operation_conflict`.

## 7. Identity and revision model

Forget preserves the stable logical `memory_id` and advances the canonical revision exactly once:

```text
revision 1 active
  -> Correct
revision 2 active
  -> Forget
revision 3 hidden
```

The hidden successor is the canonical current physical page. Prior pages remain immutable audit evidence and are neither current nor retrieval-eligible. Forget does not create new semantic assertions; the bounded user reason remains runtime-private audit content. No Correct and Forget operation may both consume the same current revision.

## 8. Persistence decision

Phase I-4 uses immutable successor Primary pages plus lifecycle metadata `hidden`, monotonically increasing revision, existing M3e/M3f/M3g convergence, and runtime-private prepared/tombstone artifacts. The hidden successor page is lifecycle authority. The tombstone is audit/recovery evidence, not an independent sidecar current-state flag. A bare sidecar boolean such as `hidden=true` is forbidden as the sole or independently committed current-state mechanism.

## 9. Correct / Forget concurrency

One narrow Primary mutation coordinator owns the existing per-memory lock namespace, pending-operation fence, operation lookup, current-state resolution, and revision claim. It does not become a generic mutation framework.

| Starting condition | Operation A | Operation B | Required outcome |
|---|---|---|---|
| revision 1 active | Forget | none | revision 2 hidden |
| corrected revision N active | Forget | none | revision N+1 hidden |
| Correct preflight at N | Forget applies first | Correct apply | Forget wins; Correct `stale_revision` |
| Forget preflight at N | Correct applies first | Forget apply | Correct wins; Forget `stale_revision` |
| active N | concurrent different Forget operations | concurrent apply | one commit owner; loser stale/conflict |
| hidden N | exact prior replay | none | same result; no new revision |
| hidden N | new Forget | none | `already_hidden` |
| hidden N | Correct or future Pin | none | `target_not_active` |
| hidden source | future Merge or consolidation | none | ineligible; fail closed |

## 10. Retrieval exclusion

I-4D consumes the shared current-state resolver before snippet construction. A candidate remains eligible only when M2 selected it and the current-state reread proves:

```text
active + mutation none + canonical current physical revision
  + converged controls + valid scope/page -> eligible
hidden                                      -> excluded
prepared or recovery_required               -> excluded fail-closed
corrupt or ambiguous lifecycle chain        -> excluded fail-closed
unsafe or cross-scope candidate              -> excluded fail-closed
prior physical revision                      -> excluded
```

A hidden current successor never allows fallback to a prior active revision. Filtered content must not remain in selected candidates, snippets, evidence envelopes, RelayCTX, or backend-bound messages. Historical used-memory receipts remain immutable; I-4D adds the separate read-only `relaylm.lab.memory_used_lifecycle.v1` overlay.

## 11. API and product surface

The implemented loopback routes follow the Phase I-3 style:

```text
POST /lab/api/characters/{character_id}/memory/{memory_id}/forget/preflight?namespace=...
POST /lab/api/characters/{character_id}/memory/{memory_id}/forget?namespace=...
GET  /lab/api/characters/{character_id}/memory/{memory_id}/forget-history?namespace=...
```

Schema anchors:

```text
relaylm.lab.memory_forget_preflight_request.v0
relaylm.lab.memory_forget_apply_request.v0
relaylm.lab.memory_forget_history.v0
```

I-4E owns the loopback-only mutation API and SOUL Lab Forget preflight/confirm/refusal/conflict/receipt UI. It consumes I-4B current-state/token authority, I-4C1/I-4C2 mutation/recovery authority, and I-4D read-only lifecycle result. It does not own the retrieval filtering algorithm, restore, or purge.

I-4F owns fresh-conversation exclusion validation, crash/race/security validation, and product-level Forget completion proof. It does not add mutation authority.

## 12. Fault matrix

| Interruption point | Required resolver result | Required recovery behavior |
|---|---|---|
| after prepared artifact | `active / prepared / false` | exact resume or bounded conflict; retrieval remains fail-closed |
| after hidden successor | `hidden / recovery_required / false` | resume M3f/M3g convergence for the same operation |
| after index / before log | `hidden / recovery_required / false` | apply only the missing log step and then finalize tombstone |

The fault matrix is current implementation evidence for I-4C1/I-4C2/I-4D/I-4E/I-4F boundaries. It does not authorize automatic repair outside the exact operation authority.

## 13. Implemented sub-slices

```text
I-4B — complete read-only boundary
I-4C1 — complete hidden-successor commit ownership
I-4C2 — complete exact replay and forward recovery
I-4D — complete convergence and exclusion
I-4E — complete loopback wrapper and UI
I-4F — complete production validation
```

## 14. Explicit non-claims

Phase I-4 does not provide restore/unhide, purge, Secondary MEM consolidation, RelaySOUL mutation, scheduler control, worker supervision, automatic repair, Pin/Unpin runtime apply, Held Apply/Discard runtime, or direct Home-origin Primary MEM formation.
