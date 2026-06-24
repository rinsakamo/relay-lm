---
relaylm_doc_type: status
relaylm_authority: current_project_state
relaylm_status: current
relaylm_volatility: high
relaylm_owner: project_status
relaylm_update_trigger:
  - boundary moves between design dry-run read-only and apply
  - default behavior changes
  - supported request shape changes
  - current schema producer or consumer changes
  - active integration milestone changes state
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - exact schema details
  - historical implementation evidence
relaylm_related_authority:
  - docs/DOCUMENTATION_MODEL.md
  - docs/architecture/pipeline_responsibility_design.md
  - docs/architecture/pipeline_implementation_plan.md
  - docs/architecture/current_target_migration_guide.md
  - docs/architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - docs/architecture/phase6b3_relayslp_queue_state_helpers.md
  - docs/architecture/phase6c1_primary_mem_worker_contract.md
  - docs/architecture/phase6c1_one_claimed_primary_worker_handoff.md
  - docs/architecture/phase6c1_integrated_worker_fault_smoke_handoff.md
  - docs/architecture/phase6c1_durable_protected_source_persistence.md
  - docs/architecture/phase6c2_one_queued_primary_worker_integration.md
  - docs/architecture/integration_i1_primary_mem_two_turn_recall.md
  - docs/architecture/relaymem_mvp_implementation_plan.md
  - docs/architecture/relaymem_slp_current_target.md
  - docs/architecture/phase_i2_real_soul_lab_observation.md
  - docs/architecture/phase_i3_auditable_primary_mem_correct.md
  - docs/architecture/phase_i4_primary_mem_forget_hide_contract.md
---
# RelayLM Project Status

Last reviewed: 2026-06-25 JST

Status reviewed through:

- Phase 6 I1-B ordinary request-runtime enqueue and finalized-turn protected capture,
- Phase 6-C1-0 through C1-5 Primary MEM worker, fault, and durable-source boundaries,
- Phase 6-C2 one queued-job claim / rehydrate / execute integration adapter,
- Phase I-1 Primary MEM next-turn recall and character/namespace isolation,
- Phase I-2 real SOUL Lab latest-run and memory observation integration,
- Phase I-3 auditable Primary MEM Correct and later retrieval convergence,
- Phase I-4A Primary MEM Forget / Hide target contract definition only.

## Purpose and authority

This page is the concise current-state view for developers and reviewers. It records what works now, what remains gated or disconnected, and the immediate implementation priority.

When documents disagree:

1. [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md) owns component responsibilities and canonical target order.
2. [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) owns detailed implementation status and sequencing.
3. Dedicated current contracts own exact schemas and bounded behavior.
4. [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) defines compatibility and target interpretation.
5. `docs/mvp/` and historical handoffs are evidence only.

## Current implementation position

```text
Managed-route correctness: Phase 5-C complete through bounded v0/v1 apply and C5 runtime plumbing
Pre-stream hardening: Phase 5-D complete through D2
Stream safety / TTS handoff preparation: Phase 5.5 complete for RelayLM Core
Asynchronous RelaySLP orchestration: I1-B and B3 complete; C1-0 through C1-5 complete; C2 one-job adapter complete
RelayMEM Primary path: M1/M2 complete; M3a-M3h executable; ordinary next-turn recall and scope isolation complete
SOUL Lab UI: UI-A0 through UI-A7 complete; Phase I-2 observation and Phase I-3 token-gated Correct connected
I1 observe/correct/retrieve product loop: complete
Phase I-4A Forget / Hide contract: defined target; runtime apply, M2 exclusion, and UI unimplemented
I1-G pre-enqueue background-finalizer durability: unresolved
```

## Core request/runtime foundation

Current implementation includes OpenAI-compatible Chat Completions proxying, ordered managed-route pipeline execution, selected RelayMEM retrieval, gated RelayCTX injection, bounded history authority, stream-safety/TTS handoff metadata, lazy RelayRUN recovery detail, and RelaySOUL dry-run/preflight foundations.

Current limitations include incomplete tool-chain reconstruction, incomplete trusted backend-response instruction-control production, incomplete semantic RelaySCN apply, and no parser-versioned cache compatibility.

## Phase 6 RelaySLP orchestration

Implemented:

- A1/A2 deferred admission and finalized-turn handoff,
- B0-B3 durable queue schema, enqueue, claim, lease, retry, stale recovery, and terminal commit,
- I1-B ordinary managed non-stream and stream post-response A1 -> A2 -> B1 -> B2 wiring,
- C1-0 through C1-5 exact source, compose, one-claim worker, outcome, fault, and durable protected-source boundaries,
- C2 exact queued-record claim, durable rehydrate, C1-2 execution, and terminal-only cleanup.

C1-5 keeps queue records content-free and can rehydrate a fresh C1-0 source for work that already reached durable source publication and enqueue.

Current limitations:

- no queue scanner, daemon, scheduler, or supervised worker service automatically selects work,
- I1-G remains unresolved: process exit after visible-response delivery but before source/queue publication may lose that deferred turn.

## RelayMEM Primary persistence and recall

Implemented:

