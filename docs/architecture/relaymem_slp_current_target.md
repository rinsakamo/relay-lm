---
relaylm_doc_type: current_target_migration
relaylm_authority: relaymem_relayslp_current_target
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - RelayMEM or RelaySLP producer consumer boundary changes
  - Phase 6 deferred orchestration slice lands
  - durable MEM persistence apply state changes
  - ordinary-runtime worker integration changes
  - I1-G or O1 boundary changes
relaylm_not_authoritative_for:
  - repository-wide phase sequencing
  - exact RelayMEM or RelaySLP schemas
  - RelaySOUL approval contracts
relaylm_related_authority:
  - phase6_async_relayslp_bounded_slice.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6c2_one_queued_primary_worker_integration.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - o0_local_one_job_runner.md
  - o1a_two_lane_scheduler_contract.md
  - phase_i4b_primary_current_state_shared_fence.md
  - phase_i4c1_primary_forget_hidden_successor.md
  - relaymem_mvp_implementation_plan.md
  - pipeline_implementation_plan.md
  - ../PROJECT_STATUS.md
---
# RelayMEM / RelaySLP Current / Target Boundary

Last reviewed: 2026-06-26 JST

## Current implemented boundary

RelayMEM currently provides bounded store discovery, Primary/Secondary layout compatibility, retrieval priority, runtime-private snippet selection, content-free retrieval projection, gated RelayCTX injection, auditable Correct, canonical read-only Primary current-state resolution, and I-4C1 hidden-successor lifecycle commit ownership.

The Primary MEM persistence chain is implemented through M3a-M3h. The Phase 6 execution boundary is implemented through C1-5 and C2, with O0 as the explicit local caller:

```text
C1-0 exact current-claim protected source
C1-1 canonical M3a-M3h compose
C1-2 lease-fenced one-already-claimed worker
C1-3 pure outcome classification
C1-4 integrated fault/crash convergence
C1-5 durable claim-independent protected source and restart rehydration
C2 one-job claim/rehydrate/execute adapter
O0 one invocation -> at most one eligible queued job
```

C1-2 executes one already-claimed canonical B3 job. C1-5 persists protected content separately from the content-free queue. C2 accepts one caller-selected queued record and connects B3 claim, C1-5 preparation, and C1-2 execution. O0 adds bounded discovery and one C2 delegation without polling or retry scheduling.

## Queue and worker compatibility anchors

Phase 6-B2 performs atomic durable enqueue behind explicit gates.

Phase 6-B3 performs default-off, dry-run-first `claim`, `renew_lease`, `retry_release`, `stale_recovery`, and `commit_terminal`. It owns queue metadata only and never executes a worker.

I1-B runs A1 -> A2 -> B1 -> C1-5 protected-source publication -> B2 queue publication after ordinary managed response finalization. It never claims or executes work inline.

C1-5 fixes source-before-queue order:

```text
finalized-turn protected capture
  -> durable protected-source commit
  -> unchanged B2 content-free queue publication
  -> optional process-local hot cache
```

C1-5 and C2 provide restart recovery for durably enqueued jobs. O0 remains default-off, operator-invoked, and one-shot.

## I1-G durable-finalization boundary

I1-GA, I1-GB, and I1-GC are complete:

```text
I1-GA contract / fault model
  -> I1-GB sealed evidence before protected visible release
  -> I1-GC caller-selected one-record replay
       -> exact finalized-turn reconstruction
       -> existing A1/A2/B1
       -> exact C1-5 source
       -> exact B2 queue
       -> canonical downstream reread
       -> immutable completion marker
```

The normal finalizer and restart replay use the same nonblocking cross-process per-record fence and completion authority. I1-GC adds no scanner, batch replay, polling, retry loop, cleanup, B3 transition, C2 execution, worker execution, M3 write, or UI.

I1-GD retention/orphan reconciliation/cleanup and I1-GE full production crash validation remain unimplemented.

