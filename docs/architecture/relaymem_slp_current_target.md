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
  - phase6b1_relayslp_dispatch_preflight.md
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

Current RelayMEM provides `relaymem_retrieval.v0`, bounded candidate/snippet planning, selected gated context-injection helpers, typed content-free trace projection, Primary/Secondary store-layout compatibility diagnostics, RelayMEM-M2 retrieval-priority helpers, the helper-only RelayMEM-M3a Primary MEM formation candidate boundary, M3b source-lineage/write-preflight, M3c Primary MEM page-candidate construction, M3d Primary writer-handoff preflight, M3e atomic Primary MEM page publication, and M3f read-only Primary MEM index/log reconciliation planning.

RelayMEM-M3e may atomically publish one exact M3d-selected Primary MEM Markdown page only through explicit default-off apply gates. RelayMEM-M3f consumes an exact M3e receipt, revalidates the published page and current bounded index/log files, and emits a deterministic dry-run reconciliation plan. M3f does not mutate the index, log, page, queue, trace, or visible response.

Phase 6-A1 provides the helper-only `relaymem.slp_job_admission_preflight.v0` boundary. Phase 6-A2 consumes the exact A1 private result for a finalized `turn_end` response and may create one runtime-private `relaymem.slp_enqueue_candidate.v0` artifact without queue I/O.

Phase 6-B0 defines the durable queue contract, dispatch-idempotency ownership, atomic enqueue and duplicate/collision rules, queue states, claim/lease fencing, restart/corruption behavior, retry-release boundary, and the content-free `relaymem.slp_queue_status_projection.v0` schema.

Phase 6-B1 now implements the default-off, read-only, dry-run-only `relaymem.slp_dispatch_preflight.v0` helper. It accepts only the exact in-process A2 result, revalidates the exact A2 enqueue candidate, derives a versioned deterministic dispatch-idempotency key and separately domain-separated deterministic job ID, and emits one runtime-private initial `relaymem.slp_durable_job.v0` candidate plus a content-free queue projection. It performs no queue I/O or enqueue.

Current implementation still does not provide atomic durable RelaySLP enqueue, duplicate/collision lookup, scheduled/background execution, worker claim/lease state, retry transitions, worker invocation, Secondary MEM consolidation runtime, or Primary MEM index/log apply.

## Current compatibility

- Retrieval still consumes a historical RelayREF-shaped input from the RelayINT-facing wrapper.
- Current query preparation may use request messages.
- `relaymem.retrieval_runtime.v1`, `relaymem.retrieval_projection.v1`, and `relaymem.slp_projection.v1` do not have current producers.
- RelayMEM-M3a through M3f remain direct helper boundaries and are not request-runtime RelaySLP jobs.
- M3e page publication and M3f reconciliation planning use RelayMEM memory-write identity, not Phase 6 dispatch identity.
- A1/A2 artifacts are helper-only orchestration artifacts and are not durable queue records.
- B1 produces a runtime-private durable-job candidate, but it neither persists nor checks the candidate against a queue backend.
- RelayRUN checkpoint and retry artifacts do not currently provide a general SLP queue, worker resume, or retry executor.

## Phase 6-A through B1 boundary

[Phase 6 Asynchronous RelaySLP Bounded Slice](phase6_async_relayslp_bounded_slice.md) defines the RelayLM Core implementation sequence.

```text
completed finalized turn event
  -> A1 validate trigger, stage, correlation, namespace, lineage, policy, and terminal status
  -> A2 create one exact runtime-private dry-run enqueue candidate
  -> B0 define durable queue identity and state invariants
  -> B1 derive deterministic dispatch/job identity and queued durable-job candidate
  -> no queue I/O
```

A1/A2 own deferred orchestration metadata only. They consume rather than duplicate RelayMEM source-lineage and memory-write eligibility semantics. They do not invoke or replace the independently implemented M3c/M3d/M3e/M3f page and index/log boundaries.

