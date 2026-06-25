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
  - phase_i4_primary_mem_forget_hide_contract.md
  - soul_lab_ui_b0_real_home_conversation.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - o0_local_one_job_runner.md
  - pipeline_implementation_plan.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_current_target.md
  - soul_lab_ui_mvp.md
  - soul_lab_runtime_mvp.md
  - memory_lifecycle_design.md
---
# Post-I3 Evaluation and Work Roadmap

Last reviewed: 2026-06-25 JST

## Purpose

Phase I-3 auditable Primary MEM Correct, UI-B0 real Home conversation, and O0 local one-job execution are complete. I1-GA defines the pre-enqueue durable-finalization target and pure fault model. Phase I-4A defines the Forget / Hide target contract. Production I1-G durability and production Forget remain incomplete.

This roadmap records the dependency-first execution sequence for the next RelayLM work. It intentionally separates three authorities:

```text
Memory governance
  -> current-state resolution and mutation fencing
  -> Forget, Pin, Held review, Merge
  -> Secondary MEM and RelaySOUL

SOUL Lab experience
  -> real Home conversation
  -> lifecycle and operation visibility
  -> repeatable evaluation evidence

Operations
  -> O0 one-job execution
  -> durable-finalization replay
  -> bounded scheduling
  -> supervised and always-on operation
```

Phase numbering remains stable, but implementation order follows dependency and risk rather than numeric order alone.

## Current completed foundation

Complete:

- ordinary managed Turn 1 Primary MEM formation through C2;
- O0 explicit selection and execution of at most one eligible durable queued job;
- next-turn M2 retrieval and RelayCTX injection;
- character and namespace isolation;
- Phase I-2 latest-run, memory, and used-memory observation;
- Phase I-3 auditable Correct and corrected retrieval;
- UI-B0 bounded non-stream and SSE real Home conversation;
- explicit Real Runtime / Local Preview separation;
- Stop, Retry, New Conversation, and stale-request fencing;
- I1-GA durable-finalization contract and deterministic fault model.

Defined target only:

- Phase I-4A Forget / Hide lifecycle, persistence, concurrency, API, recovery, and retrieval-exclusion contract.

Unresolved or unimplemented:

- I1-GB through I1-GE production durability;
- Phase I-4B through I-4F Forget implementation;
- O1 automatic durable-finalization replay and queue scheduling;
- O2 supervised worker operation;
- O3 always-on local operation.

## Target product loop

```text
SOUL Lab Home real conversation
  -> existing RelayLM managed request
  -> existing M2 retrieval and RelayCTX injection
  -> visible response
  -> durable-finalization evidence
  -> C1-5 protected source and B2 queue convergence
  -> O0 or later O1 execution
  -> Primary MEM formed / held / blocked / failed
  -> Phase I-2 observation
  -> explicit memory operation
  -> Home New Conversation
  -> changed retrieval and response behavior
```

The long-term loop extends this path:

```text
Primary MEM governance
  -> Secondary MEM consolidation
  -> stable lineage-backed retrieval
  -> separately governed RelaySOUL proposal
  -> explicit intervention and rollback
```

## Track A: Memory governance phases

### Phase I-3: Auditable Correct — complete

Phase I-3 is the implemented mutation baseline. Later operations must reuse exact scope resolution, current-revision validation, bounded preview, explicit confirmation, durable audit evidence, page/index/log convergence, recovery, and later retrieval validation.

### Phase I-4: Forget / Hide

Goal:

> Exclude one current active Primary MEM from ordinary retrieval without destroying auditability or rewriting historical use evidence.

Canonical terminology:

```text
user-facing operation: Forget
canonical lifecycle state: hidden
runtime-private audit artifact: Forget tombstone
```

Persistence and convergence:

```text
revision N active
  -> exact prepared operation and fail-closed quarantine
  -> immutable successor Primary page through M3e
revision N+1 hidden
  -> M3f/M3g index-before-log convergence
  -> M2 exclusion verification
  -> immutable Forget tombstone finalization
```

The hidden successor page is lifecycle authority. The tombstone is audit/recovery evidence. Correct and Forget share one canonical current-state resolver and one mutation fence.

Work slices:

