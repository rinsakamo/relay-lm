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

## Current limitations

The current runtime still lacks:

- queue scanning, daemon supervision, generalized worker pools, and retry scheduling,
- guaranteed enqueue when the process exits after visible response delivery but before the Starlette background finalizer publishes the source/queue pair,
- real SOUL Lab observation of formed and used memory,
- Secondary MEM consolidation,
- real SOUL Lab memory observation and mutation APIs.

C1-5 is restart-complete only for protected-source recovery of durably enqueued jobs. It does not claim to recover a turn that never reached durable source publication and B2 enqueue.

A1/A2/B1/B2/B3 and C1 consume exact runtime-private artifacts. They must not reconstruct private evidence from public projection, frontend metadata, visible response text, generic trace, or lookalike dictionaries.

B2 queue persistence and M3e/M3g memory persistence remain separate apply boundaries. B3 controls queue state only. M3h is read-only evidence and cannot authorize repair by itself.

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

RelaySLP may read SOUL as a protected anchor and may later emit a separately governed proposal. It never directly mutates SOUL.

## Idempotency boundary

```text
Phase 6 dispatch idempotency
  prevents duplicate logical scheduling and active execution dispatch

RelayMEM memory-write idempotency
  prevents duplicate durable memory application
```

A worker retry may be valid while a prior memory write is already exact. Dispatch keys, claim generation, lease token, and memory-write keys remain distinct.

## Active migration: Primary MEM end-to-end integration

```text
finalized ordinary turn
  -> I1-B request-runtime A1/A2/B1/B2              complete
  -> C1-5 durable protected source                  complete
  -> B3 queue claim/lease/retry lifecycle           helper complete
  -> C2 one-job claim/rehydrate/execute adapter      complete
  -> C1-0 exact protected source                    complete
  -> C1-2 one-claimed worker                        complete
  -> C1-1 M3a-M3h compose                           complete
  -> C1-3 pure outcome classification               complete
  -> C1-4 fault/crash convergence                   complete
  -> B3 retry release or terminal commit
  -> verified durable Primary MEM
  -> later RelayMEM retrieval                          complete as Phase I-1
  -> RelayCTX bounded injection                           complete as Phase I-1
  -> response uses formed memory                          complete as Phase I-1
```

The sequence is now:

1. expose real latest-run and memory outcomes through server-owned SOUL Lab APIs,
2. add one auditable Correct operation that changes later retrieval,
3. resolve or formally bound the separate pre-enqueue background-finalizer crash window,
4. keep queue scanning and daemon lifecycle as separate operational work.

I1-B, B3, C1-0 through C1-5, C2, and Phase I-1 next-turn recall are complete. Character and namespace isolation: complete. SOUL Lab real observation is next.

## Target after the active migration

After I1, later work may add:

- Secondary MEM consolidation,
- broader scheduler/service lifecycle,
- correction/forget/pin/merge APIs,
- RelaySOUL proposal handoff,
- broader recovery only where M3h evidence requires it.

## Preserved invariants

Every migration step preserves:

- visible response delivery does not wait for deferred processing,
- SLP failure does not invalidate an already valid response,
- default-off and dry-run-first rollout where applicable,
- fail-closed namespace, lineage, policy, schema, queue, lease, and source validation,
- protected content-bearing memory/SLP domains,
- content-free public diagnostics,
- autonomous ordinary memory only when RelayMEM gates pass,
- held/blocked handling for sensitive, contradictory, destructive, cross-namespace, or SOUL-affecting changes,
- separation between dispatch and memory-write idempotency,
- terminal-state immutability and exact lease fencing,
- no direct RelaySOUL mutation.

## Completion interpretation

M3a-M3h completion means the Primary MEM primitives exist. C1-1 fixes their exact order. C1-2 executes one active claim. C1-3 classifies exact outcomes. C1-4 verifies integrated convergence. C1-5 makes protected-source recovery restart-complete for durably enqueued jobs. C2 connects one exact queued record to that worker.

Phase I-1 completes the ordinary two-turn Primary MEM loop by retrieving and using the resulting memory only within the correct character/namespace scope. SOUL Lab observation and Correct operations remain later boundaries.

## Phase I-1 recall handoff

I1 next-turn Primary MEM recall: complete. Character and namespace isolation: complete. C2 remains an explicit one-record integration seam; it is not a queue
scanner or daemon. The C2 caller and ordinary request retrieval share the
character-partition resolver. Existing M2 selection is narrowed by canonical
page/index/log/namespace validation before bounded RelayCTX injection.

The pre-enqueue background-finalizer crash window remains unresolved. SOUL Lab
real observation is next and auditable Correct operation is later.
