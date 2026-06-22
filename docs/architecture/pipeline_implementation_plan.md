---
relaylm_doc_type: implementation_plan
relaylm_authority: implementation_status_and_phase_sequencing
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - phase lands
  - sequencing changes
  - an integration milestone changes state
  - a target-only schema gains producer consumer apply skip block contract projection and smoke coverage
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - exact schema details
  - historical MVP authority
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - pipeline_responsibility_design.md
  - current_target_migration_guide.md
  - phase5_5_stream_unpack_bounded_slice.md
  - phase6_async_relayslp_bounded_slice.md
  - phase6a1_relayslp_job_admission_contract.md
  - phase6a2_relayslp_response_handoff_contract.md
  - phase6b0_relayslp_durable_queue_contract.md
  - phase6b1_relayslp_dispatch_preflight.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_current_target.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - soul_lab_ui_mvp.md
  - soul_lab_ui_a6_shared_shell_settings_handoff.md
  - soul_lab_runtime_mvp.md
---
# RelayLM Pipeline Implementation Plan

## Purpose

This document owns implementation status, phase sequencing, dependency boundaries, and the active integration priority. Component ownership remains in [Pipeline Responsibility Design](pipeline_responsibility_design.md), exact contracts remain in their dedicated documents, and current/target interpretation remains in [Current / Target / Migration Guide](current_target_migration_guide.md).

The project is now in an integration-first stage. New helper-only or mock-only slices are justified only when they directly unblock the active end-to-end milestone or close a demonstrated safety defect.

## Status legend

- **complete**: the bounded contract and intended helper or runtime wiring exist with smoke coverage.
- **integration pending**: component boundaries exist, but the ordinary runtime does not yet complete the user-visible loop.
- **planned**: design exists without a complete producer, consumer, apply, and validation path.
- **deferred**: intentionally not a gate for the active milestone.

## Current position

```text
Phase 5-C managed-route correctness: complete
Phase 5-D pre-stream hardening: complete through D2
Phase 5.5 Stream Unpack / TTS handoff preparation: complete for RelayLM Core

Phase 6 asynchronous RelaySLP orchestration:
  A0 ownership and sequencing: complete
  A1 job admission: complete as helper-only
  A2 response-finalization handoff: complete as helper-only
  B0 durable queue contract: complete
  B1 dispatch/job-record preflight: complete as helper-only
  B2 atomic durable enqueue: complete as direct helper
  B3 queue lifecycle helpers: next

RelayMEM independent track:
  M1/M2 store and retrieval foundations: complete
  M3a-M3g Primary MEM formation and persistence primitives: complete
  M3h read-only reconciliation recovery audit: complete
  ordinary-runtime worker integration and next-turn recall: pending

SOUL Lab UI independent track:
  UI-A0 through UI-A6: complete as browser-local mock/presentation slices
  real /lab/api/* read and mutation integration: pending

SOUL Lab Runtime:
  TTS/audio/avatar adapter execution: planned later
```

### Compatibility status anchors

Phase 6-B1 dry-run job-record and dispatch-idempotency preflight helper: complete.

Phase 6-B1: job-record and dispatch-idempotency preflight — complete.

Phase 6-B2 atomic durable enqueue: complete.

The next RelayLM Core boundary is Phase 6-B3. That boundary is the last queue-only prerequisite before request-runtime enqueue wiring and worker execution.

## Active priority: Integration Milestone I1

### Primary MEM end-to-end runtime loop

The highest-priority implementation goal is one ordinary runtime loop that proves RelayLM's core product value:

```text
finalized user turn
  -> deferred SLP admission and durable enqueue
  -> queue claim and worker execution
  -> RelayMEM M3a-M3h Primary MEM processing
  -> durable page/index/log result
  -> next-turn RelayMEM retrieval
  -> RelayCTX injection
  -> model response uses the formed memory
  -> SOUL Lab can inspect the result through a real API
```

This milestone has priority over Secondary MEM consolidation, additional mock UI surfaces, TTS/Live2D execution, new RelaySOUL governance documents, protocol expansion, and model-specific optimization.

### I1-A: Phase 6-B3 queue lifecycle

Implement bounded claim, lease, retry-release, stale-lease recovery, and terminal-state transitions over exact B2 durable records.

Requirements:

- preserve dispatch-idempotency ownership in Phase 6 / RelayRUN,
- use lease-token and claim-generation fencing,
- classify retryable and terminal control outcomes without deciding memory meaning,
- remain content-free on public diagnostic surfaces,
- do not make visible-response success depend on queue processing.

B3 is the final queue-only prerequisite. It must not become an open-ended sequence of additional helper-only queue phases.

### I1-B: request-runtime deferred enqueue wiring

Wire the existing A1 -> A2 -> B1 -> B2 sequence into finalized ordinary managed turns.

Requirements:

- visible response finalization occurs independently of queue persistence,
- enqueue failure is recorded but does not invalidate an already valid response,
- only exact runtime-private artifacts are passed between stages,
- default-off and dry-run-first rollout remains available,
- request-runtime smoke proves no content-bearing SLP artifact enters generic trace or public errors.

### I1-C: Primary MEM worker execution

Add a bounded worker that claims one eligible job and invokes existing RelayMEM-owned boundaries rather than redefining memory semantics:

```text
M3a formation candidate
  -> M3b lineage/write preflight
  -> M3c deterministic page candidate
  -> M3d writer handoff
  -> M3e atomic page publication
  -> M3f reconciliation plan
  -> M3g index-before-log apply
  -> M3h read-only recovery audit
  -> queue terminal or retry state
```

