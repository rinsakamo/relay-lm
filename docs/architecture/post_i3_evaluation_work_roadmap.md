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
  - phase_i4b_primary_current_state_shared_fence.md
  - soul_lab_ui_b0_real_home_conversation.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - o0_local_one_job_runner.md
  - o1a_two_lane_scheduler_contract.md
  - pipeline_implementation_plan.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_current_target.md
  - soul_lab_ui_mvp.md
  - soul_lab_runtime_mvp.md
  - memory_lifecycle_design.md
---
# Post-I3 Evaluation and Work Roadmap

Last reviewed: 2026-06-26 JST

## Purpose

Phase I-3 Correct, UI-B0 real Home conversation, O0 local one-job execution, I1-GB pre-release durable-finalization publication, the I-4B read-only current-state/shared-fence boundary, and the O1A two-lane scheduler/idle contract are complete. Phase I-4A remains the target Forget / Hide contract. Restart replay/completion convergence, production lane discovery/delegation, and production hidden-lifecycle apply/exclusion remain incomplete.

This roadmap records dependency-first work after I-3 while keeping four authorities separate:

```text
Memory governance
  -> current-state resolution and mutation fencing
  -> Forget, Pin, Held review, Merge
  -> Secondary MEM and RelaySOUL

SOUL Lab experience
  -> real Home conversation
  -> lifecycle and operation visibility
  -> repeatable evaluation evidence

Durability
  -> pre-release durable-finalization evidence
  -> one-record restart replay and completion
  -> retention and crash proof

Operations
  -> O0 one-job execution
  -> O1A two-lane round/idle contract
  -> O1B/O1C bounded production lane adapters
  -> O1D/O1E/O1F policy, recovery, shutdown, and validation
  -> supervised and always-on operation
```

Phase identifiers remain stable. Production order follows dependency and risk rather than numeric order alone.

## Current completed foundation

Complete:

- ordinary managed Turn 1 Primary MEM formation through C2;
- O0 explicit selection and execution of at most one eligible durable queued job;
- O1A pure replay-before-queue round, adapter-result, disposition, and content-free projection contract;
- next-turn M2 retrieval and RelayCTX injection;
- character and namespace isolation;
- Phase I-2 latest-run, memory, and used-memory observation;
- Phase I-3 auditable Correct and corrected retrieval;
- UI-B0 bounded non-stream and SSE real Home conversation;
- I1-GA durable-finalization contract and deterministic fault model;
- I1-GB bounded private base/segment/seal publication before protected visible release;
- I-4B canonical read-only current-state resolver, shared Correct/Forget fence, Forget preflight/token validation, and bounded zero-item history.

Defined target:

- Phase I-4A Forget / Hide lifecycle, persistence, concurrency, recovery, API, and retrieval-exclusion contract.

Unresolved or unimplemented:

- I1-GC through I1-GE restart replay, cleanup, and crash validation;
- Phase I-4C through I-4F hidden apply, M2 exclusion, API/UI, and validation;
- O1B one eligible sealed-record discovery and I1-GC delegation;
- O1C one eligible queue-record discovery and O0-compatible C2 delegation;
- O1D fairness/retry/backoff, O1E stale recovery/shutdown, and O1F operational validation;
- any production O1 polling/sleep loop, scheduler configuration, or CLI;
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

E1 does not prove direct Home-origin formation because UI-B0 sends standard Chat Completions fields and does not self-assert trusted scene-admission metadata. It also does not prove automatic scheduling; O1A is a pure contract only.

## Target product loop

```text
SOUL Lab Home real conversation
  -> existing RelayLM managed request
  -> existing M2 retrieval and RelayCTX injection
  -> visible response
  -> durable-finalization evidence
  -> I1-GC canonical C1-5 and B2 convergence after restart when needed
  -> O0 or later O1C execution
  -> Primary MEM formed / held / blocked / failed
  -> Phase I-2 observation
  -> explicit memory operation
  -> Home New Conversation
  -> changed retrieval and response behavior
```

The long-term loop extends governed Primary MEM into Secondary MEM and separately governed RelaySOUL proposals. RelayMEM and RelaySLP never mutate SOUL directly.

## Track A: Memory governance

### Phase I-3: Auditable Correct — complete

Phase I-3 is the mutation baseline. Later operations reuse exact scope resolution, current-revision validation, bounded preview, explicit confirmation, durable audit evidence, page/index/log convergence, recovery, and later retrieval validation.

### Phase I-4A: Forget / Hide target contract — defined

Goal:

> Exclude one current active Primary MEM from ordinary retrieval without destroying auditability or rewriting historical use evidence.

Canonical terms:

