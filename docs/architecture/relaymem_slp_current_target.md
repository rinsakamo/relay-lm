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
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_execution_design.md
  - memory_lifecycle_design.md
  - pipeline_implementation_plan.md
  - ../PROJECT_STATUS.md
---
# RelayMEM / RelaySLP Current / Target Boundary

## Current implemented

Current RelayMEM provides `relaymem_retrieval.v0`, bounded candidate/snippet planning, selected gated context-injection helpers, typed content-free trace projection, read-only durable-memory behavior, Primary/Secondary store-layout compatibility diagnostics, RelayMEM-M2 retrieval-priority helpers, the helper-only RelayMEM-M3a Primary MEM formation candidate boundary, and the helper-only RelayMEM-M3b Primary MEM source-lineage/write-preflight boundary.

RelayMEM-M3b validates content-free source lineage, derives bounded Primary MEM write-preflight operations and memory-write idempotency keys, and blocks unsupported or non-autonomous apply classes. It does not write memory, invoke RelaySLP, expose a Lab API, mutate RelaySOUL, or change visible response delivery.

Phase 6-A1 now provides the helper-only `relaymem.slp_job_admission_preflight.v0` boundary. It validates trigger, processing stage, correlation, namespace, source lineage, response terminal state, and persistence-policy status without queue I/O or memory writes.

Phase 6-A2 now provides the helper-only response-finalization handoff. It consumes the exact A1 private result for a finalized `turn_end` response and may create one runtime-private `relaymem.slp_enqueue_candidate.v0` artifact. The candidate is metadata-only, dry-run-only, and is omitted from public diagnostics.

Phase 6-B0 defines the durable queue contract: `relaymem.slp_durable_job.v0`, dispatch-idempotency ownership and derivation inputs, atomic create-if-absent enqueue semantics, queue states, claim/lease fencing, stale-lease and restart behavior, corruption handling, and the content-free `relaymem.slp_queue_status_projection.v0` boundary. B0 is design-only and adds no producer, key generation, queue I/O, claim, lease, or terminal-state implementation.

Current implementation still does not provide a durable RelaySLP job queue, dispatch idempotency key, scheduled/background execution, worker claim/lease state, worker invocation, Secondary MEM consolidation runtime, or page/index/log apply.

## Current compatibility

- Retrieval still consumes a historical RelayREF-shaped input from the RelayINT-facing wrapper.
- Current query preparation may use request messages.
- `relaymem.retrieval_runtime.v1`, `relaymem.retrieval_projection.v1`, and `relaymem.slp_projection.v1` do not have current producers.
- RelayMEM-M3a candidates and M3b write-preflight operations are helper-only and are not request-runtime RelaySLP jobs.
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

A1/A2 own deferred orchestration metadata only. They consume rather than duplicate RelayMEM-M3b source-lineage semantics, Primary MEM write eligibility, memory-write idempotency, or later RelayMEM-M4 consolidation semantics.

B0 assigns dispatch identity, durable queue state, duplicate prevention, claim/lease fencing, and content-free queue status to Phase 6 / RelayRUN orchestration. It requires direct runtime-private A2 consumption and forbids reconstruction from public projection, trace, frontend metadata, or visible response text.

Dispatch idempotency and memory-write idempotency remain separate:

- Phase 6 / RelayRUN orchestration prevents duplicate job enqueue, claim, or retry execution.
- RelayMEM persistence preflight prevents duplicate durable memory writes.

A1 and A2 remain helper-only, default-off, dry-run-first, fail-closed, and free of durable queue I/O, worker execution, request-runtime wiring, or MEM persistence. B0 remains design-only.

## Target architecture

The detailed RelayMEM and RelaySLP documents define the target local-first store, typed relations, lint, safety scopes, deferred candidate compiler, and gated page/index/log updates. Those details remain target design rather than current runtime claims until their bounded producers, consumers, apply/skip/block contracts, projections, and smoke coverage land.

[Memory Lifecycle Design](memory_lifecycle_design.md) owns the target semantic boundary between RelayCTX short-term memory, governed experience evidence, autonomous ordinary MEM formation, Primary MEM, Secondary MEM consolidation, and SOUL Lab observation/correction operations.

Ordinary MEM formation is target-autonomous by default. User approval is not the normal path for every memory candidate; review and approval are exception paths for sensitive, destructive, identity-level, low-confidence, contradictory, cross-namespace, or SOUL-affecting changes.

RelaySLP may read SOUL as a protected anchor and may emit a separately governed RelaySOUL proposal candidate, but it must never directly mutate SOUL.

## Required migration

The next bounded implementation is Phase 6-B1: validate the exact A2 runtime-private candidate and derive a deterministic Phase 6-owned dispatch identity and dry-run durable-record candidate behind default-off, dry-run-only gates, without queue I/O.

Later B2/B3 slices must add atomic durable enqueue, duplicate/collision/corruption handling, claim/lease/stale-lease/terminal-state helpers, and content-free status projection without taking over RelayMEM memory meaning or memory-write idempotency. Worker execution, storage/idempotency apply, RelayRUN retry/checkpoint integration, RelaySOUL proposal handoff, and SOUL Lab memory-operation UI remain separate later work.

Do not require the full migration to land atomically. Each slice must preserve:

- request-runtime non-blocking behavior,
- default-off and dry-run-first gates,
- content-free public diagnostics,
- protected content-bearing memory/SLP domains,
- fail-closed namespace, lineage, policy, and schema validation,
- separation between dispatch and memory-write idempotency,
- no direct RelaySOUL mutation.

See [Phase 6 Asynchronous RelaySLP Bounded Slice](phase6_async_relayslp_bounded_slice.md), [Phase 6-A1 RelaySLP Job Admission Contract](phase6a1_relayslp_job_admission_contract.md), [Phase 6-A2 RelaySLP Response-Finalization Handoff Contract](phase6a2_relayslp_response_handoff_contract.md), [Phase 6-B0 RelaySLP Durable Queue Contract](phase6b0_relayslp_durable_queue_contract.md), [Memory Lifecycle Design](memory_lifecycle_design.md), [RelayMEM MVP Design](relaymem_mvp_design.md), [RelayMEM MVP Implementation Plan](relaymem_mvp_implementation_plan.md), [RelayMEM Retrieval Execution Design](relaymem_retrieval_execution_design.md), and [RelayMEM SLP Execution Design](relaymem_slp_execution_design.md).
