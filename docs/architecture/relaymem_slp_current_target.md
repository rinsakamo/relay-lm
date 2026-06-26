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
  - i1gd_durable_finalization_retention_cleanup.md
  - o0_local_one_job_runner.md
  - o1a_two_lane_scheduler_contract.md
  - o1b_sealed_i1g_replay_lane.md
  - o1c_eligible_b2_queue_lane.md
  - phase_i4b_primary_current_state_shared_fence.md
  - phase_i4c1_primary_forget_hidden_successor.md
  - phase_i4c2_primary_forget_recovery_finalization.md
  - relaymem_mvp_implementation_plan.md
  - pipeline_implementation_plan.md
  - ../PROJECT_STATUS.md
---
# RelayMEM / RelaySLP Current / Target Boundary

Last reviewed: 2026-06-26 JST

## Current implemented boundary

RelayMEM currently provides bounded store discovery, Primary/Secondary layout compatibility, retrieval priority, runtime-private snippet selection, content-free retrieval projection, gated RelayCTX injection, auditable Correct, canonical read-only Primary current-state resolution, I-4C1 hidden-successor lifecycle commit ownership, and bounded I-4C2 recovery/finalization.

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

I1-GA through I1-GD are complete:

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
  -> I1-GD one bounded maintenance pass
       -> complete bounded inventory
       -> shared per-record fence and existing root mutation lock
       -> retain sealed pending | isolate | clean known components | block
       -> isolation marker removed last
```

The normal finalizer and restart replay use the same nonblocking cross-process per-record fence and completion authority. I1-GD uses that exact per-record fence and additionally holds the existing I1-GB store-root mutation lock while classifying and cleaning. It adds no scheduler, polling, replay invocation, B3 transition, C2 execution, worker execution, M3 write, or UI.

I1-GD never deletes valid sealed evidence without completion. It publishes `relaymem.slp_durable_finalization_isolation.v0`, fsyncs and canonically rereads it before removing stable known components, and deletes the marker last after isolated retention. C1-5 protected sources and B2/B3 records are outside cleanup authority.

I1-GE remains unimplemented and is validation-only: it must prove the existing I1-GB through I1-GD production boundaries with real process exits and fresh-process restart without adding a durable schema, replay path, scheduler, queue lifecycle, worker behavior, or memory mutation.

## O1 scheduler boundary

O1A defines a pure scheduler contract without adding production scheduling:

```text
one bounded round
  -> replay lane first
       -> O1B discovery
       -> one existing I1-GC delegation
  -> queue lane second
       -> O1C discovery
       -> one existing C2 delegation
  -> stop | run_next_round | idle