```text
I-4A  lifecycle, persistence, concurrency, API, recovery, and fault contract — defined target
I-4B  canonical current-state resolver, shared mutation fence, exact preflight/history, and token issuance
I-4C  immutable hidden successor apply, prepared artifact, Forget tombstone, and exact replay
I-4D  index/log convergence, M2 exclusion, and historical used-memory lifecycle projection
I-4E  loopback API and SOUL Lab confirmation/refusal/conflict/receipt UI
I-4F  fresh-conversation exclusion, security, race, and crash-recovery smoke
```

Only I-4A is defined. I-4B through I-4F are unimplemented.

#### I-4C delivery subdivision

The official phase remains I-4C, but implementation should be delivered through two separately reviewable PRs:

```text
I-4C1  exact token validation, shared revision claim, prepared artifact,
       hidden successor candidate, M3e publication, and one-winner concurrency

I-4C2  prepared-operation resume, forward-only recovery, exact replay,
       Forget tombstone finalization, and response-loss convergence
```

I-4C1 must not claim retrieval exclusion. I-4C2 must not reactivate a prior active page after the hidden successor is committed.

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

Pinning must not override Secondary MEM, SOUL, OUTPUT_POLICY, or RELATIONSHIP_ANCHOR. Hidden memory is ineligible.

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

Merge is the first multi-memory mutation and therefore the largest extension of the mutation coordinator. Hidden memories are ineligible by default.

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

Held review remains exceptional. Ordinary safe formation must not become a mandatory approval queue.

### Recommended production order after I-4

The phase identifiers remain I-5, I-6, and I-7, but production implementation should proceed:

```text
I-5 Pin / Unpin
  -> I-7 Held Apply / Discard
  -> I-6 Merge / Supersession
```

This order stabilizes single-memory mutation, token, receipt, and UI patterns before introducing multi-memory claims and supersession lineage. I-6A/I-6B contract work may proceed in parallel with I-5 or I-7, but production mutation-coordinator changes should land serially.

### Phase I-8: Secondary MEM Consolidation

Goal:

> Consolidate related governed Primary MEM into stable lineage-backed Secondary MEM.

```text
I-8A  grouping and candidate discovery
I-8B  duplicate, supersession, contradiction, lifecycle, and namespace analysis
I-8C  stable summary and relation candidates
I-8D  SOUL-anchor validation without SOUL mutation
I-8E  idempotent rollback-friendly apply or hold
I-8F  M2 Secondary-priority retrieval integration
I-8G  Lab observation and lineage inspection
I-8H  long-horizon retrieval and contradiction smoke
```

Hidden, unresolved, or superseded-ineligible Primary MEM must not enter ordinary consolidation.

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
UI-B0A  server-owned character and model-route resolution
UI-B0B  bounded real non-stream request path
UI-B0C  bounded UTF-8/SSE streaming and one-entry accumulation
UI-B0D  Stop, abort, failure, and snapshot retry
UI-B0E  character/session/generation/route stale-response fencing
UI-B0F  explicit Real Runtime / Local Preview separation
UI-B0G  browser-local New Conversation
UI-B0H  existing M2 / RelayCTX and Phase I-2 evidence boundary
```

The browser owns no queue, worker, SOUL, filesystem, credential, namespace, or memory mutation authority.

### UI-B1: Memory lifecycle visibility

Goal:

> Make conversation, durable processing, memory lifecycle, and intervention understandable as one product loop.

UI-B1 is split so read-only visibility does not wait for every governance operation.

```text
UI-B1A  after I1-GC and I-4D
         conversation-to-Lab correlation
         not-scheduled / durable-finalization-pending / queued / processing
         formed / held / blocked / failed
         active / hidden / recovery-required
         current revision and fresh-conversation verification entry

UI-B1B  after I-5 through I-7
         operation receipts
         pin/unpin state
         merge/supersession lineage
         held apply/discard decisions
         separation of runtime state, evidence, and mutation authority
