---
relaylm_doc_type: implementation_plan
relaylm_authority: planned_post_i3_work_and_evaluation_sequence
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - a post-I3 product slice begins or lands
  - SOUL Lab real conversation integration changes state
  - I1-G or worker-service sequencing changes
  - an evaluation gate changes state
relaylm_not_authoritative_for:
  - current runtime implementation status
  - exact mutation schemas
  - exact queue or worker contracts
  - RelaySOUL revision schema
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - pipeline_implementation_plan.md
  - phase_i4_primary_mem_forget_hide_contract.md
  - phase_i4b_primary_current_state_shared_fence.md
  - phase_i4c1_primary_forget_hidden_successor.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - o1a_two_lane_scheduler_contract.md
---
# Post-I3 Evaluation and Work Roadmap

Last reviewed: 2026-06-26 JST

## Purpose

Phase I-3 Correct, UI-B0 real Home conversation, O0 local one-job execution, I1-GA/GB/GC, I-4B, I-4C1, and O1A are complete at their bounded boundaries. Phase I-4A remains the target Forget / Hide contract. I1-GD/GE, I-4C2 through I-4F, and O1B through O1F remain incomplete.

This roadmap separates four authorities:

```text
Memory governance
  -> Forget, Pin, Held review, Merge
  -> Secondary MEM and RelaySOUL

SOUL Lab experience
  -> real Home conversation
  -> lifecycle and operation visibility
  -> repeatable evaluation evidence

Durability
  -> pre-release evidence
  -> one-record restart replay and completion
  -> retention and crash proof

Operations
  -> O0 one-job execution
  -> O1A round/idle contract
  -> O1B/O1C bounded production lane adapters
  -> O1D/O1E/O1F policy, recovery, shutdown, validation
  -> O2/O3 supervised and always-on operation
```

## Current completed foundation

Complete:

- ordinary managed Turn 1 Primary MEM formation through C2;
- O0 explicit execution of at most one eligible durable queued job;
- O1A pure replay-before-queue round/idle contract;
- next-turn M2 retrieval and RelayCTX injection;
- character and namespace isolation;
- Phase I-2 real read-only Lab observation;
- Phase I-3 auditable Correct and corrected retrieval;
- UI-B0 bounded non-stream and SSE Home conversation;
- I1-GA durable-finalization contract and fault model;
- I1-GB bounded base/segment/seal publication before protected visible release;
- I1-GC caller-selected one-record replay, exact C1-5/B2 convergence, duplicate suppression, and immutable completion marker;
- I-4B canonical current-state resolver, shared Correct/Forget fence, preflight, token validation, and zero-item history;
- I-4C1 exact Forget prepare, hidden successor, M3e commit, and hidden/recovery-required resolution.

Defined target:

- Phase I-4A Forget / Hide lifecycle, persistence, concurrency, recovery, API, and retrieval-exclusion contract.

Unimplemented:

- I1-GD retention/orphan reconciliation/cleanup and I1-GE full crash validation;
- I-4C2 through I-4F recovery/tombstone, M2 exclusion, API/UI, and validation;
- O1B through O1F automatic bounded scheduling;
- O2 supervised worker operation;
- O3 always-on local operation.

## Proven E1 boundary

The first local E1 result is proven through two separate lanes:

```text
formation lane
  explicit trusted scene-qualified managed request
    -> durable protected source and queue publication
    -> O0 one-job execution
    -> Primary MEM formation
    -> Phase I-2 observation
    -> Phase I-3 Correct when required

recall lane
  SOUL Lab Home real conversation
    -> existing M2 / RelayCTX recall
    -> fresh browser-local conversation
    -> remembered or corrected fact question
    -> Phase I-2 used-memory evidence
```

E1 does not prove direct Home-origin formation because UI-B0 sends standard Chat Completions fields and does not self-assert trusted scene-admission metadata. It also does not prove automatic scheduling.

## Target product loop

```text
SOUL Lab Home real conversation
  -> existing RelayLM managed request
  -> existing M2 retrieval and RelayCTX injection
  -> visible response
  -> I1-GB durable-finalization evidence before protected release
  -> I1-GC exact C1-5/B2 convergence when caller-selected replay is needed
  -> O0 or later O1C queue execution
  -> Primary MEM formed / held / blocked / failed
  -> Phase I-2 observation
  -> explicit memory operation
  -> Home New Conversation
  -> changed retrieval and response behavior
```

## Track A: Memory governance

### Phase I-3: Auditable Correct — complete