```text
Forget            user-facing explicit operation
hidden            canonical current retrieval-ineligible lifecycle state
Forget tombstone  immutable runtime-private audit/recovery artifact
```

Persistence target:

```text
revision N active
  -> exact prepared operation and fail-closed quarantine
  -> immutable successor Primary page through M3e
revision N+1 hidden
  -> M3f/M3g index-before-log convergence
  -> M2 and RelayCTX exclusion verification
  -> immutable Forget tombstone finalization
```

The hidden successor page is lifecycle authority. The tombstone is audit/recovery evidence, not an independently mutable sidecar flag.

### Phase I-4B: Current-state resolver and shared mutation fence — complete

I-4B implements:

- `relaylm.mem.primary_current_state.v0` read-only resolution;
- one stable logical identity and exact current physical revision;
- lifecycle, mutation, retrieval-eligibility, control, and page validation;
- reuse of the Phase I-3 per-memory `.lock` path for Correct and Forget;
- read-only Forget preflight;
- five-minute exact-binding Forget token validation;
- bounded zero-item history;
- fail-closed `recovery_required` classification for valid unresolved prepared evidence.

I-4B does not write hidden successors, prepared Forget artifacts, tombstones, index/log changes, API routes, or UI state. Ordinary M2 and RelayCTX behavior remains unchanged in this slice.

### Phase I-4C through I-4F: Remaining Forget work

```text
I-4C1  exact token validation, shared revision claim, prepared artifact,
       hidden-successor candidate, M3e publication, one-winner concurrency

I-4C2  prepared resume, forward-only recovery, exact replay,
       tombstone finalization, response-loss convergence

I-4D   index/log convergence, M2/RelayCTX exclusion,
       historical used-memory lifecycle projection

I-4E   loopback API and SOUL Lab confirmation/refusal/conflict/receipt UI

I-4F   fresh-conversation exclusion, security, race, and crash-recovery smoke
```

I-4D is the user-visible semantic commit. Forget must not be described as product-complete before hidden-state exclusion is proven in a fresh ordinary managed turn.

Physical deletion, secure erase, purge, restore, and unhide remain separate future boundaries.

### Phase I-5: Pin / Unpin

```text
I-5A  pin eligibility and bounded priority contract
I-5B  atomic pin metadata apply and audit receipt
I-5C  unpin convergence
I-5D  M2 ranking integration without unconditional injection
I-5E  SOUL Lab UI
I-5F  ranking, budget, isolation, and stale-revision smoke
```

Pinning must not override Secondary MEM, SOUL, OUTPUT_POLICY, or RELATIONSHIP_ANCHOR. Hidden memory is ineligible.

### Phase I-7: Held Apply / Discard

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

### Phase I-6: Merge / Supersession

```text
I-6A  multi-memory eligibility and contradiction preflight
I-6B  bounded merged representation and semantic diff
I-6C  optimistic concurrency and atomic apply
I-6D  source memories marked superseded
I-6E  index/log and retrieval de-duplication
I-6F  SOUL Lab multi-select and confirmation
I-6G  crash, retry, stale-record, and duplicate-retrieval smoke
```

Merge is the first multi-memory mutation and therefore lands after single-memory token, receipt, revalidation, and UI patterns stabilize.

Recommended governance order after I-4:

```text
I-5 Pin / Unpin
  -> I-7 Held Apply / Discard
  -> I-6 Merge / Supersession
```

### Phase I-8: Secondary MEM consolidation

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

Hidden, unresolved, recovery-required, corrupt, or superseded-ineligible Primary MEM must not enter ordinary consolidation.

### Phase I-9: RelaySOUL proposal / intervention / rollback

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

RelayMEM and RelaySLP may produce proposals; they never mutate SOUL directly.

## Track B: SOUL Lab experience

### UI-B0: Real Home Conversation — complete

UI-B0 provides server-owned character/model route resolution, bounded real non-stream/SSE transport, Stop/Retry/New Conversation, stale-response fencing, and explicit Real Runtime / Local Preview separation. The browser owns no queue, worker, scheduler, SOUL, filesystem, credential, namespace, or memory mutation authority.

### UI-B1: Memory lifecycle visibility — planned

```text
UI-B1A  after I1-GC and I-4D
          conversation/run correlation
          durable-finalization-pending / queued / processing
          formed / held / blocked / failed
          active / hidden / recovery-required
          current revision and fresh-conversation verification

UI-B1B  after I-5 through I-7
          operation receipts
          pin/unpin state
          merge/supersession lineage
          held apply/discard decisions
          evidence/runtime/mutation authority separation
```

UI-B1A remains read-only and outside queue, scheduler, worker, and mutation authority.