```

UI-B1A is read-only and must not introduce worker or mutation authority into the browser.

### UI-B2: Evaluation scenarios and evidence

Goal:

> Provide repeatable manual and automated product-evaluation scenarios.

Required scenarios include correction, forgetting, pinning, held review, merge, Secondary consolidation, SOUL proposal/rollback, restart recovery, and cross-character isolation.

## Track C: Operational work phases

### O0: Local one-job runner — complete

Completion claim:

> A local operator can process at most one eligible queued job per CLI invocation through the existing C2 production path.

```text
relaylm-worker --once --config config.yaml [--character-id CHARACTER_ID]
```

O0 adds no polling, fairness policy, stale scanner, service supervision, browser control, or worker pool.

### I1-G: Pre-enqueue durability

Goal:

> Close the process-exit window after visible response delivery but before durable protected-source and B2 queue publication.

```text
I1-GA  failure-window and durable-finalization contract — complete
I1-GB  atomic/convergent durable publication and bounded response-release admission — current implementation work
I1-GC  one-record restart replay, fencing, duplicate suppression, and completion marker
I1-GD  retention, orphan reconciliation, and cleanup
I1-GE  production crash-at-every-boundary integration smoke
```

I1-GB and I1-GC are distinct completion boundaries. I1-GB leaves restart-recoverable evidence; I1-GC turns one caller-selected sealed record into canonical C1-5 and B2 convergence. I1-GD classifies and cleans only proven-safe records. I1-GE validates the production sequence.

### O1: Queue scanner and retry scheduler

Goal:

> Repeatedly select bounded eligible work and invoke existing one-record authorities without redefining durable-finalization, queue, worker, or memory semantics.

O1 has two distinct work-source lanes:

```text
O1A  bounded work-source scheduling and idle contract

O1B  durable-finalization replay lane
     discover one eligible sealed I1-G record
       -> secure reread
       -> invoke one I1-GC replay
       -> produce or verify C1-5 and B2 only

O1C  queue execution lane
     discover one eligible B2 record
       -> reuse O0 selection/reread primitives where compatible
       -> invoke one existing C2 execution

O1D  deterministic ordering, fairness, retry-time, and bounded backoff
O1E  stale-claim recovery orchestration and graceful shutdown
O1F  corrupt, terminal, concurrent, saturation, restart, and leakage smoke
```

A recommended scheduler cycle is:

```text
bounded I1-G sealed replay
  -> bounded B2 queue execution
  -> idle/backoff
```

The two lanes remain different state machines and authorities. O1 must not treat an I1-G sealed record as a queue record, execute a worker during I1-G replay, or recreate I1-B/C1-5/B2 semantics.

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

> Operate RelayLM, SOUL Lab, durable-finalization replay, and worker processing over extended sessions with predictable startup and recovery.

```text
O3A  local startup and shutdown integration
O3B  static SOUL Lab serving or packaged launch
O3C  retention, cleanup, and disk-capacity policy
O3D  upgrade and schema-compatibility procedure
O3E  multi-day soak and restart testing
```

TTS, audio, Live2D, ASR, and public remote access are not required for the text-first evaluation gates.

## Dependency-first implementation waves

### Wave 0 — current parallel work

```text
Thread A  I1-GB durable-finalization publication
Thread B  Phase I-4B canonical resolver, shared fence, and read-only contracts
Thread C  O1A work-source scheduling contract only
```

I1-GB and I-4B are independent production authorities. They may merge in either order. The later merge must rerun affected regression and reconcile shared documentation/configuration files.

Required cross-regression after both land:

```text
I1-G side:
  non-stream and SSE response behavior
  I1-B source production
  C1-5 / B2 regressions
  UI-B0 conversation regressions

I-4 side:
  I-3 Correct preflight/apply/replay
  original and corrected revision resolution
  pending-operation conflict
  M2 current-revision equivalence
```

### Wave 1 — one-record recovery and authoritative lifecycle commit

```text
Thread A  I1-GC one-record replay
Thread B  I-4C1 hidden-successor commit ownership
Thread C  O1 replay/queue lane contract refinement
Thread D  UI-B1A projection design
```

I1-GC is the immediate follow-up to I1-GB. Durable evidence without a production replay helper is not complete restart convergence.

### Wave 2 — convergence, cleanup, and automatic bounded operation

```text
Thread A  I1-GD retention / orphan reconciliation / cleanup
Thread B  I-4C2 forward recovery and tombstone
          -> I-4D M2 exclusion and historical projection
Thread C  O1 implementation using I1-GC and O0/C2
Thread D  I-5A contract and I-7A/B contract work
```

I-4D is the user-visible Forget semantic commit. Forget apply must not be exposed as complete before hidden-state M2 and RelayCTX exclusion are proven.

### Wave 3 — production proof and product surfaces

```text
Thread A  I1-GE crash-at-every-boundary integration smoke
Thread B  I-4E loopback API and SOUL Lab UI
          -> I-4F fault/security/race/fresh-conversation smoke