Phase I-3 is the mutation baseline: exact scope/current-revision validation, bounded preview, explicit confirmation, durable evidence, immutable successor, M3f/M3g convergence, recovery, exact replay, and later retrieval validation.

### Phase I-4A: Forget / Hide target contract — defined

```text
Forget            user-facing explicit operation
hidden            canonical current retrieval-ineligible lifecycle state
Forget tombstone  immutable runtime-private audit/recovery artifact
```

The hidden successor page is lifecycle authority. The tombstone is audit/recovery evidence.

### Phase I-4B: Current-state resolver and shared mutation fence — complete

I-4B implements `relaylm.mem.primary_current_state.v0`, stable logical/current physical identity, shared Correct/Forget `.lock`, read-only Forget preflight, five-minute exact-binding token validation, zero-item history, and fail-closed `recovery_required` classification.

### Phase I-4C1: Hidden-successor commit — complete

I-4C1 consumes the I-4B token and shared fence, publishes immutable prepared evidence, commits the deterministic hidden page through M3c/M3d/M3e, canonically rereads it, enforces one-winner concurrency, and resolves `hidden / recovery_required / false`.

### Phase I-4C2 through I-4F: Remaining Forget work

```text
I-4C2  prepared resume, exact replay, forward-only recovery,
        tombstone finalization, response-loss convergence
I-4D   index/log convergence, M2/RelayCTX exclusion,
        historical used-memory lifecycle projection
I-4E   loopback API and SOUL Lab confirmation/refusal/conflict/receipt UI
I-4F   fresh-conversation exclusion, security, race, and crash-recovery smoke
```

I-4D is the user-visible semantic commit. Physical deletion, secure erase, purge, restore, and unhide remain separate.

### Phase I-5: Pin / Unpin

```text
I-5A eligibility and priority contract
I-5B atomic pin apply and audit receipt
I-5C unpin convergence
I-5D M2 ranking integration
I-5E SOUL Lab UI
I-5F ranking/budget/isolation/stale-revision smoke
```

### Phase I-7: Held Apply / Discard

```text
I-7A held identity/reason/evidence/expiry contract
I-7B policy/scope/source revalidation
I-7C Apply into authoritative Primary MEM
I-7D Discard into durable reviewed rejection
I-7E optional bounded correction before Apply
I-7F SOUL Lab review UI
I-7G sensitive/contradictory/stale/cross-scope/replay smoke
```

### Phase I-6: Merge / Supersession

```text
I-6A multi-memory eligibility and contradiction preflight
I-6B bounded merged representation and semantic diff
I-6C optimistic concurrency and atomic apply
I-6D source memories marked superseded
I-6E index/log and retrieval de-duplication
I-6F SOUL Lab multi-select and confirmation
I-6G crash/retry/stale/duplicate-retrieval smoke
```

Recommended governance order:

```text
I-5 Pin / Unpin
  -> I-7 Held Apply / Discard
  -> I-6 Merge / Supersession
```

### Phase I-8: Secondary MEM consolidation

Grouping, contradiction/lifecycle analysis, stable summary candidates, SOUL-anchor validation without SOUL mutation, rollback-friendly apply/hold, Secondary-priority retrieval, lineage inspection, and long-horizon smoke.

### Phase I-9: RelaySOUL proposal / intervention / rollback

Proposal identity/evidence/risk, bounded SOUL diff, approval/hold/discard, atomic revision with prior preservation, rollback, Pod UI, fresh-conversation validation, and stale/cross-character/conflict smoke. RelayMEM and RelaySLP may propose; they never mutate SOUL directly.

## Track B: SOUL Lab experience

### UI-B0: Real Home Conversation — complete

Server-owned character/model route resolution, bounded non-stream/SSE transport, Stop/Retry/New Conversation, stale-response fencing, and explicit Real Runtime / Local Preview separation.

### UI-B1: Memory lifecycle visibility — planned

```text
UI-B1A after I-4D and bounded O1 visibility
  conversation/run correlation
  durable-finalization pending / complete
  queued / processing / formed / held / blocked / failed
  active / hidden / recovery-required
  current revision and fresh-conversation verification

UI-B1B after I-5 through I-7
  operation receipts
  pin/unpin state
  merge/supersession lineage
  held apply/discard decisions
```

UI-B1 remains read-only until exact mutation routes separately land.

### UI-B2: Evaluation scenarios and evidence — planned

Required scenarios include correction, forgetting, pinning, held review, merge, Secondary consolidation, SOUL proposal/rollback, restart recovery, and cross-character isolation.