### UI-B2: Evaluation scenarios and evidence — planned

Required scenarios include correction, forgetting, pinning, held review, merge, Secondary consolidation, SOUL proposal/rollback, restart recovery, and cross-character isolation.

## Track C: Operational work

### O0: Local one-job runner — complete

```text
relaylm-worker --once --config config.yaml [--character-id CHARACTER_ID]
```

One invocation processes at most one eligible queued record through existing C2 authority. It adds no polling, fairness policy, stale scanner, service supervision, browser control, or worker pool.

### I1-G: Pre-enqueue durability — in progress

```text
I1-GA  failure-window and durable-finalization contract                 complete
I1-GB  durable publication and bounded response-release admission       complete
I1-GC  one-record restart replay, duplicate convergence, completion     current implementation work
I1-GD  retention, orphan reconciliation, and cleanup                    planned
I1-GE  production crash-at-every-boundary integration smoke             planned
```

I1-GB leaves canonical restart evidence before protected visible release. I1-GC must turn one caller-selected sealed record into canonical C1-5 and B2 convergence without executing a worker.

### O1A: Two-lane scheduler and idle contract — complete

O1A fixes the scheduler authority without implementing production work discovery:

```text
validate scheduler gates
  -> replay-lane opportunity
       -> at most one future I1-GC delegation
  -> queue-lane opportunity
       -> at most one future C2 delegation
  -> aggregate bounded content-free results
  -> stop | run_next_round | idle
  -> return without sleeping
```

The order is fixed as replay then queue. A newly converged B2 record may be discovered in the same round, but only through independent queue discovery and canonical reread. Scheduler code must not pass replay output, job identity, or dispatch identity directly to C2.

O1A defines:

- separate `ReplayLaneAdapter` and `QueueLaneAdapter` contracts;
- at most one delegation per lane and two per round;
- lane-local failure isolation;
- scheduler-level fatal gate/dependency/configuration classification;
- target-only default-off configuration names;
- `stop`, `run_next_round`, and `idle` disposition semantics;
- bounded content-free result/projection schemas;
- pure deterministic contract smoke.

O1A adds no production scan, I1-GC/C2 invocation, polling, sleep, fairness, stale recovery, shutdown, config field, CLI, daemon, or service.

### O1B through O1F: Production scheduling — unimplemented

```text
O1B  one eligible I1-G sealed-record discovery and I1-GC delegation
O1C  one eligible B2 discovery and O0/C2 delegation
O1D  deterministic ordering, fairness, retry-time, bounded backoff, jitter
O1E  stale-claim recovery orchestration, cancellation, graceful shutdown
O1F  corruption, concurrency, saturation, restart, and leakage smoke
```

The two lanes remain separate state machines. O1 never treats an I1-G record as a queue record or executes a worker during replay.

O1D owns record ordering and fairness; O1A's fixed lane order is not a fairness policy. O1E owns cancellation and shutdown. O1F owns full operational proof.

### O2: Supervised worker service — planned

```text
O2A  lifecycle and configuration contract
O2B  bounded concurrency and backpressure
O2C  graceful shutdown and lease-aware cancellation
O2D  health and content-free diagnostics
O2E  restart, lock, saturation, and repeated-failure smoke
```

### O3: Always-on local operation — planned

```text
O3A  local startup and shutdown integration
O3B  static SOUL Lab serving or packaged launch
O3C  retention, cleanup, and disk-capacity policy
O3D  upgrade and schema-compatibility procedure
O3E  multi-day soak and restart testing
```

TTS, audio, Live2D, ASR, and public remote access are not required for text-first evaluation gates.

## Dependency-first implementation waves

### Wave 0 — completed implementation foundation

```text
Thread A  I1-GB durable-finalization publication — complete
Thread B  I-4B resolver/shared fence/read-only Forget — complete
Thread C  O1A scheduling and idle contract — complete
```

The final I-4B head passed the affected I1-G, response, I1-B, C1-5, B2, UI-B0, I-3 Correct, resolver, and M2-equivalence regressions. O1A adds a pure contract and documentation boundary without changing those production paths.

### Wave 1 — current

```text
Thread A  I1-GC one-record replay
Thread B  I-4C1 hidden-successor commit ownership
Thread C  O1B/O1C production lane adapters after exact dependency readiness
Thread D  UI-B1A projection design
```

O1B must consume the merged I1-GC one-record interface and must not copy a parallel branch implementation. O1C may extract a narrow O0-compatible helper while preserving O0 CLI/smoke behavior and unchanged C2/B3 authority.

### Wave 2 — forward convergence and bounded automation