Thread C  O1 completion and operational regression
Thread D  UI-B1A read-only lifecycle visibility
```

## Integration checkpoints

```text
G1  I1-G complete
    visible release -> sealed evidence -> restart replay
    -> canonical C1-5/B2 convergence -> retention/crash proof

M4  Phase I-4 complete
    active current memory -> hidden successor
    -> M2/RelayCTX exclusion -> historical evidence preserved

O1  automatic bounded local processing complete
    sealed replay lane + queue execution lane
    without redefining I1-G, B3, C2, or M3 semantics

E2  governed Primary MEM product
    I-4 through I-7 + UI-B1 + repeatable real conversation use
```

## Recommended overall order

```text
Completed:
  Phase I-3 Correct
  UI-B0 Real Home Conversation
  O0 Local one-job runner
  I1-GA contract / design decision / fault model
  Phase I-4A Forget / Hide contract

Current:
  I1-GB || I-4B || O1A design

Next:
  I1-GC || I-4C1

Then:
  I1-GD || I-4C2 -> I-4D || O1 implementation

Then:
  I1-GE || I-4E -> I-4F || UI-B1A

Governance after I-4:
  I-5 -> I-7 -> I-6 -> UI-B1B

Long-term:
  I-8 -> I-9 -> UI-B2 -> O3 soak
```

I1-G and O1/O2 become mandatory before long-duration memory-formation or multi-day consolidation evidence is treated as reliable.

## Parallel ownership

- UI-B0 owns Home/chat transport and browser-local session state.
- I1-G owns pre-enqueue durable-finalization evidence, one-record replay, completion, and retention classification.
- O1 owns bounded discovery and scheduling across separate I1-G and B2 lanes.
- O0/C2/B3/C1-5/C1-2 remain queue execution authorities.
- I-4 owns Primary lifecycle semantics and the separately reviewed Forget mutation.
- M2 and RelayCTX own retrieval eligibility and backend-bound injection.
- UI-B1 remains read-only visibility until an exact operation route is separately implemented.

## Evaluation gates

### E1: Core RelayLM product hypothesis

Required:

```text
Phase I-3 complete
+ UI-B0 complete
+ O0 complete
```

E1 is available now as an explicit operator-driven evaluation. It proves conversation, real Primary formation, observation, Correct, fresh-conversation corrected retrieval, and separation from frontend history. It is not automatic processing.

### E2: Primary MEM governance product

Required:

```text
Phase I-4 through I-7
+ UI-B1
+ repeatable real conversation use
```

E2 proves safe exclusion, bounded prioritization, held resolution, duplicate convergence, understandable intervention, and fresh-conversation validation.

### E3: Long-term character system

Required:

```text
Phase I-8 and I-9
+ I1-G
+ O1 and O2
+ O3 soak evidence
```

E3 proves stable consolidation, proposal-driven identity change, rollback, restart safety, and operational reliability.

## Measurement guidance

Record at least:

- formed, held, blocked, failed, and lost-or-unknown counts;
- durable-finalization pending/replayed/isolated/complete counts;
- correction/Forget/pin/held/merge outcomes and stale/mixed-scope refusals;
- retrieval selection before and after each operation;
- injected revision and lifecycle evidence;
- duplicate and contradiction rates;
- worker retry/restart behavior;
- user effort required to keep memory useful.

Raw prompts, protected source, credentials, full traces, and unrestricted memory pages must not be copied into generic telemetry.

## Preserved boundaries

- Phase I-3 remains the implemented baseline mutation contract.
- Phase I-4A remains the exact target contract until production slices land.
- I-4C1/I-4C2 are delivery subdivisions, not new lifecycle authorities.
- I1-G records and B2 queue records remain separate state machines.
- O1 invokes I1-GC and O0/C2; it does not absorb their semantics.
- UI-B0 and UI-B1 do not own worker, queue, filesystem, namespace, SOUL, or mutation authority.
- Physical deletion, secure erase, purge, restore, and unhide remain separate future contracts.
- Text conversation does not imply TTS, audio, avatar, or Live2D execution.