B1 generates Phase 6-owned dispatch identity from only the B0 canonical identity tuple. It excludes admission status, runtime terminal status, persistence-policy status, timestamps, random values, queue paths, claim/lease/retry metadata, memory-write idempotency, and raw content. `job_id` is deterministically derived in a separate domain and is never an input to the dispatch key.

Dispatch idempotency and memory-write idempotency remain separate:

- Phase 6 / RelayRUN orchestration will prevent duplicate durable job enqueue, active claim, and execution dispatch.
- RelayMEM persistence preflight/apply prevents duplicate durable memory publication and reconciliation apply.

B1 creates only the first identity domain and does not write memory. RelayMEM-M3e/M3f remain separate direct-helper persistence boundaries and are not evidence that Phase 6 queue or worker execution exists.

## Target architecture

The target remains a detached post-response durable queue followed by bounded claim/lease helpers and later worker execution through RelayMEM-owned artifacts. Queue failure must not change or delay the already-finalized visible response.

Atomic Primary MEM page publication has landed as M3e and deterministic index/log reconciliation planning has landed as M3f. Index/log mutation and crash-safe reconciliation apply remain later RelayMEM work. Secondary MEM consolidation remains a later RelaySLP/RelayMEM boundary.

[Memory Lifecycle Design](memory_lifecycle_design.md) owns the semantic boundary between RelayCTX short-term memory, governed experience evidence, autonomous ordinary MEM formation, Primary MEM, Secondary MEM consolidation, and SOUL Lab observation/correction operations.

RelaySLP may read SOUL as a protected anchor and may emit a separately governed RelaySOUL proposal candidate, but it must never directly mutate SOUL.

## Required migration

The next bounded Phase 6 implementation is Phase 6-B2: consume only an exact validated B1 result and durable-job candidate, assign durable timestamps, and perform gated atomic create-if-absent enqueue with explicit `enqueued_new`, `duplicate_existing`, `blocked_collision`, `blocked_corrupt`, and `write_failed` outcomes.

B2 must not invoke a worker or add claim/lease/retry mutation. Phase 6-B3 remains responsible for structurally fenced claim, lease renewal, retry release, stale-lease recovery, and terminal-state helpers. Worker execution, RelayRUN retry/checkpoint integration, Secondary MEM consolidation, RelaySOUL proposal handoff, and SOUL Lab memory-operation UI remain separate later work.

Each slice must preserve:

- request-runtime and visible-response independence,
- default-off and dry-run-first gates,
- content-free public diagnostics,
- protected runtime-private candidates and identities,
- fail-closed namespace, lineage, policy, schema, and state validation,
- strict separation between dispatch and memory-write idempotency,
- no direct RelaySOUL mutation.

See [Phase 6 Asynchronous RelaySLP Bounded Slice](phase6_async_relayslp_bounded_slice.md), [Phase 6-A1 RelaySLP Job Admission Contract](phase6a1_relayslp_job_admission_contract.md), [Phase 6-A2 RelaySLP Response-Finalization Handoff Contract](phase6a2_relayslp_response_handoff_contract.md), [Phase 6-B0 RelaySLP Durable Queue Contract](phase6b0_relayslp_durable_queue_contract.md), [Phase 6-B1 RelaySLP Dispatch Preflight](phase6b1_relayslp_dispatch_preflight.md), [RelayMEM-M3e Atomic Primary MEM Page Writer](relaymem_m3e_atomic_primary_page_writer.md), [RelayMEM-M3f Primary MEM Index/Log Reconciliation Preflight](relaymem_m3f_primary_index_log_reconciliation_preflight.md), [Memory Lifecycle Design](memory_lifecycle_design.md), [RelayMEM MVP Implementation Plan](relaymem_mvp_implementation_plan.md), and [RelayMEM SLP Execution Design](relaymem_slp_execution_design.md).
