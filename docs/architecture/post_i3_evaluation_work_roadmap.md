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
  - an evaluation gate changes its completion claim
relaylm_not_authoritative_for:
  - current runtime implementation status
  - exact mutation schemas
  - exact queue or worker contracts
  - RelaySOUL revision schema
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase_i3_auditable_primary_mem_correct.md
  - soul_lab_ui_b0_real_home_conversation.md
  - pipeline_implementation_plan.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_current_target.md
  - soul_lab_ui_mvp.md
  - soul_lab_runtime_mvp.md
  - memory_lifecycle_design.md
---
# Post-I3 Evaluation and Work Roadmap

## Purpose

Phase I-3 auditable Primary MEM Correct and UI-B0 real Home conversation are complete. This document records the remaining sequence for evaluating RelayLM as a text-first local character product and then extending memory governance and operations.

The roadmap has three tracks:

```text
Memory governance
  -> Forget, Pin, Merge, Held review, Secondary MEM, RelaySOUL

SOUL Lab experience
  -> real Home conversation, lifecycle visibility, evaluation evidence

Operations
  -> one-job execution, pre-enqueue durability, queue selection,
     worker supervision, always-on operation
```

Implementation must remain incremental. Real product evaluation begins before I-9.

## Current completed foundation

Complete:

- ordinary managed Turn 1 Primary MEM formation through C2,
- next-turn M2 retrieval and RelayCTX injection,
- character and namespace isolation,
- Phase I-2 real latest-run and memory observation,
- Phase I-3 auditable Correct and corrected retrieval,
- UI-B0 bounded real Home non-stream and SSE conversation,
- explicit Real Runtime / Local Preview separation,
- Stop, Retry, New Conversation, and stale-request fencing.

Unresolved operational boundaries:

- O0 local one-job selection and execution convenience,
- I1-G pre-enqueue durability,
- automatic queue scanning and supervised operation.

## Target product loop

```text
SOUL Lab Home real conversation
  -> existing RelayLM managed request
  -> existing M2 retrieval and RelayCTX injection
  -> visible response
  -> explicit C2 one-job execution or future O0
  -> Primary MEM formation or held/blocked result
  -> Phase I-2 Lab Observation
  -> Phase I-3 or later explicit memory operation
  -> Home New Conversation
  -> changed retrieval and response behavior
```

The long-term loop extends this path:

```text
Primary MEM set
  -> Secondary MEM consolidation
  -> stable long-term retrieval
  -> separately governed RelaySOUL proposal
  -> explicit intervention and rollback
```

## Track A: Memory governance phases

### Phase I-3: Auditable Correct — complete

Phase I-3 is the baseline mutation contract. Later operations must reuse exact scope, current-revision validation, bounded semantic diff, explicit confirmation, durable audit evidence, page/index/log convergence, recovery, and later retrieval validation.

### Phase I-4: Forget / Hide

Goal:

> Exclude one memory from ordinary retrieval without destroying auditability.

Work slices:

```text
I-4A  lifecycle-state and destructive-operation contract
I-4B  exact revision, scope, lineage, and current-state preflight
I-4C  atomic tombstone or hidden-state apply
I-4D  index/log convergence and M2 exclusion
I-4E  SOUL Lab confirmation, refusal, conflict, and receipt UI
I-4F  fresh-conversation exclusion and recovery smoke
```

Physical deletion is not the default. Irreversible purge requires a separate future boundary.

### Phase I-5: Pin / Unpin

Goal:

> Raise or restore bounded retrieval priority without changing authority order.

```text
I-5A  pin eligibility and bounded priority contract
I-5B  atomic pin metadata apply and audit receipt
I-5C  unpin convergence
I-5D  M2 ranking integration without unconditional injection
I-5E  SOUL Lab UI
I-5F  ranking, budget, isolation, and stale-revision smoke
```

Pinning must not override Secondary MEM, SOUL, OUTPUT_POLICY, or RELATIONSHIP_ANCHOR.

### Phase I-6: Merge / Supersession

Goal:

> Converge duplicate or sequential Primary memories into one canonical representation while preserving lineage.

```text
I-6A  multi-memory eligibility and contradiction preflight
I-6B  bounded merged representation and semantic diff
I-6C  optimistic concurrency and atomic apply
I-6D  source memories marked superseded
I-6E  index/log and retrieval de-duplication
I-6F  SOUL Lab multi-select and confirmation
I-6G  crash, retry, stale-record, and duplicate-retrieval smoke
```

### Phase I-7: Held Apply / Discard

Goal:

> Review exceptional held candidates and explicitly apply, correct-then-apply, or discard them.