```

Replay and queue remain independent state machines. A B2 record converged by replay may be selected in the same round only through independent queue-root discovery and canonical reread. Replay output is never a C2 input.

O1A is contract-only. O1B and O1C bounded production discovery and delegation are complete. O1D1 remains unimplemented and must accept the five exact scheduler gates, invoke O1B then O1C at most once each, aggregate through O1A, and return without sleeping. O1D2 fairness/retry-time/backoff/jitter/pacing, O1E stale recovery/shutdown, O1F operational validation, O2 supervision, and O3 always-on operation remain unimplemented.

O1A proposed scheduler field names are target-only. `relaylm/config.py`, `docs/config_schema.md`, `config.example.yaml`, and CLI behavior do not accept or expose them until O1D1 lands.

## Completed product integration

- Phase I-1 ordinary next-turn M2 recall and RelayCTX injection;
- exact character and namespace isolation;
- I2 real SOUL Lab observation: complete;
- Phase I-3 token-gated auditable Correct and corrected retrieval;
- Phase I-4B canonical read-only current-state resolver and shared Correct/Forget mutation fence;
- Phase I-4C1 immutable Forget prepare and deterministic hidden-successor M3e commit;
- Phase I-4C2 exact prepared recovery, operation-scoped M3f/M3g convergence, tombstone finalization, and replay.

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

### Phase I-4C2 recovery/finalization — complete

I-4C2 resumes one exact durable prepare, reuses the shared mutation fence and deterministic I-4C1 successor, performs operation-scoped index-before-log convergence through existing M3f/M3g authorities, canonically verifies page/control correlation, publishes `relaylm.mem.forget_tombstone.v0`, and supports exact replay. The public governance resolver reaches `hidden / none / false`; the ordinary correction-only M2 projection remains unchanged until I-4D.

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

Forget is not product-complete until I-4D provides ordinary retrieval exclusion and historical lifecycle overlay, I-4E provides API/UI, and I-4F provides production validation.

## Current limitations

The current runtime still lacks:

- I1-GE validation-only full crash proof;
- O1D1 one production round, O1D2 scheduling policy, O1E recovery/shutdown, O1F validation, O2 supervision, and O3 always-on operation;
- I-4D hidden/prepared/recovery/corrupt/ambiguous/unsafe/cross-scope and prior-revision M2/RelayCTX exclusion plus historical lifecycle overlay;
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

I1-G owns durable-finalization evidence, one-record replay, completion, retention classification, isolation, and evidence cleanup. O1 owns only bounded scheduling and lane aggregation. B3 owns queue lifecycle. C2 owns one queued-record coordination. C1-2 owns worker execution. RelayCTX owns backend-bound packing. SOUL Lab owns bounded read models and explicit user-operation surfaces without filesystem, queue, scheduler, or worker authority.

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

I1-G retention idempotency
  converges one expired record through immutable isolation to marker-last cleanup

O1 scheduler round identity
  is not a durable job or mutation identity
```

## Completed Primary MEM integration

```text
finalized ordinary turn
  -> I1-B request-runtime A1/A2/B1                     complete
  -> C1-5 protected source then B2 queue               complete
  -> B3 queue claim/lease/retry lifecycle              complete
  -> O0 explicit local selection and one C2 call       complete
  -> C2/C1 worker path and verified Primary MEM        complete
  -> later M2 / RelayCTX recall                        complete as I-1
  -> real Lab observation                              complete as I-2
  -> audited correction and corrected retrieval        complete as I-3
  -> canonical read-only lifecycle resolution          complete as I-4B
  -> hidden-successor lifecycle commit                 complete as I-4C1
  -> prepared recovery and tombstone finalization      complete as I-4C2
```

Phase I-4C2 adds durable recovery/finalization evidence and governance convergence, but no implemented ordinary M2/RelayCTX exclusion step exists until I-4D.

## Target migration sequence

```text
I1-GD bounded retention / isolation cleanup                         complete
I1-GE validation-only full production crash proof                  unimplemented

I-4A  lifecycle/persistence/concurrency/API/fault contract         defined target
I-4B  current-state resolver/shared Correct/Forget fence           complete
I-4C1 shared revision claim/prepared artifact/hidden successor     complete
I-4C2 exact replay/forward recovery/tombstone                      complete
I-4D  ordinary M2/RelayCTX exclusion/historical projection        unimplemented
I-4E  loopback API and SOUL Lab Forget UI                          unimplemented
I-4F  crash/race/security/fresh-conversation validation            unimplemented

O1A   two-lane round/adapter/idle contract                         complete
O1B   sealed-record discovery/I1-GC delegation                    complete
O1C   B2 discovery/O0-compatible C2 delegation                    complete
O1D1  accepted scheduler gates/one production round               unimplemented
O1D2  ordering/fairness/retry-time/backoff/jitter/pacing          unimplemented
O1E   stale recovery/cancellation/graceful shutdown               unimplemented
O1F   full operational validation                                 unimplemented
```

## Completion interpretation

M3a-M3h, C1-0 through C1-5, C2, O0, I1-GC, I1-GD, O1B, O1C, I-1 recall, I-2 observation, I-3 Correct, I-4B, I-4C1, and I-4C2 are implemented. I1-GE, I-4D, and O1D1 are the independent Wave 3 tracks. O1D1 is a bounded one-round coordinator only; O1D2, O1E, O1F, O2, and O3 remain incomplete. Forget is not product-complete until I-4D through I-4F provide retrieval exclusion, API/UI, and production validation.