## O1 scheduler boundary

O1A defines a pure scheduler contract without adding production scheduling:

```text
one bounded round
  -> replay lane first
       -> future O1B discovery
       -> one existing I1-GC delegation
  -> queue lane second
       -> future O1C discovery
       -> one existing C2 delegation
  -> stop | run_next_round | idle
```

Replay and queue remain independent state machines. A B2 record converged by replay may be selected in the same round only through independent queue-root discovery and canonical reread. Replay output is never a C2 input.

O1A is contract-only. O1B/O1C production discovery and delegation, O1D fairness/retry/backoff, O1E stale recovery/shutdown, O1F operational validation, O2 supervision, and O3 always-on operation remain unimplemented.

O1A proposed scheduler field names are target-only. `relaylm/config.py`, `docs/config_schema.md`, `config.example.yaml`, and CLI behavior do not accept or expose them.

## Completed product integration

- Phase I-1 ordinary next-turn M2 recall and RelayCTX injection;
- exact character and namespace isolation;
- I2 real SOUL Lab observation: complete;
- Phase I-3 token-gated auditable Correct and corrected retrieval;
- Phase I-4B canonical read-only current-state resolver and shared Correct/Forget mutation fence;
- Phase I-4C1 immutable Forget prepare and deterministic hidden-successor M3e commit.

Observation receipts cannot authorize repair or retrieval. They are secondary read-only evidence only.

## Current Primary mutation and lifecycle-read boundary

Phase I-3 Correct provides exact character/namespace/logical-memory/physical-page/revision validation, read-only preflight, bounded semantic diff, short-lived token, shared per-memory lock and pending-operation fence, immutable successor page, M3f/M3g convergence, prepared/applied recovery, exact replay, immutable correction receipt, M2 current-revision resolution, and historical used-memory integrity.

Phase I-4B provides:

```text
relaylm.mem.primary_current_state.v0
lifecycle_state: active | hidden
mutation_state: none | prepared | recovery_required | corrupt
retrieval_eligible: true | false
```

It resolves stable logical/current physical identity, validates page and controls, reuses the Phase I-3 `.lock`, performs read-only Forget preflight, validates a five-minute exact-binding token, exposes bounded zero-item history, and fails closed on unresolved prepared evidence.

### Phase I-4C1 hidden-successor commit — complete

I-4C1 revalidates the exact token/reason under the shared lock, publishes immutable `relaylm.mem.forget_prepared.v0`, constructs deterministic `relaymem.primary_lifecycle_page.v0`, delegates publication to M3c/M3d/M3e, canonically rereads the page, and returns `hidden / recovery_required / false`.

It stops before M3f/M3g, tombstone finalization, exact applied replay, prepared resume, and ordinary M2 exclusion.

## Defined target: Phase I-4A Forget / Hide

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
  -> Forget tombstone finalization
```

The immutable hidden successor page is lifecycle authority. The tombstone is audit/recovery evidence. Correct and Forget share one current-state resolver and one per-memory mutation fence.

## Current limitations

The current runtime still lacks:

- I1-GD retention/cleanup and I1-GE full crash validation;
- O1B through O1F automatic scheduling, O2 supervision, and O3 always-on operation;
- I-4C2 prepared resume, exact replay, forward recovery, response-loss convergence, and tombstone finalization;
- I-4D hidden/prepared/recovery/corrupt M2 and RelayCTX exclusion;
- I-4E loopback mutation API and SOUL Lab Forget UI;
- I-4F production crash/race/security/fresh-conversation validation;
- trusted scene admission for direct Home-origin formation;
- restore/unhide and physical purge;
- Pin/Unpin, Merge/Supersession, Held Apply/Discard;
- Secondary MEM consolidation and RelaySOUL mutation;
- static Lab bundle serving and TTS/audio/avatar execution.

## Ownership boundary

RelayMEM owns memory meaning, lifecycle, source lineage, current-state resolution, mutation identity, deterministic page content, page/index/log semantics, recovery classification, and Secondary MEM meaning.

Phase 6 owns dispatch admission and identity, response-finalization handoff, durable queue lifecycle, claim/lease/retry/terminal control, worker invocation, and restart/checkpoint integration.

I1-G owns durable-finalization evidence, one-record replay, completion, and future retention classification. O1 owns only bounded scheduling and lane aggregation. B3 owns queue lifecycle. C2 owns one queued-record coordination. C1-2 owns worker execution. RelayCTX owns backend-bound packing. SOUL Lab owns bounded read models and explicit user-operation surfaces without filesystem, queue, scheduler, or worker authority.

## Idempotency boundary

```text
Phase 6 dispatch idempotency
  prevents duplicate logical scheduling and active execution dispatch