```text
I-7A  held identity, reason, evidence, and expiry contract
I-7B  policy, character, namespace, and source revalidation
I-7C  Apply into authoritative Primary MEM
I-7D  Discard into durable reviewed rejection
I-7E  optional bounded correction before Apply
I-7F  SOUL Lab held-review UI
I-7G  sensitive, contradictory, stale, cross-scope, and replay smoke
```

Held review remains exceptional; ordinary safe formation must not become a mandatory approval queue.

### Phase I-8: Secondary MEM Consolidation

Goal:

> Consolidate related Primary MEM into stable lineage-backed Secondary MEM.

```text
I-8A  grouping and candidate discovery
I-8B  duplicate, supersession, contradiction, and namespace analysis
I-8C  stable summary and relation candidates
I-8D  SOUL-anchor validation without SOUL mutation
I-8E  idempotent rollback-friendly apply or hold
I-8F  M2 Secondary-priority retrieval integration
I-8G  Lab observation and lineage inspection
I-8H  long-horizon retrieval and contradiction smoke
```

### Phase I-9: RelaySOUL Proposal / Intervention / Rollback

Goal:

> Derive identity-level proposals from governed evidence, require explicit intervention, and support auditable rollback.

```text
I-9A  proposal identity, evidence, scope, and risk contract
I-9B  bounded SOUL semantic diff and protected-anchor validation
I-9C  approval, hold, and discard decisions
I-9D  atomic SOUL revision with prior revision preservation
I-9E  rollback contract and convergence
I-9F  Pod / SOUL Intervention real UI
I-9G  fresh-conversation behavior validation
I-9H  stale, cross-character, conflict, and rollback smoke
```

RelayMEM and RelaySLP may produce proposals; they must never mutate SOUL directly.

## Track B: SOUL Lab experience

### UI-B0: Real Home Conversation — complete

Implemented:

```text
UI-B0A  server-owned character and single unambiguous model-route resolution
UI-B0B  bounded real non-stream request path
UI-B0C  bounded UTF-8/SSE streaming and one-entry delta accumulation
UI-B0D  soft stop, abort, failure, and snapshot retry
UI-B0E  character/session/generation/route stale-response fencing
UI-B0F  explicit Real Runtime / Local Preview separation
UI-B0G  browser-local New Conversation
UI-B0H  existing M2 / RelayCTX path and Phase I-2 evidence boundary
```

The browser does not create SOUL authority, filesystem paths, memory namespaces, backend IDs, credentials, or hidden system prompts. See [UI-B0 Real Home Conversation](soul_lab_ui_b0_real_home_conversation.md).

### UI-B1: Memory lifecycle visibility

Goal:

> Make conversation, memory processing, observation, and intervention understandable as one product loop.

```text
UI-B1A  conversation-to-Lab navigation and latest-run correlation
UI-B1B  not-scheduled / queued / processing / formed / held / blocked / failed states
UI-B1C  operation receipt and current revision display
UI-B1D  fresh-conversation verification entry point
UI-B1E  separation of runtime state, evidence, and mutation authority
```

### UI-B2: Evaluation scenarios and evidence

Goal:

> Provide repeatable manual and automated product-evaluation scenarios.

Required scenarios include correction, forgetting, pinning, merge, held review, Secondary consolidation, SOUL proposal/rollback, and cross-character isolation.

## Track C: Operational work phases

### O0: Local one-job runner

Goal:

> Process one eligible queued job locally using existing B3, C1-5, C2, and C1-2 authority.

```text
O0A  bounded eligible-record selection
O0B  canonical reread before claim
O0C  unchanged B3 claim and lease fencing
O0D  unchanged C1-5 rehydration and C2 execution
O0E  content-free result projection and exit status
O0F  duplicate, retry-time, terminal, and corruption smoke
```

The browser must not be the worker or queue-selection authority.

### I1-G: Pre-enqueue durability

Goal:

> Close the process-exit window after visible response delivery but before durable protected-source and B2 queue publication.

```text
I1-GA  failure-window and durable-finalization contract
I1-GB  atomic or convergent durable publication boundary
I1-GC  restart replay and duplicate suppression
I1-GD  retention and cleanup
I1-GE  crash-at-every-boundary smoke
```

The design must preserve visible-response independence, source-before-queue ordering, dispatch idempotency, content separation, restart recovery, and no duplicate logical memory formation.

### O1: Queue scanner and retry scheduler

Goal:

> Select eligible queued records and invoke existing one-job execution without redefining queue or memory semantics.

