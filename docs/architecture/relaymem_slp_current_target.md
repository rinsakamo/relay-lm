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
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i2_real_soul_lab_observation.md
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4_primary_mem_forget_hide_contract.md
  - relaymem_mvp_implementation_plan.md
  - pipeline_implementation_plan.md
  - ../PROJECT_STATUS.md
---
# RelayMEM / RelaySLP Current / Target Boundary

## Current implemented boundary

RelayMEM currently provides bounded store discovery, Primary/Secondary layout compatibility, retrieval priority, runtime-private snippet selection, content-free retrieval projection, and gated RelayCTX injection.

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

The Phase 6 integration boundary is implemented through C1-5 and C2:

```text
C1-0 exact current-claim protected source
C1-1 canonical M3a-M3h compose
C1-2 lease-fenced one-already-claimed worker
C1-3 pure outcome classification
C1-4 integrated fault/crash convergence
C1-5 durable claim-independent protected source and restart rehydration
C2 one-job claim/rehydrate/execute adapter
```

C1-2 executes only one already-claimed canonical B3 job. It does not scan or select queued work. C1-5 persists protected content separately from the content-free queue and creates a fresh C1-0 source/scope for each current claim. C2 accepts one caller-selected exact queued record and connects canonical B3 claim, C1-5 preparation, and unchanged C1-2 execution.

Phase I-1 completes the ordinary second-turn path through existing M2, exact Primary page/index/log/namespace validation, bounded selected-memory construction, existing RelayCTX injection, and completed backend response generation.

Phase I-2 completes real read-only observation through bounded durable evidence, character/namespace-scoped projection, loopback-only Lab API, strict browser validation, and server-owned rendering.

Phase I-3 completes token-gated auditable Correct and later M2 resolution of only the corrected current revision.

## Compatibility status anchors

Phase 6-B1 is the exact consumer of the A2 runtime-private handoff and performs no queue I/O.

Phase 6-B2 performs atomic durable enqueue behind explicit gates.

Phase 6-B3 performs default-off, dry-run-first `claim`, `renew_lease`, `retry_release`, `stale_recovery`, and `commit_terminal`. It owns queue metadata only and never executes a worker.

I1-B runs A1 -> A2 -> B1 -> B2 after ordinary managed non-stream/stream response finalization. It never claims or executes work inline.

C1-5 fixes publication order:

```text
finalized-turn protected capture
  -> durable protected-source commit
  -> unchanged B2 content-free queue publication
  -> optional process-local hot cache
```

A claim resolves the capture from the hot cache or durable artifact, validates identity/integrity, creates a fresh one-shot scope, and invokes the canonical C1-0 builder.

I1 next-turn Primary MEM recall: complete. Character and namespace isolation: complete.

I2 real SOUL Lab observation: complete. The observation surface is read-only and cannot become memory or queue authority.

I3 auditable Primary MEM Correct: complete.

## Current Phase I-3 mutation boundary

Correct currently provides exact character/namespace/logical-memory/physical-page/revision validation, read-only preflight, bounded semantic diff, opaque short-lived token, per-memory lock and pending-operation fence, immutable successor page, M3f/M3g convergence, prepared/applied recovery, exact replay, immutable correction receipt, M2 current-revision resolution, and historical used-memory integrity.

The current resolver is correction-specific. It does not yet understand a canonical `hidden` lifecycle state.

## Defined target: Phase I-4A Forget / Hide contract

Phase I-4A defines but does not implement:

```text
Forget            user-facing explicit operation
hidden            canonical current retrieval-ineligible lifecycle state
Forget tombstone  immutable runtime-private audit/recovery artifact
```

Persistence decision:

```text
revision N active
  -> exact prepared operation and fail-closed quarantine
  -> immutable successor Primary page through M3e
revision N+1 hidden
  -> M3f/M3g index-before-log convergence
  -> M2 exclusion verification
  -> Forget tombstone finalization
```

Candidate A is authoritative: lifecycle advances with an immutable successor page and revision. A tombstone is audit/recovery evidence, not a second sidecar current-state authority.

Target canonical resolver:

```text
relaylm.mem.primary_current_state.v0
lifecycle_state: active | hidden
mutation_state: none | prepared | recovery_required | corrupt
retrieval_eligible: true | false
```

Correct and Forget must share one per-memory lock namespace, pending-operation fence, operation identity lookup, and revision claim. At most one operation may consume a current revision.

Prepared, recovery-required, corrupt, hidden, and prior physical revisions are fail-closed for ordinary M2 retrieval. No correction-specific or Forget-specific retriever is introduced.

## Current limitations

The current runtime still lacks:

- queue scanning, daemon supervision, generalized worker pools, and retry scheduling,
- guaranteed enqueue when the process exits after visible response delivery but before the Starlette background finalizer publishes the source/queue pair,
- I1-G durable-finalization production publication/replay/cleanup despite the completed I1-GA target contract,
- the canonical lifecycle resolver defined by I-4A,
- production Forget preflight/apply/history artifacts,
- hidden-state M2 exclusion and historical lifecycle projection,
- SOUL Lab Forget UI,
- restore / unhide and physical purge,
- Pin/Unpin, Merge/Supersession, Held Apply/Discard,
- Secondary MEM consolidation,
- RelaySOUL mutation,
- static Lab bundle serving and TTS/audio/avatar execution.

C1-5 is restart-complete only for protected-source recovery of durably enqueued jobs. It does not claim to recover a turn that never reached durable source publication and B2 enqueue. I1-G pre-enqueue background-finalizer durability remains unresolved.

A1/A2/B1/B2/B3 and C1 consume exact runtime-private artifacts. They must not reconstruct private evidence from public projection, frontend metadata, visible response text, generic trace, or lookalike dictionaries.

B2 queue persistence, M3e/M3g memory persistence, Primary mutation operation identity, and observation receipt identity remain separate boundaries.

## Ownership boundary

RelayMEM owns memory meaning and safety scope, source lineage, memory-write and mutation-operation identity, deterministic page content, lifecycle/current-state resolution, page/index/log apply semantics, recovery classification, and Secondary MEM consolidation meaning.

Phase 6 / RelayRUN owns dispatch admission and identity, response-finalization handoff, durable queue lifecycle, claim/lease/retry/terminal control, worker invocation control, and restart/checkpoint integration.

RelayCTX owns backend-bound packing and injection. SOUL Lab observation records only bounded evidence of the already completed outcome. RelaySLP may read SOUL as a protected anchor and may later emit a separately governed proposal. It never directly mutates SOUL.

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

A worker retry, exact memory write, observation receipt, correction replay, and future Forget replay must not be conflated.

## Completed Primary MEM integration

```text
finalized ordinary turn
  -> I1-B request-runtime A1/A2/B1/B2              complete
  -> C1-5 durable protected source                  complete
  -> B3 queue claim/lease/retry lifecycle           complete helper boundary
  -> C2 one-job claim/rehydrate/execute adapter      complete
  -> C1-0/C1-2/C1-1/C1-3/C1-4 worker path          complete
  -> verified durable Primary MEM                   complete
  -> later RelayMEM retrieval                       complete as Phase I-1
  -> RelayCTX bounded injection                     complete as Phase I-1
  -> real Lab observation                           complete as Phase I-2
  -> audited correction and corrected retrieval      complete as Phase I-3
```

Phase I-4A does not add an implemented runtime step to this path.

## Phase I-2 observation boundary

The observation API exposes only bounded, exact, server-owned projections for latest completed managed run, recently formed validated Primary memories, held/blocked outcomes, and memories actually included in the latest backend-bound request.

Existing durable Primary state is reused for formed memory. Minimal durable observation receipts are used only for worker outcome and used-memory evidence that otherwise would not survive restart. Receipts are not M1/M2 candidates, protected source, B3 records, lifecycle authority, or repair instructions.

## Target migration sequence

```text
I-4A  exact lifecycle/persistence/concurrency/API/fault contract      defined target
I-4B  common current-state resolver and shared Correct/Forget fence   unimplemented
I-4C  hidden successor apply and prepared/tombstone artifacts         unimplemented
I-4D  M3 convergence, M2 exclusion, historical lifecycle projection  unimplemented
I-4E  loopback API and SOUL Lab Forget UI                             unimplemented
I-4F  crash/race/security/fresh-conversation validation                unimplemented
```

I-4B may narrow-refactor the current correction resolver. It must preserve M2 relevance ownership and avoid a broad generic mutation framework.

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

Forget is not a physical deletion, secure erase, purge, restore/unhide, or legal-erasure feature.

## Completion interpretation

M3a-M3h primitives, C1-0 through C1-5, C2, I-1 recall, I-2 observation, and I-3 Correct are implemented. I-4A is a defined target contract. Forget is not implemented until I-4B through I-4F provide producer, consumer, apply, retrieval exclusion, UI, and validation coverage.

## Phase I-2 / I1-G status

I1 next-turn Primary MEM recall: complete.
Character and namespace isolation: complete.
I2 real SOUL Lab observation: complete.
I3 auditable Primary MEM Correct: complete.
I1-G pre-enqueue background-finalizer durability remains unresolved.

UI-B0 is complete. I1-GA is complete as a contract/fault model only. O0, queue scanner / daemon operation, supervised worker status, and Phase I-4 runtime status remain unchanged by I-4A.