RelayMEM memory-write idempotency
  prevents duplicate durable memory application

Primary mutation operation idempotency
  prevents duplicate Correct or Forget revisions and audit artifacts

I1-G finalization replay idempotency
  converges one sealed record to exact C1-5/B2 and completion

O1 scheduler round identity
  is not a durable job or mutation identity
```

## Completed Primary MEM integration

```text
finalized ordinary turn
  -> I1-B request-runtime A1/A2/B1                   complete
  -> C1-5 protected source then B2 queue             complete
  -> B3 queue claim/lease/retry lifecycle            complete
  -> O0 explicit local selection and one C2 call     complete
  -> C2/C1 worker path and verified Primary MEM      complete
  -> later M2 / RelayCTX recall                      complete as I-1
  -> real Lab observation                            complete as I-2
  -> audited correction and corrected retrieval      complete as I-3
  -> canonical read-only lifecycle resolution        complete as I-4B
  -> hidden-successor lifecycle commit                complete as I-4C1
```

Phase I-4C1 adds durable hidden-lifecycle evidence, but no implemented ordinary M2/RelayCTX exclusion step exists until I-4D.

## Target migration sequence

```text
I1-GD retention / cleanup                                         unimplemented
I1-GE full production crash validation                            unimplemented

I-4A  lifecycle/persistence/concurrency/API/fault contract         defined target
I-4B  current-state resolver/shared Correct/Forget fence           complete
I-4C1 shared revision claim/prepared artifact/hidden successor     complete
I-4C2 exact replay/forward recovery/tombstone                      unimplemented
I-4D  M3 convergence/M2 exclusion/historical projection           unimplemented
I-4E  loopback API and SOUL Lab Forget UI                          unimplemented
I-4F  crash/race/security/fresh-conversation validation            unimplemented

O1A   two-lane round/adapter/idle contract                         complete
O1B   sealed-record discovery/I1-GC delegation                    unimplemented
O1C   B2 discovery/O0-compatible C2 delegation                    unimplemented
O1D   ordering/fairness/retry-time/backoff/jitter                  unimplemented
O1E   stale recovery/cancellation/graceful shutdown               unimplemented
O1F   full operational validation                                  unimplemented
```

## Completion interpretation

M3a-M3h, C1-0 through C1-5, C2, O0, I1-GC, I-1 recall, I-2 observation, I-3 Correct, I-4B, and I-4C1 are implemented. Forget is not product-complete until I-4C2 through I-4F provide recovery/tombstone, retrieval exclusion, API/UI, and production validation.

<!-- O1B_CURRENT_BOUNDARY -->
### O1B sealed replay-lane discovery — complete

O1B owns one bounded secure inventory of the configured durable-finalization root, exact grouping and eligibility classification, lexicographic selection of one sealed-pending locator, canonical selected-locator reread, and at most one delegation to the existing I1-GC authority. It owns no replay algorithm, completion publication, queue lane, C2/worker execution, polling, fairness, backoff, shutdown, supervision, or always-on operation. O1C through O1F, O2, and O3 remain unimplemented.