```text
O1A  secure bounded discovery
O1B  deterministic eligibility and retry ordering
O1C  canonical reread before B3 claim
O1D  bounded idle and polling behavior
O1E  stale, corrupt, terminal, and concurrent scanner smoke
```

### O2: Supervised worker service

Goal:

> Run bounded workers with controlled lifecycle and recoverable local operation.

```text
O2A  lifecycle and configuration contract
O2B  bounded concurrency and backpressure
O2C  graceful shutdown and lease-aware cancellation
O2D  health and content-free diagnostics
O2E  restart, lock, saturation, and repeated-failure smoke
```

### O3: Always-on local operation

Goal:

> Operate RelayLM, SOUL Lab, and worker processing over extended sessions with predictable startup and recovery.

```text
O3A  local startup and shutdown integration
O3B  static SOUL Lab serving or packaged launch
O3C  retention, cleanup, and disk-capacity policy
O3D  upgrade and schema-compatibility procedure
O3E  multi-day soak and restart testing
```

TTS, audio, Live2D, ASR, and public remote access are not required for the text-first evaluation gates.

## Recommended implementation order

```text
Completed:
  Phase I-3 Correct
  UI-B0 Real Home Conversation

Current parallel work:
  O0 Local one-job runner
  I1-G contract and fault model
  Phase I-4 contract and lifecycle-state design

Available now:
  Evaluation Gate E1 using an existing explicit one-job C2 method

Then:
  Phase I-4 Forget / Hide
  Phase I-5 Pin / Unpin
  Phase I-6 Merge / Supersession
  Phase I-7 Held Apply / Discard
  UI-B1 memory lifecycle visibility

  Evaluation Gate E2

  I1-G implementation
  O1 queue scanner / retry scheduler
  O2 supervised worker service

  Phase I-8 Secondary MEM consolidation
  Phase I-9 RelaySOUL proposal / intervention / rollback
  UI-B2 evaluation scenarios and evidence
  O3 always-on local operation and soak

  Evaluation Gate E3
```

I1-G and operations may move earlier in parallel, but become mandatory before long-duration memory-formation or multi-day consolidation evidence is treated as reliable.

## Parallel development map

```text
Thread A  O0 Local one-job runner
Thread B  I1-G contract and fault model
Thread C  Phase I-4 contract and lifecycle-state design
Thread D  UI-B1 lifecycle visibility design after stable status projections
```

Ownership:

- UI-B0 owns Home/chat transport and browser session state and is complete.
- O0 owns a thin Python runner reusing B3, C1-5, C2, and C1-2.
- I1-G owns the pre-enqueue failure window and durable-finalization boundary.
- I-4 owns lifecycle semantics and a separately reviewed authoritative apply.

## Evaluation gates

### E1: Core RelayLM product hypothesis

Required:

```text
Phase I-3 complete
+ UI-B0 complete
+ O0 or another explicit one-job execution method
```

Proves that the user can converse, form and observe a real Primary MEM, Correct it, retrieve the corrected representation in a fresh browser-local conversation, and distinguish durable memory influence from frontend history.

UI-B0 is complete, so E1 may be exercised now with the existing explicit C2 method. O0 improves repeatability but is not required to begin.

### E2: Primary MEM governance product

Required:

```text
Phase I-4 through I-7
+ UI-B1
+ repeatable real conversation use
```

Proves safe exclusion, bounded prioritization, duplicate convergence, held resolution, autonomous ordinary formation, and understandable intervention.

### E3: Long-term character system

Required:

```text
Phase I-8 and I-9
+ I1-G
+ O1 and O2
+ O3 soak evidence
```

Proves stable consolidation, proposal-driven identity change, rollback, restart safety, and operational reliability.

## Measurement guidance

Record at least:

- formed, held, blocked, failed, and lost-or-unknown counts,
- governance outcomes and stale/mixed-scope refusals,
- retrieval selection before and after each operation,
- injected revision and backend-bound inclusion evidence,
- duplicate and contradiction rates,
- worker retry/restart behavior,
- user effort required to keep memory useful.

Raw prompts, protected source, credentials, full traces, and unrestricted memory pages must not be copied into generic telemetry.

## Preserved boundaries

- Phase I-3 remains the baseline mutation contract.
- UI-B0 is a client of existing route, M2, RelayCTX, backend, and RelaySLP authority.
- Phase I-4 through I-9 require dedicated contracts.
- RelayMEM owns memory meaning and persistence.
- M2 and RelayCTX own selection and backend-bound injection.
- RelaySOUL changes require explicit intervention.
- queue scanning and supervision must reuse B3, C1-5, C2, and C1-2.
- text conversation does not imply TTS or avatar execution.