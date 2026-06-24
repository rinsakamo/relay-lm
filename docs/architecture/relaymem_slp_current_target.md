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

Phase I-1 completes the ordinary second-turn path:

```text
validated character partition
  -> existing M2 candidate discovery
  -> exact Primary page/index/log/namespace validation
  -> bounded selected-memory artifact
  -> existing RelayCTX injection
  -> backend-bound request
  -> completed response generation
```

Phase I-2 completes real read-only observation:

```text
completed managed run and worker outcomes
  -> bounded durable observation evidence where required
  -> pure character/namespace-scoped projection
  -> loopback-only Lab API
  -> strict browser validation
  -> server-owned Lab Observation UI
```

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

## Current limitations

The current runtime still lacks:

- queue scanning, daemon supervision, generalized worker pools, and retry scheduling,
- guaranteed enqueue when the process exits after visible response delivery but before the Starlette background finalizer publishes the source/queue pair,
- Secondary MEM consolidation,
- auditable Correct and later forget/pin/merge/held-review mutations,
- RelaySOUL mutation,
- static Lab bundle serving and TTS/audio/avatar execution.

C1-5 is restart-complete only for protected-source recovery of durably enqueued jobs. It does not claim to recover a turn that never reached durable source publication and B2 enqueue. This pre-enqueue background-finalizer crash window remains separate from Phase I-2 observation durability.

A1/A2/B1/B2/B3 and C1 consume exact runtime-private artifacts. They must not reconstruct private evidence from public projection, frontend metadata, visible response text, generic trace, or lookalike dictionaries.

B2 queue persistence and M3e/M3g memory persistence remain separate apply boundaries. B3 controls queue state only. M3h is read-only evidence and cannot authorize repair by itself. Phase I-2 receipts are also read-only evidence and cannot authorize repair or retrieval.

## Ownership boundary

RelayMEM owns:

- memory meaning and safety scope,
- source lineage,
- memory-write idempotency,
- deterministic page content,
- page/index/log apply semantics,
- recovery classification,
- Secondary MEM consolidation meaning.

Phase 6 / RelayRUN owns:

- dispatch admission and identity,
- response-finalization handoff,
- durable queue lifecycle,
- claim/lease/retry/terminal control,
- worker invocation control,
- restart/checkpoint integration.

RelayCTX owns backend-bound packing and injection. SOUL Lab observation records only bounded evidence of the already completed outcome. RelaySLP may read SOUL as a protected anchor and may later emit a separately governed proposal. It never directly mutates SOUL.

## Idempotency boundary

```text
Phase 6 dispatch idempotency
  prevents duplicate logical scheduling and active execution dispatch

RelayMEM memory-write idempotency
  prevents duplicate durable memory application

Lab observation receipt identity
  prevents duplicate read-model evidence without changing either authority
```

A worker retry may be valid while a prior memory write is already exact. Dispatch keys, claim generation, lease token, memory-write keys, and observation receipt correlations remain distinct.

## Completed Primary MEM integration

```text
finalized ordinary turn
  -> I1-B request-runtime A1/A2/B1/B2              complete
  -> C1-5 durable protected source                  complete
  -> B3 queue claim/lease/retry lifecycle           complete helper boundary
  -> C2 one-job claim/rehydrate/execute adapter      complete
  -> C1-0 exact protected source                    complete
  -> C1-2 one-claimed worker                        complete
  -> C1-1 M3a-M3h compose                           complete
  -> C1-3 pure outcome classification               complete
  -> C1-4 fault/crash convergence                   complete
  -> verified durable Primary MEM                   complete
  -> later RelayMEM retrieval                       complete as Phase I-1
  -> RelayCTX bounded injection                     complete as Phase I-1
  -> response uses formed memory                    complete as Phase I-1
  -> real Lab observation                           complete as Phase I-2
```

## Phase I-2 observation boundary

The observation API exposes only bounded, exact, server-owned projections for:

- latest completed managed run,
- recently formed validated Primary memories,
- held and blocked outcomes,
- memories actually included in the latest backend-bound request.

The API requires explicit character and namespace scope. It reuses UI-A7's loopback configured-host and actual-peer checks, returns `Cache-Control: no-store`, and refuses mutation methods.

Existing durable Primary state is reused for formed memory. Minimal durable receipts are used only for worker outcome and used-memory evidence that otherwise would not survive restart. Receipts are not M1/M2 candidates, not protected source, not B3 records, and not repair instructions.

## Active migration: Phase I-3 auditable Correct

The next sequence is:

1. accept one explicit Correct request for one validated observed Primary memory,
2. validate exact character, namespace, current memory identity, page, index, and log state,
3. build a bounded correction preflight,
4. apply one atomic authoritative update while preserving prior representation and provenance,
5. persist audit evidence distinct from observation receipts,
6. verify a later M2 retrieval uses the corrected representation.

Forget, pin/unpin, merge, held apply/discard, broader scheduler/service lifecycle, and RelaySOUL proposal handoff remain later.

## Preserved invariants

Every migration step preserves:

- visible response delivery does not wait for deferred processing,
- SLP or observation failure does not invalidate an already valid response,
- default-off and dry-run-first rollout where applicable,
- fail-closed namespace, lineage, policy, schema, queue, lease, source, and receipt validation,
- protected content-bearing memory/SLP domains,
- bounded explicit Lab inspection without raw prompt/transcript/source disclosure,
- content-free generic public diagnostics,
- autonomous ordinary memory only when RelayMEM gates pass,
- held/blocked handling for sensitive, contradictory, destructive, cross-namespace, or SOUL-affecting changes,
- separation between dispatch, memory-write, and observation idempotency,
- terminal-state immutability and exact lease fencing,
- no direct RelaySOUL mutation.

## Completion interpretation

M3a-M3h completion means the Primary MEM primitives exist. C1-1 fixes their exact order. C1-2 executes one active claim. C1-3 classifies exact outcomes. C1-4 verifies integrated convergence. C1-5 makes protected-source recovery restart-complete for durably enqueued jobs. C2 connects one exact queued record to that worker.

Phase I-1 completes the ordinary two-turn Primary MEM loop within the correct character/namespace scope. Phase I-2 completes bounded real observation of that loop. Phase I-3 auditable Correct is next.

## Phase I-2 / I1-G status

I1 next-turn Primary MEM recall: complete.
Character and namespace isolation: complete.
I2 real SOUL Lab observation: complete.
I1-G pre-enqueue background-finalizer durability remains unresolved.

<!-- phase-i3-auditable-primary-mem-correct -->
## Phase I-3 auditable Primary MEM Correct — complete (2026-06-24)

Phase I-3 completes the first real observe/correct/retrieve loop. A formed Primary MEM observed through Phase I-2 can be corrected through read-only preflight, bounded semantic diff, explicit short-lived-token apply, immutable successor-page publication through the existing M3e boundary, canonical M3f/M3g index/log convergence, and immutable audit receipt finalization. Existing M2 retrieval resolves only the corrected current revision and existing RelayCTX injection remains the sole prompt path.

Character/namespace isolation, stable logical memory identity, no-clobber publication, exact operation idempotency, one-winner revision fencing, crash recovery, and historical used-memory integrity are preserved. Correction reason, audit receipt, paths, digests, lineage, queue/lease state, and prior full pages are not retrieval inputs or public prompt content.

Authority and exact contracts: `docs/architecture/phase_i3_auditable_primary_mem_correct.md`.

Still separate and unresolved: the I1-G process-exit window after visible-response delivery but before background-finalizer protected-source and B2 queue publication. Phase I-3 does not implement forget, pin/unpin, merge, held apply/discard, Secondary MEM consolidation, RelaySOUL mutation, queue scanner/scheduler/daemon, static UI serving, or TTS/audio/avatar execution.