- M3a-M3h Primary formation, page publication, index/log convergence, and read-only recovery audit,
- C1-1/C1-2 integration,
- Phase I-1 ordinary next-turn M2 retrieval,
- exact Primary page plus canonical index/log validation,
- bounded RelayCTX injection for the exact character and namespace,
- Phase I-3 immutable successor correction with later corrected retrieval.

Current limitations:

- Secondary MEM consolidation is not implemented,
- Phase I-4A defines Forget / Hide only as a target contract,
- production Forget apply, canonical lifecycle resolver, hidden-state M2 exclusion, and Forget UI are unimplemented,
- Pin/Unpin, Merge/Supersession, and Held Apply/Discard are unimplemented.

## SOUL Lab UI and observation

UI-A0 through UI-A7 and Phase I-2 provide the TypeScript/React/Vite shell, character-scoped state, real loopback-only latest-run and memory observation, strict exact-schema browser validation, bounded projections, and explicit separation of RelayLM runtime data from local preview data.

Phase I-3 adds token-gated Correct for real formed Primary MEM. Observation receipts remain read-only evidence and cannot become memory, queue, lifecycle, or repair authority.

Current limitations:

- no real Home conversation yet,
- no Forget, Pin, Merge, or held-review UI,
- no RelaySOUL apply/rollback,
- no static RelayLM serving of the built SOUL Lab bundle,
- no TTS, audio, or avatar execution.

## Phase I-3: auditable Primary MEM Correct — complete

```text
real formed Primary MEM observation
  -> read-only correction preflight and bounded semantic diff
  -> explicit short-lived-token apply
  -> immutable successor page through M3e
  -> M3f/M3g index/log convergence and bounded recovery
  -> immutable correction receipt
  -> existing M2 and RelayCTX select the corrected current revision
```

The stable logical memory identity remains unchanged, prior pages remain auditable, superseded or prepared-only pages are excluded from ordinary retrieval, and past used-memory evidence is not rewritten.

Authority: `docs/architecture/phase_i3_auditable_primary_mem_correct.md`.

## Phase I-4A: Primary MEM Forget / Hide contract — defined target

The contract fixes one terminology and lifecycle model:

```text
user-facing operation: Forget
canonical lifecycle state: hidden
runtime-private audit artifact: Forget tombstone
persistence: immutable hidden successor Primary page with revision N+1
resolver: one canonical current/active/retrieval-eligibility resolver
concurrency: one Correct/Forget per-memory revision fence
```

Candidate A is selected: lifecycle authority advances through an immutable successor Primary page and existing M3e/M3f/M3g convergence. A tombstone is audit evidence, not an independent sidecar authority. Prepared, recovery-required, or corrupt states must fail closed for ordinary retrieval.

Authority: `docs/architecture/phase_i4_primary_mem_forget_hide_contract.md`.

Contract definition is not product completion. The target routes, schemas, page lifecycle metadata, M2 exclusion, historical lifecycle projection, and SOUL Lab Forget UI do not exist in production yet.

## Completion boundary (2026-06-25)

- I1-B producer: complete
- B3 lifecycle: complete
- C1-0 through C1-5 complete
- C2 one-job claim/rehydrate/execute adapter: complete
- I1 next-turn Primary MEM recall: complete
- character and namespace isolation: complete
- I2 real SOUL Lab observation: complete
- I3 auditable Primary MEM Correct: complete
- I1 observe/correct/retrieve product loop: complete
- I4A Forget / Hide contract: defined target
- I4 production Forget runtime, M2 exclusion, and UI: unimplemented
- I1-G pre-enqueue background-finalizer durability: unresolved

## Safe defaults and compatibility

Current safe defaults remain conservative. Phase 6 source publication/enqueue is gated; B3/C1-2/C2 remain caller-driven rather than daemon-owned; SOUL Lab management reads remain local-only; Correct requires exact JSON, expected revision, and a preflight-issued token. The I-4A routes and schemas are target definitions and are not accepted by the current runtime.

## Not yet implemented

The runtime does not yet provide:

- queue scanner, retry scheduler, daemon, or supervised worker service,
- restart completion for I1-G's pre-enqueue background-finalizer crash window,
- production Forget lifecycle apply, hidden-state M2 exclusion, Forget history API, or Forget UI,
- restore / unhide,
- hard delete, secure erase, or physical purge through Forget,
- Pin/Unpin, Merge/Supersession, Held Apply/Discard, or Secondary MEM consolidation,
- actual RelaySOUL apply or rollback,
- static SOUL Lab serving,
- TTS/audio/avatar execution,
- complete output-side RelayREF/RelaySCN and Runtime Compile Gate v1,
- model-specific exact tokenizer integration,
- `/v1/responses` support.

UI-B0 Real Home Conversation and O0 Local one-job runner remain planned; Phase I-4A does not change their state.

## Usable runtime path

```text
OpenWebUI
  -> RelayLM http://127.0.0.1:8090/v1
  -> LM Studio http://127.0.0.1:1234/v1
```

C1-5/C2 provide one restart-safe durably enqueued job path, Phase I-1 provides ordinary scoped recall, Phase I-2 provides bounded read-only observation, and Phase I-3 provides audited Correct with later M2 convergence. Phase I-4A adds a target contract only.

I1-G tracks the process-exit window after visible response delivery but before protected-source and B2 queue publication. Neither observation receipts nor the I-4A contract repair that gap.
