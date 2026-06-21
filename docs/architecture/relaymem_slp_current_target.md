---
relaylm_doc_type: current_target_boundary
relaylm_authority: relaymem_relayslp_current_target
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - RelayMEM or RelaySLP producer consumer boundary changes
  - Phase 6 deferred orchestration slice lands
  - durable MEM persistence apply state changes
relaylm_not_authoritative_for:
  - repository-wide phase sequencing
  - exact RelayMEM or RelaySLP schemas
  - RelaySOUL approval contracts
relaylm_related_authority:
  - phase6_async_relayslp_bounded_slice.md
  - phase6a1_relayslp_job_admission_contract.md
  - phase6a2_relayslp_response_handoff_contract.md
  - phase6b0_relayslp_durable_queue_contract.md
  - relaymem_m3d_primary_writer_handoff.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_execution_design.md
  - memory_lifecycle_design.md
  - pipeline_implementation_plan.md
  - ../PROJECT_STATUS.md
---
# RelayMEM / RelaySLP Current / Target Boundary

## Current implemented

Current RelayMEM provides `relaymem_retrieval.v0`, bounded candidate/snippet planning, selected gated context-injection helpers, typed content-free trace projection, read-only durable-memory behavior, Primary/Secondary store-layout compatibility diagnostics, RelayMEM-M2 retrieval-priority helpers, the helper-only RelayMEM-M3a Primary MEM formation candidate boundary, the helper-only RelayMEM-M3b source-lineage/write-preflight boundary, the M3c Primary MEM page-candidate boundary, the M3d Primary writer-handoff preflight, the M3e atomic Primary MEM page writer, and the M3f Primary index/log reconciliation preflight.

RelayMEM-M3b validates content-free source lineage, derives bounded Primary MEM write-preflight operations and memory-write idempotency keys, and blocks unsupported or non-autonomous apply classes. M3c derives the deterministic page candidate. M3d revalidates the exact candidate and store target without mutation, then emits a runtime-private writer handoff plus content-free projection.

RelayMEM-M3e is a default-off, dry-run-first direct helper that may atomically publish one exact M3d-selected Primary MEM Markdown page when all explicit apply gates pass. It revalidates path, lineage, digest, page shape, and memory-write idempotency immediately before secure no-clobber publication. M3e does not update the MEM index or log, invoke RelaySLP, wire request runtime, expose a Lab API, mutate RelaySOUL, or change visible response delivery.

RelayMEM-M3f is a default-off, read-only, dry-run-only helper that consumes one exact eligible M3e receipt, securely revalidates the published page and bounded current index/log state, and derives a deterministic ordered reconciliation plan. It distinguishes exact no-op, repairable index-only/log-only states, page mismatch, and index/log conflict without writing any file.

Phase 6-A1 now provides the helper-only `relaymem.slp_job_admission_preflight.v0` boundary. It validates trigger, processing stage, correlation, namespace, source lineage, response terminal state, and persistence-policy status without queue I/O or memory writes.

Phase 6-A2 now provides the helper-only response-finalization handoff. It consumes the exact A1 private result for a finalized `turn_end` response and may create one runtime-private `relaymem.slp_enqueue_candidate.v0` artifact. The candidate is metadata-only, dry-run-only, and is omitted from public diagnostics.

Phase 6-B0 defines the durable queue contract: `relaymem.slp_durable_job.v0`, dispatch-idempotency ownership and derivation inputs, atomic create-if-absent enqueue semantics, queue states, claim/lease fencing, stale-lease and restart behavior, corruption handling, and the content-free `relaymem.slp_queue_status_projection.v0` boundary. B0 is design-only and adds no producer, key generation, queue I/O, claim, lease, or terminal-state implementation.

Current implementation still does not provide a durable RelaySLP job queue, dispatch idempotency key, scheduled/background execution, worker claim/lease state, worker invocation, Secondary MEM consolidation runtime, or Primary MEM index/log reconciliation apply. M3f planning exists; M3g apply does not.

## Current compatibility

- Retrieval still consumes a historical RelayREF-shaped input from the RelayINT-facing wrapper.
- Current query preparation may use request messages.
- `relaymem.retrieval_runtime.v1`, `relaymem.retrieval_projection.v1`, and `relaymem.slp_projection.v1` do not have current producers.
- RelayMEM-M3a through M3d artifacts are helper-only and are not request-runtime RelaySLP jobs.
- RelayMEM-M3e may apply one Primary MEM page only through explicit direct-helper gates; it is not request-runtime or worker wired and does not reconcile index/log state.
- RelayMEM-M3f may only read/revalidate and derive a private reconciliation plan; it cannot write or create index/log files.
- A1/A2 artifacts are helper-only orchestration artifacts and are not durable queue records.
- B0 schema names and state transitions are contract reservations, not runtime producers or persisted artifacts.
- RelayRUN checkpoint and retry artifacts do not currently provide a general SLP queue, worker resume, or retry executor.

## Phase 6-A and B0 boundary

[Phase 6 Asynchronous RelaySLP Bounded Slice](phase6_async_relayslp_bounded_slice.md) defines the RelayLM Core implementation sequence.

The implemented A1/A2 sequence and B0 design handoff are:

```text
completed finalized turn event
  -> A1 validate trigger, processing stage, correlation, namespace, source lineage, and terminal status
  -> admitted / held / blocked / skipped
  -> A2 create one runtime-private dry-run enqueue candidate
  -> B0 defines the future durable queue contract
  -> no queue I/O
```

A1/A2 own deferred orchestration metadata only. They consume rather than duplicate RelayMEM-M3b source-lineage and memory-write eligibility semantics. They do not invoke or replace the separately implemented M3c/M3d/M3e/M3f Primary MEM page-candidate, writer-handoff, atomic page-write, or reconciliation-preflight boundaries, and they do not own later RelayMEM-M4 consolidation semantics.

B0 assigns dispatch identity, durable queue state, duplicate prevention, claim/lease fencing, and content-free queue status to Phase 6 / RelayRUN orchestration. It requires direct runtime-private A2 consumption and forbids reconstruction from public projection, trace, frontend metadata, or visible response text.

Dispatch idempotency and memory-write idempotency remain separate:

- Phase 6 / RelayRUN orchestration prevents duplicate job enqueue, claim, or retry execution.
- RelayMEM persistence preflight and M3e apply prevent duplicate durable Primary MEM page publication; M3f independently revalidates existing page/index/log identity before proposing reconciliation.

A1 and A2 remain helper-only, default-off, dry-run-first, fail-closed, and free of durable queue I/O, worker execution, request-runtime wiring, or MEM persistence. B0 remains design-only. RelayMEM-M3e remains a separate direct-helper persistence boundary and is not evidence that Phase 6 queue or worker execution exists.

## Target architecture

The detailed RelayMEM and RelaySLP documents define the target local-first store, typed relations, lint, safety scopes, deferred candidate compiler, and gated persistence updates. Atomic Primary MEM page publication has landed as the bounded M3e helper, and deterministic Primary MEM index/log reconciliation planning has landed as the bounded read-only M3f helper. M3g index/log apply, Secondary MEM consolidation, and broader page/index/log transaction recovery remain target design until their bounded producers, consumers, apply/skip/block contracts, projections, and smoke coverage land.

[Memory Lifecycle Design](memory_lifecycle_design.md) owns the target semantic boundary between RelayCTX short-term memory, governed experience evidence, autonomous ordinary MEM formation, Primary MEM, Secondary MEM consolidation, and SOUL Lab observation/correction operations.

Ordinary MEM formation is target-autonomous by default. User approval is not the normal path for every memory candidate; review and approval are exception paths for sensitive, destructive, identity-level, low-confidence, contradictory, cross-namespace, or SOUL-affecting changes.

RelaySLP may read SOUL as a protected anchor and may emit a separately governed RelaySOUL proposal candidate, but it must never directly mutate SOUL.

## Required migration

The next bounded implementation is Phase 6-B1: validate the exact A2 runtime-private candidate and derive a deterministic Phase 6-owned dispatch identity and dry-run durable-record candidate behind default-off, dry-run-only gates, without queue I/O.

The next bounded independent RelayMEM implementation is M3g: consume one exact ready M3f plan and apply index-before-log reconciliation under explicit gates and compare-and-swap validation. M3g must not become the Phase 6 dispatch queue or imply worker execution.

Later Phase 6 B2/B3 slices must add atomic durable enqueue, duplicate/collision/corruption handling, claim/lease/stale-lease/terminal-state helpers, and content-free status projection without taking over RelayMEM memory meaning or memory-write idempotency. Worker execution, broader Phase 6 persistence reconciliation, RelayRUN retry/checkpoint integration, RelaySOUL proposal handoff, and SOUL Lab memory-operation UI remain separate later work.

Do not require the full migration to land atomically. Each slice must preserve:

- request-runtime non-blocking behavior,
- default-off and dry-run-first gates,
- content-free public diagnostics,
- protected content-bearing memory/SLP domains,
- fail-closed namespace, lineage, policy, and schema validation,
- separation between dispatch and memory-write idempotency,
- no direct RelaySOUL mutation.

See [Phase 6 Asynchronous RelaySLP Bounded Slice](phase6_async_relayslp_bounded_slice.md), [Phase 6-A1 RelaySLP Job Admission Contract](phase6a1_relayslp_job_admission_contract.md), [Phase 6-A2 RelaySLP Response-Finalization Handoff Contract](phase6a2_relayslp_response_handoff_contract.md), [Phase 6-B0 RelaySLP Durable Queue Contract](phase6b0_relayslp_durable_queue_contract.md), [RelayMEM-M3d Primary Writer Handoff Preflight](relaymem_m3d_primary_writer_handoff.md), [RelayMEM-M3e Atomic Primary MEM Page Writer](relaymem_m3e_atomic_primary_page_writer.md), [RelayMEM-M3f Primary Index/Log Reconciliation Preflight](relaymem_m3f_primary_index_log_reconciliation_preflight.md), [Memory Lifecycle Design](memory_lifecycle_design.md), [RelayMEM MVP Design](relaymem_mvp_design.md), [RelayMEM MVP Implementation Plan](relaymem_mvp_implementation_plan.md), [RelayMEM Retrieval Execution Design](relaymem_retrieval_execution_design.md), and [RelayMEM SLP Execution Design](relaymem_slp_execution_design.md).
