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
relaylm_not_authoritative_for:
  - repository-wide phase sequencing
  - exact RelayMEM or RelaySLP schemas
  - RelaySOUL approval contracts
relaylm_related_authority:
  - phase6_async_relayslp_bounded_slice.md
  - phase6b0_relayslp_durable_queue_contract.md
  - phase6b1_relayslp_dispatch_preflight.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_primary_worker_outcome_classifier.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6c2_one_queued_primary_worker_integration.md
  - o0_local_one_job_runner.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i2_real_soul_lab_observation.md
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4_primary_mem_forget_hide_contract.md
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

The Primary MEM formation/persistence chain is implemented through:

```text
M3a formation candidate
M3b source lineage and write preflight
M3c deterministic Primary page candidate
M3d writer handoff and store-target preflight
M3e atomic no-clobber page publication
M3f read-only index/log reconciliation plan
M3g gated index-before-log reconciliation apply
M3h read-only receipt/store recovery audit
```

The Phase 6 execution boundary is implemented through C1-5 and C2, with O0 as the explicit local caller:

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

Completed product integration:

- Phase I-1 ordinary next-turn M2 recall and RelayCTX injection;
- exact character and namespace isolation;
- Phase I-2 real read-only Lab observation;
- Phase I-3 token-gated auditable Correct and corrected retrieval;
- Phase I-4B canonical read-only current-state resolver and shared Correct/Forget mutation fence;
- Phase I-4C1 immutable Forget prepare and deterministic hidden-successor M3e commit.

I2 real SOUL Lab observation: complete. Observation receipts cannot authorize repair or retrieval.

Phase I-4B completes the canonical read-only Primary current-state resolver. Phase I-4C1 consumes it to publish exact prepared evidence and a hidden successor while preserving current M2 and RelayCTX behavior until I-4D.

## Compatibility status anchors

Phase 6-B1 consumes the A2 runtime-private handoff and performs no queue I/O.

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

O0 remains default-off, operator-invoked, and one-shot. O1 polling/retry scheduling, O2 supervision, and O3 always-on operation remain unimplemented.

## Current Primary mutation and lifecycle-read boundary

Phase I-3 Correct provides exact character/namespace/logical-memory/physical-page/revision validation, read-only preflight, bounded semantic diff, short-lived token, per-memory lock and pending-operation fence, immutable successor page, M3f/M3g convergence, prepared/applied recovery, exact replay, immutable correction receipt, M2 current-revision resolution, and historical used-memory integrity.

Phase I-4B now provides:

```text
relaylm.mem.primary_current_state.v0
lifecycle_state: active | hidden
mutation_state: none | prepared | recovery_required | corrupt
retrieval_eligible: true | false
```

The I-4B implementation:

- resolves one stable logical identity and exact current physical revision;
- validates page and control state with bounded content-free reasons;
- preserves the Phase I-3 per-memory `.lock` path as the shared Correct/Forget fence;
- implements read-only Forget preflight;
- validates an exact-binding five-minute Forget token;
- exposes bounded zero-item history;
- classifies valid unresolved prepared evidence as `recovery_required` and retrieval-ineligible.

I-4B itself performs no hidden successor write, prepared Forget artifact, tombstone, index/log mutation, loopback route, or browser behavior change. Ordinary M2 and RelayCTX behavior remains unchanged until I-4D.

### Phase I-4C1 hidden-successor commit — complete

I-4C1 revalidates the exact token/reason under the shared lock, publishes immutable `relaylm.mem.forget_prepared.v0`, deterministically constructs `relaymem.primary_lifecycle_page.v0`, delegates publication to existing M3c/M3d/M3e authority, canonically rereads the page, and returns `hidden / recovery_required / false`. It stops before M3f/M3g, tombstone, exact replay, and M2 exclusion.

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

