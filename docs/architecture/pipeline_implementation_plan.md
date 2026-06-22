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
  - client_history_authority_contract.md
  - client_instruction_authority_contract.md
  - phase5_5_stream_unpack_bounded_slice.md
  - phase6_async_relayslp_bounded_slice.md
  - phase6a1_relayslp_job_admission_contract.md
  - phase6a2_relayslp_response_handoff_contract.md
  - phase6b0_relayslp_durable_queue_contract.md
  - phase6b1_relayslp_dispatch_preflight.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6b3_relayslp_queue_state_helpers.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_current_target.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - soul_lab_ui_mvp.md
  - soul_lab_ui_a6_shared_shell_settings_handoff.md
  - soul_lab_ui_a7_management_projection_handoff.md
  - soul_lab_runtime_mvp.md
---
# RelayLM Pipeline Implementation Plan

## Purpose

This document owns implementation status, phase sequencing, dependency boundaries, and the active integration priority. Component ownership remains in [Pipeline Responsibility Design](pipeline_responsibility_design.md), exact contracts remain in their dedicated documents, and current/target interpretation remains in [Current / Target / Migration Guide](current_target_migration_guide.md).

The project is in an integration-first stage. New helper-only or mock-only slices are justified only when they directly unblock the active end-to-end milestone or close a demonstrated safety defect.

## Status legend

- **complete**: the bounded contract and intended helper or runtime wiring exist with smoke coverage.
- **integration pending**: component boundaries exist, but the ordinary runtime does not yet complete the user-visible loop.
- **planned**: design exists without a complete producer, consumer, apply, and validation path.
- **deferred**: intentionally not a gate for the active milestone.

## Current position

```text
Phase 5-C managed-route correctness:
  v0 no-instruction managed apply: complete
  v1 explicit-provenance instruction-bearing managed apply: complete
  C4b cache-hit RelaySCN-facing diagnostics projection: complete, diagnostics-only
  C5 runtime-private typed-parse / cache-writer plumbing: complete, default-off
  trusted backend-response artifact producer and RelaySCN semantic apply: pending

Phase 5-D pre-stream hardening: complete through D2

Phase 5.5 Stream Unpack / TTS handoff preparation:
  complete for RelayLM Core through B2 and C4
  adapter delivery and TTS/audio/avatar execution: pending outside Core

Phase 6 asynchronous RelaySLP orchestration:
  A0 ownership and sequencing: complete
  A1 job admission: complete as helper-only
  A2 response-finalization handoff: complete as helper-only
  B0 durable queue contract: complete
  B1 dispatch/job-record preflight: complete as helper-only
  B2 atomic durable enqueue: complete as direct helper
  B3 queue lifecycle helpers: complete as direct helper
  C worker execution under an active lease fence: next

RelayMEM independent track:
  M1/M2 store and retrieval foundations: complete
  M3a-M3g Primary MEM formation and persistence primitives: complete
  M3h read-only reconciliation recovery audit: complete
  ordinary-runtime worker integration and next-turn recall: pending

SOUL Lab UI independent track:
  UI-A0 through UI-A6 browser-local presentation slices: complete
  UI-A7 local-only settings/characters read projections: complete
  latest-run and memory-outcome reads: pending
  authoritative mutation APIs: pending

SOUL Lab Runtime:
  TTS/audio/avatar adapter execution: planned later
```

### Compatibility status anchors

Phase 6-B1 dry-run job-record and dispatch-idempotency preflight helper: complete.

Phase 6-B1: job-record and dispatch-idempotency preflight — complete.

Phase 6-B2 atomic durable enqueue: complete.

Phase 6-B3 queue lifecycle: complete.

The next RelayLM Core boundary is Phase 6-C worker execution under an exact active B3 owner, claim-generation, and lease-token fence. Request-runtime enqueue wiring is also required for the active milestone; neither worker execution nor request-runtime wiring is included in B3.

## Active priority: Integration Milestone I1

### Primary MEM end-to-end runtime loop

The highest-priority implementation goal is one ordinary runtime loop that proves RelayLM's core product value:

```text
finalized user turn
  -> deferred SLP admission and durable enqueue
  -> B3 queue claim and active lease
  -> Phase 6-C worker execution
  -> RelayMEM M3a-M3h Primary MEM processing
  -> durable page/index/log result
  -> next-turn RelayMEM retrieval
  -> RelayCTX injection
  -> model response uses the formed memory
  -> SOUL Lab can inspect the result through a real API
```

This milestone has priority over Secondary MEM consolidation, additional mock UI surfaces, TTS/Live2D execution, new RelaySOUL governance documents, protocol expansion, and model-specific optimization.

### I1-A: Phase 6-B3 queue lifecycle — complete

The bounded direct helper now implements:

```text
claim
renew_lease
retry_release
stale_recovery
commit_terminal
```

It preserves dispatch-idempotency ownership in Phase 6 / RelayRUN, uses revision/owner/claim-generation/lease-token fencing, classifies queue-control outcomes without deciding memory meaning, exposes only content-free public diagnostics, and keeps visible-response success independent of queue processing.

B3 remains default-off and dry-run-first. It validates complete canonical B2 records, uses a nonblocking queue lock and inode/byte compare-and-swap, never generates `dead_letter`, and never executes a worker.

B3 was the final queue-only prerequisite. The implementation sequence must now move into runtime integration and worker execution rather than adding another queue-helper phase.

### I1-B: request-runtime deferred enqueue wiring

Wire the existing A1 -> A2 -> B1 -> B2 sequence into finalized ordinary managed turns.

Requirements:

- visible response finalization occurs independently of queue persistence,
- enqueue failure is recorded but does not invalidate an already valid response,
- only exact runtime-private artifacts are passed between stages,
- default-off and dry-run-first rollout remains available,
- request-runtime smoke proves no content-bearing SLP artifact enters generic trace or public errors,
- the runtime does not claim or execute work inline with visible response delivery.

### I1-C: Phase 6-C Primary MEM worker execution

Add a bounded worker that obtains one active B3 claim and invokes existing RelayMEM-owned boundaries rather than redefining memory semantics:

```text
B3 active lease fence
  -> M3a formation candidate
  -> M3b lineage/write preflight
  -> M3c deterministic page candidate
  -> M3d writer handoff
  -> M3e atomic page publication
  -> M3f reconciliation plan
  -> M3g index-before-log apply
  -> M3h read-only recovery audit
  -> B3 retry release or terminal commit
```

The worker must:

- revalidate the exact active owner, claim generation, lease token, revision, and expiry before execution-sensitive transitions,
- never execute under an expired or stale lease,
- preserve the separation between dispatch idempotency and memory-write idempotency,
- invoke M3a-M3h as their exact current typed boundaries,
- classify retry/terminal outcomes without moving memory meaning into Phase 6,
- avoid direct RelaySOUL mutation and Secondary MEM consolidation,
- remain detached from visible response completion.

The first worker slice should execute one already-claimed job; scheduler loops, broad concurrency management, and generalized worker pools are not prerequisites for the first end-to-end proof.

### I1-D: next-turn recall validation

Prove that a Primary MEM formed by the ordinary runtime can be selected by the existing RelayMEM retrieval path and injected by RelayCTX on a later turn.

Required integration smoke:

1. complete a first turn with an eligible governed experience,
2. enqueue and process one Primary MEM job,
3. verify durable page/index/log state,
4. submit a second turn whose answer requires that memory,
5. verify the selected memory is scoped to the correct character and namespace,
6. verify the backend-bound context includes only the bounded selected memory,
7. verify no cross-character or cross-namespace leakage,
8. verify duplicate dispatch and worker retry preserve both idempotency domains.

### I1-E: SOUL Lab real observation bridge

UI-A7 already provides the bounded local-only read foundation for settings and character-registry metadata. It does not expose run or memory outcomes.

After the runtime loop exists, add server-owned read APIs for:

- latest run and SLP status,
- recently formed memories,
- held or blocked memory outcomes,
- memories used in the latest concrete UI session or run.

The first mutation slice should be one fully auditable memory correction path. Forget, pin/unpin, merge, and broader held-memory operations follow after correction works end to end.

## I1 completion criteria

Integration Milestone I1 is complete only when all of the following are true:

- a normal managed turn can schedule deferred Primary MEM processing without delaying the visible response,
- the durable queue can claim, lease, retry, recover stale work, and reach terminal state,
- a worker can execute the existing M3a-M3h boundaries under an exact B3 lease,
- formed Primary MEM is retrieved in a later ordinary turn,
- character and namespace isolation are verified,
- SOUL Lab reads real latest-run and memory outcomes,
- at least one correction operation changes later retrieval behavior,
- restart and duplicate-dispatch smoke preserve idempotency.

Helper-level completion and UI-A7 settings/characters reads alone do not satisfy I1.

## Current caveats

- Managed client-history exclusion remains default-off and dry-run-only by default.
- v1 instruction-bearing apply requires exact explicit provenance; active tool transactions remain blocked.
- C4b is a diagnostics-only cache-hit projection and does not semantically apply RelaySCN state.
- C5 runtime writer plumbing requires a trusted in-process typed-parse source and does not parse backend visible responses.
- Current profile compilation still precedes normalized target SCN/INT/Retrieval handoffs.
- Complete Runtime Compile Gate v1 route-authority/fallback/source taxonomy is not implemented.
- RelayCTX stream suppression and TTS handoff metadata are default-off; RelayLM Core does not deliver transport or execute TTS/audio/avatar behavior.
- Phase 6 A1/A2/B1/B2 request-runtime wiring is absent.
- Phase 6-C worker execution and worker invocation of RelayMEM M3a-M3h are absent.
- SOUL Lab UI-A7 provides bounded local read management metadata but no real run/memory observation or authoritative mutation.
- RelayREF output observation, Secondary MEM consolidation, and actual RelaySOUL apply remain later work.
- Token estimation is deterministic and CJK-aware but model-agnostic rather than tokenizer-exact.

## Completed implementation groups

### Core request and context path

Complete bounded work includes PipelineContext stabilization, RelayCTX Repack, RelayINT compatibility, PipelineNodeResult, non-stream RelayCTX Unpack, managed client-history authority through v0/v1 apply, C4b cache-hit diagnostics projection, C5 runtime-private parse/writer plumbing, CJK-aware token estimation, and lazy RelayRUN recovery-detail wiring.

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

Phase 6 has implemented exact bounded artifacts through B3 fenced queue lifecycle. B2 persists a queued record. B3 can claim, renew, retry-release, recover stale work, and commit terminal state, but neither helper invokes a worker or wires ordinary request finalization.

### Primary MEM primitives

RelayMEM M3a-M3h provide formation, lineage, deterministic page construction, atomic page publication, index/log reconciliation, and read-only recovery classification. They remain direct/helper boundaries until I1 worker integration lands.

### SOUL Lab presentation and read foundation

UI-A0 through UI-A6 provide the shared shell, Home, Adoption, Communication, Pod, Memory Inspector, Settings, localization, theme, active-character scope, and bounded browser-local operation previews.

UI-A7 adds loopback-only, secret-free `GET /lab/api/settings` and `GET /lab/api/characters` projections with exact browser schema validation and explicit mock fallback. It does not prove real memory observation or durable mutation.

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