## Track C: Operational work

### O0: Local one-job runner — complete

`relaylm-worker --once --config config.yaml [--character-id CHARACTER_ID]` processes at most one eligible queued record through existing C2 authority and exits.

### I1-G: Pre-enqueue durability — in progress overall

```text
I1-GA contract / fault model                                  complete
I1-GB durable publication / response-release admission       complete
I1-GC one-record replay / exact convergence / completion     complete
I1-GD retention / orphan reconciliation / cleanup            planned
I1-GE production crash-at-every-boundary integration smoke   planned
```

I1-GC does not scan, batch, poll, sleep, retry in a loop, clean up, transition B3, execute workers, or write memory.

### O1A: Two-lane scheduler and idle contract — complete

O1A fixes replay-before-queue ordering, one delegation per lane, independent queue rediscovery, lane-local failure isolation, bounded content-free results, and `stop | run_next_round | idle`. It adds no production scanner or runtime loop.

### O1B through O1F: Production scheduling — unimplemented

```text
O1B  one eligible I1-G sealed-record discovery and I1-GC delegation
O1C  one eligible B2 discovery and O0/C2 delegation
O1D  deterministic ordering, fairness, retry-time, backoff, jitter
O1E  stale-claim recovery, cancellation, graceful shutdown
O1F  corruption, concurrency, saturation, restart, leakage smoke
```

### O2: Supervised worker service — planned

Lifecycle/configuration, bounded concurrency/backpressure, graceful shutdown, health diagnostics, and restart/saturation/repeated-failure smoke.

### O3: Always-on local operation — planned

Local startup/shutdown integration, packaged UI launch, retention/disk-capacity policy, upgrade compatibility, and multi-day soak testing.

## Dependency-first implementation waves

### Wave 0 — complete

I1-GB, I-4B, and O1A.

### Wave 1 — complete

I1-GC and I-4C1.

### Wave 2 — current

```text
I1-GD
|| I-4C2
|| O1B
|| O1C
|| UI-B1A projection design
```

### Wave 3 — next

```text
I-4D
|| O1D -> O1E
|| I-5A and I-7A/B contracts
```

### Wave 4 — production proof and product surfaces

```text
I1-GE
|| I-4E -> I-4F
|| O1F
|| UI-B1A implementation
```

## Integration checkpoints

```text
G1  I1-G complete
    sealed evidence -> exact replay -> C1-5/B2 completion
    -> retention -> crash proof

M4  Phase I-4 complete
    active current memory -> hidden successor
    -> M2/RelayCTX exclusion -> historical evidence preserved

O1  automatic bounded local processing complete
    O1A + O1B/O1C + O1D/O1E + O1F

E2  governed Primary MEM product
    I-4 through I-7 + UI-B1 + repeatable real conversation use
```

O1A completion alone does not satisfy the O1 checkpoint.

## Evaluation gates

### E1: Core RelayLM product hypothesis — available

Phase I-3 + UI-B0 + O0 prove trusted-scene formation, separate Home recall, observation, Correct, and fresh-conversation corrected retrieval. They do not prove direct Home-origin formation or automatic processing.

### E2: Primary MEM governance product — future

Phase I-4 through I-7 + UI-B1 + repeatable real conversation use.

### E3: Long-term character system — future

Phase I-8 and I-9 + complete I1-G + O1/O2 + O3 soak evidence.

## Preserved boundaries

- I1-GA, I1-GB, and I1-GC are complete; I1-GD and I1-GE remain incomplete.
- O1A is contract-only; O1B is complete; O1C through O1F remain unimplemented.
- I1-G records and B2 queue records remain separate state machines.
- O1 invokes I1-GC and O0/C2; it does not absorb their semantics.
- I-4C1/I-4C2 are delivery subdivisions, not new lifecycle authorities.
- UI-B0/UI-B1 own no worker, queue, scheduler, filesystem, namespace, SOUL, or mutation authority.
- Text conversation does not imply TTS, audio, avatar, or Live2D execution.

<!-- O1B_CURRENT_BOUNDARY -->
### O1B sealed replay-lane discovery — complete

O1B owns one bounded secure inventory of the configured durable-finalization root, exact grouping and eligibility classification, lexicographic selection of one sealed-pending locator, canonical selected-locator reread, and at most one delegation to the existing I1-GC authority. It owns no replay algorithm, completion publication, queue lane, C2/worker execution, polling, fairness, backoff, shutdown, supervision, or always-on operation. O1C through O1F, O2, and O3 remain unimplemented.