- I1-GC one-record replay/completion convergence, I1-GD cleanup, and I1-GE full crash validation despite completed I1-GA/I1-GB;
- O1 automatic queue scanning and retry scheduling, O2 supervised service, and O3 always-on operation;
- I-4C2 prepared resume, exact replay/response-loss convergence, forward recovery, and Forget tombstone finalization;
- durable applied Forget history artifacts and projection beyond the I-4B zero-item read-only boundary;
- I-4D hidden/prepared/recovery/corrupt M2 and RelayCTX exclusion;
- I-4E loopback mutation API and SOUL Lab Forget UI;
- I-4F production crash/race/security/fresh-conversation validation;
- trusted scene admission for direct Home-origin formation;
- restore/unhide and physical purge;
- Pin/Unpin, Merge/Supersession, Held Apply/Discard;
- Secondary MEM consolidation and RelaySOUL mutation;
- static Lab bundle serving and TTS/audio/avatar execution.

C1-5 is restart-complete only for protected-source recovery of durably enqueued jobs. I1-GB persists sealed pre-release evidence for turns not yet converged to C1-5/B2, but restart discovery/replay and completion are I1-GC work.

## Ownership boundary

RelayMEM owns memory meaning, lifecycle, source lineage, current-state resolution, mutation-operation identity, deterministic page content, page/index/log semantics, recovery classification, and Secondary MEM consolidation meaning.

Phase 6 / RelayRUN owns dispatch admission and identity, response-finalization handoff, durable-finalization publication, durable queue lifecycle, claim/lease/retry/terminal control, worker invocation, and restart/checkpoint integration.

RelayCTX owns backend-bound packing and injection. SOUL Lab owns bounded read models and explicit user-operation surfaces without filesystem, queue, or worker authority. RelaySLP may read SOUL as a protected anchor and may later emit separately governed proposals; it never mutates SOUL directly.

## Idempotency boundary

```text
Phase 6 dispatch idempotency
  prevents duplicate logical scheduling and active execution dispatch

RelayMEM memory-write idempotency
  prevents duplicate durable memory application

Primary mutation operation idempotency
  prevents duplicate Correct or Forget revisions and audit artifacts

Lab observation receipt identity
  prevents duplicate read-model evidence without changing authority
```

Worker retry, memory write, observation receipt, correction replay, Forget replay, and durable-finalization replay remain separate identities.

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

Phase I-4C1 adds a durable hidden-lifecycle commit, but no implemented M2/RelayCTX exclusion step yet exists in the ordinary retrieval path.

## Target migration sequence

```text
I-4A  lifecycle/persistence/concurrency/API/fault contract              defined target
I-4B  current-state resolver and shared Correct/Forget fence            complete
I-4C1 shared revision claim, prepared artifact, hidden successor         complete
I-4C2 exact replay, forward recovery, tombstone finalization             unimplemented
I-4D  M3 convergence, M2/RelayCTX exclusion, historical projection      unimplemented
I-4E  loopback API and SOUL Lab Forget UI                                unimplemented
I-4F  crash/race/security/fresh-conversation validation                  unimplemented
```

I-4B completed the narrow resolver/fence refactor and I-4C1 consumed it for the hidden lifecycle commit while preserving M2 relevance ownership and avoiding a broad generic mutation framework. I-4C2 and I-4D continue from this boundary without absorbing queue or worker semantics.

## Historical evidence target

Past used-memory receipts remain immutable. A future projection may show:

```text
injected_summary: historical backend-bound representation
current_summary: null when current lifecycle is hidden
current_lifecycle_state: hidden
lifecycle_changed: true
```

The past request is never rewritten to imply the memory was not used.

## Preserved invariants

Every migration step preserves visible-response independence, exact scope and lineage, protected content domains, bounded public projections, separate idempotency domains, fail-closed corruption handling, no browser filesystem/lifecycle authority, no mock mutation fallback, no direct RelaySOUL mutation, and no re-exposure of a prepared or committed hidden memory.

Forget is not physical deletion, secure erase, purge, restore/unhide, or legal erasure.

## Completion interpretation

M3a-M3h, C1-0 through C1-5, C2, O0, I-1 recall, I-2 observation, I-3 Correct, I-4B read-only current-state/fence/preflight-token-history, and I-4C1 hidden-successor commit are implemented. I-4A is the target contract. Forget is not product-complete until I-4C2 through I-4F provide recovery/tombstone, retrieval exclusion, API/UI, and production validation.

I1-GA and I1-GB are complete. I1-GC replay/completion, I1-GD cleanup, and I1-GE full crash validation remain unimplemented. UI-B0 and O0 are complete; O1/O2/O3 and I-4C2 through I-4F remain separate work.