```text
Thread A  I1-GD retention/orphan reconciliation/cleanup
Thread B  I-4C2 forward recovery/tombstone
          -> I-4D M2 exclusion/historical projection
Thread C  O1D fairness/retry/backoff
          -> O1E stale recovery/cancellation/shutdown
Thread D  I-5A and I-7A/B contract work
```

### Wave 3 — production proof and product surfaces

```text
Thread A  I1-GE crash-at-every-boundary integration smoke
Thread B  I-4E loopback API and SOUL Lab UI
          -> I-4F fault/security/race/fresh-conversation smoke
Thread C  O1F operational regression and production scheduling completion
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
    O1A contract + O1B/O1C adapters + O1D/O1E policy/recovery + O1F proof
    sealed replay lane + queue execution lane
    without redefining I1-G, B3, C2, or M3 semantics

E2  governed Primary MEM product
    I-4 through I-7 + UI-B1 + repeatable real conversation use
```

O1A completion alone does not satisfy the O1 checkpoint.

## Recommended overall order

```text
Completed:
  Phase I-3 Correct
  UI-B0 Real Home Conversation
  O0 Local one-job runner
  I1-GA / I1-GB
  Phase I-4A target contract
  Phase I-4B read-only resolver/shared-fence boundary
  O1A two-lane scheduler/idle contract

Current:
  I1-GC || I-4C1
  O1B/O1C only after their exact dependencies are ready

Next:
  I1-GD || I-4C2 -> I-4D || O1D -> O1E

Then:
  I1-GE || I-4E -> I-4F || O1F || UI-B1A

Governance after I-4:
  I-5 -> I-7 -> I-6 -> UI-B1B

Long-term:
  I-8 -> I-9 -> UI-B2 -> O3 soak
```

I1-G and O1/O2 become mandatory before long-duration memory formation or multi-day consolidation evidence is treated as reliable.

## Parallel ownership

- UI-B0 owns Home/chat transport and browser-local session state.
- I1-G owns pre-enqueue evidence, one-record replay, completion, and retention classification.
- O1A owns only round/gate/adapter-result/disposition/projection contracts.
- O1B owns sealed-record discovery and one I1-GC call.
- O1C owns queue discovery and one O0-compatible C2 call.
- O1D/O1E own policy/recovery/shutdown; O1F owns operational proof.
- O0/C2/B3/C1-5/C1-2 remain queue execution authorities.
- I-4 owns Primary lifecycle semantics and the separately reviewed Forget mutation.
- M2 and RelayCTX own retrieval eligibility and backend-bound injection.
- UI-B1 remains read-only visibility until exact operation routes separately land.

## Evaluation gates

### E1: Core RelayLM product hypothesis — available

```text
Phase I-3 complete
+ UI-B0 complete
+ O0 complete
```

E1 proves trusted-scene Primary formation through O0, separate real Home recall, observation, Correct, fresh-conversation corrected retrieval, and separation from frontend history. It does not prove direct Home-origin formation or automatic processing.

### E2: Primary MEM governance product — future

```text
Phase I-4 through I-7
+ UI-B1
+ repeatable real conversation use
```

E2 proves safe exclusion, bounded prioritization, held resolution, duplicate convergence, understandable intervention, and fresh-conversation validation.

### E3: Long-term character system — future

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
- scheduler lane no-work/busy/changed/delegated/completed counts without private identity;
- correction/Forget/pin/held/merge outcomes and stale/mixed-scope refusals;
- retrieval selection before and after each operation;
- injected revision and lifecycle evidence;
- duplicate and contradiction rates;
- worker retry/restart behavior;
- user effort required to keep memory useful.

Raw prompts, protected source, credentials, full traces, exact job/dispatch/locator/claim identity, exact retry timestamps, paths, and unrestricted memory pages must not be copied into generic telemetry.

## Preserved boundaries

- Phase I-3 remains the implemented mutation baseline.
- Phase I-4A remains the exact target contract; I-4B is the completed read-only resolver/shared-fence consumer boundary.
- I-4C1/I-4C2 are delivery subdivisions, not new lifecycle authorities.
- I1-GA and I1-GB are complete; I1-GC through I1-GE remain unimplemented and I1-G overall is in progress.
- O1A is complete only as a pure scheduler contract; O1B through O1F remain unimplemented.
- I1-G records and B2 queue records remain separate state machines.
- O1 invokes I1-GC and O0/C2; it does not absorb their semantics.
- UI-B0 and UI-B1 do not own worker, queue, scheduler, filesystem, namespace, SOUL, or mutation authority.
- Physical deletion, secure erase, purge, restore, and unhide remain separate future contracts.
- Text conversation does not imply TTS, audio, avatar, or Live2D execution.