The worker must preserve the separation between dispatch idempotency and memory-write idempotency. It must not directly mutate RelaySOUL or perform Secondary MEM consolidation.

### I1-D: next-turn recall validation

Prove that a Primary MEM formed by the ordinary runtime can be selected by the existing RelayMEM retrieval path and injected by RelayCTX on a later turn.

Required integration smoke:

1. complete a first turn with an eligible governed experience,
2. enqueue and process one Primary MEM job,
3. verify durable page/index/log state,
4. submit a second turn whose answer requires that memory,
5. verify the selected memory is scoped to the correct character and namespace,
6. verify the backend-bound context includes only the bounded selected memory,
7. verify no cross-character or cross-namespace leakage.

### I1-E: SOUL Lab real observation bridge

After the runtime loop exists, replace the most important mock projections with server-owned read APIs:

- registered characters and active character projection,
- latest run and SLP status,
- recently formed memories,
- held or blocked memory outcomes,
- memories used in the latest concrete UI session or run.

The first mutation slice should be one fully auditable memory correction path. Forget, pin/unpin, merge, and broader held-memory operations follow after correction works end to end.

## I1 completion criteria

Integration Milestone I1 is complete only when all of the following are true:

- a normal managed turn can schedule deferred Primary MEM processing without delaying the visible response,
- the durable queue can claim, lease, retry, recover stale work, and reach terminal state,
- a worker can execute the existing M3a-M3h boundaries,
- formed Primary MEM is retrieved in a later ordinary turn,
- character and namespace isolation are verified,
- SOUL Lab reads real latest-run and memory outcomes,
- at least one correction operation changes later retrieval behavior,
- restart and duplicate-dispatch smoke preserve idempotency.

Helper-level completion alone does not satisfy I1.

## Current caveats

- Managed client-history exclusion remains default-off and dry-run-only by default.
- Current profile compilation still precedes normalized target SCN/INT/Retrieval handoffs.
- Complete Runtime Compile Gate v1 route-authority/fallback/source taxonomy is not implemented.
- Active tool transactions remain blocked because minimum-chain reconstruction is absent.
- Instruction-cache lookup and RelaySCN projection are read-only; cache writing requires explicit trusted runtime-private input and gates.
- RelayCTX stream suppression and TTS handoff planning remain default-off; RelayLM Core does not deliver adapter transport or execute TTS/audio/avatar behavior.
- Phase 6 A1/A2/B1/B2 and RelayMEM M3a-M3h are not yet connected into one ordinary request-runtime worker path.
- SOUL Lab UI-A0 through UI-A6 remain browser-local presentation slices without authoritative management APIs.
- RelayREF output observation, Secondary MEM consolidation, and actual RelaySOUL apply remain later work.
- Token estimation is deterministic and CJK-aware but model-agnostic rather than tokenizer-exact.

## Completed implementation groups

### Core request and context path

Complete bounded work includes PipelineContext stabilization, RelayCTX Repack, RelayINT compatibility, PipelineNodeResult, non-stream RelayCTX Unpack, managed client-history authority through instruction-bearing apply, CJK-aware token estimation, and lazy RelayRUN recovery-detail wiring.

### Stream safety and handoff preparation

Phase 5.5 is closed for RelayLM Core through:

- stream sentinel observation,
- safe visible/internal suppression,
- request-runtime SSE wrapping,
- TTS-safe segmentation hints,
- runtime-private adapter handoff plans,
- adapter-facing transport-envelope construction.

Concrete adapter delivery and TTS/audio/avatar execution belong to SOUL Lab Runtime MVP and are deferred until the text and memory loop is proven.

### Deferred orchestration primitives

Phase 6 has implemented exact bounded artifacts through atomic durable enqueue. B2 persists a queued record but does not claim it, invoke a worker, write memory, or wire request finalization.

### Primary MEM primitives

RelayMEM M3a-M3h provide formation, lineage, deterministic page construction, atomic page publication, index/log reconciliation, and read-only recovery classification. They remain direct/helper boundaries until I1 worker integration lands.

### SOUL Lab presentation

UI-A0 through UI-A6 provide the shared shell, Home, Adoption, Communication, Pod, Memory Inspector, Settings, localization, theme, active-character scope, and bounded browser-local operation previews. They do not prove runtime connectivity or durable mutation.

## Deferred until after I1

The following are not active blockers for I1:

- RelayMEM-M4 Secondary MEM consolidation,
- broad SOUL proposal apply/rollback execution,
- additional mock-only SOUL Lab screens,
- TTS, audio queues, Live2D/avatar control, lip-sync, or OBS integration,
- `/v1/responses` or other protocol expansion,
- model-specific tokenizer integration,
- generalized agent/tool orchestration,
- large benchmark tournaments.

Small evaluation hooks required to validate I1 are not deferred. The integration smoke must record bounded latency, duplicate/retry behavior, recall success, and isolation failures.

## Sequencing rule

Independent tracks may still proceed in parallel when they do not conflict, but their local next slice must serve the active integration milestone. The project must not interpret track independence as permission to indefinitely postpone runtime wiring.

When a choice exists between:

```text
another isolated helper or mock projection
```

and:

```text
connecting an already implemented producer to its real consumer
```

choose the integration work unless a concrete safety defect blocks it.

## Update rule

Update this plan whenever a phase lands, I1 sequencing changes, a target-only schema gains a real producer/consumer path, or a mock/direct-helper boundary becomes ordinary runtime behavior. Keep detailed schema and historical evidence in dedicated contract and handoff documents rather than duplicating them here.
