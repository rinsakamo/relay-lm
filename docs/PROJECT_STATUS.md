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
  - docs/architecture/phase6_async_relayslp_bounded_slice.md
  - docs/architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - docs/architecture/phase6b3_relayslp_queue_state_helpers.md
  - docs/architecture/phase6c1_primary_mem_worker_contract.md
  - docs/architecture/phase6c1_relaymem_primary_pipeline_compose.md
  - docs/architecture/phase6c1_primary_worker_outcome_classifier.md
  - docs/architecture/phase6c1_one_claimed_primary_worker_handoff.md
  - docs/architecture/phase6c1_integrated_worker_fault_smoke_handoff.md
  - docs/architecture/phase6c1_durable_protected_source_persistence.md
  - docs/architecture/relaymem_mvp_implementation_plan.md
  - docs/architecture/relaymem_slp_current_target.md
  - docs/architecture/soul_lab_ui_a7_management_projection_handoff.md
---
# RelayLM Project Status

Last reviewed: 2026-06-24 JST

Status reviewed through:

- Phase 6 I1-B ordinary request-runtime enqueue and finalized-turn protected capture,
- Phase 6-C1-0 protected worker-source bundle,
- Phase 6-C1-1 RelayMEM M3a-M3h compose boundary,
- Phase 6-C1-2 one-already-claimed Primary MEM worker,
- Phase 6-C1-3 pure worker-outcome classifier,
- Phase 6-C1-4 integrated worker fault and crash-convergence smoke,
- Phase 6-C1-5 durable protected source persistence and restart rehydration.

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
Asynchronous RelaySLP orchestration: I1-B and B3 complete; C1-0 through C1-5 complete
RelayMEM Primary path: M1/M2 complete; M3a-M3h composed and executable for one exact active claim
SOUL Lab UI: UI-A0 through UI-A7 implemented; A7 adds local-only read management projections
```

### Core request/runtime foundation

Current implementation includes:

- OpenAI-compatible `/v1/chat/completions` proxying, routing, and backend forwarding,
- `PipelineContext` and ordered content-free `PipelineNodeResult` collection,
- managed client-history authority through bounded v0/v1 apply,
- RelayINT-facing reference-repair compatibility,
- selected RelayMEM retrieval and gated RelayCTX injection foundations,
- pure and gated non-stream RelayCTX Unpack,
- Phase 5.5-B2 gated stream suppression,
- Phase 5.5-C0 through C4 TTS-safe segmentation and adapter-envelope metadata,
- strict read-only client-instruction cache lookup,
- C4b diagnostics-only RelaySCN-facing cache-hit projection,
- C5 runtime-private typed-parse and default-off cache-writer plumbing,
- CJK-aware deterministic token estimation,
- lazy RelayRUN recovery-detail wiring,
- RelaySOUL dry-run/preflight governance foundations.

Current managed-route limitations:

- history-exclusion apply remains default-off and dry-run-only by default,
- v1 requires exact `client_instruction_source.v1` provenance,
- role, wording, and position alone are not provenance,
- active tool transactions remain blocked because minimum-chain reconstruction is absent,
- C4b does not semantically apply RelaySCN state,
- parser-versioned cache lookup/write compatibility is not implemented.

### Phase 6 RelaySLP orchestration

Implemented:

- A1 deferred job-admission preflight,
- A2 finalized-turn handoff,
- B0 durable queue schema and state machine,
- B1 deterministic dispatch/job-record preflight,
- B2 atomic durable enqueue,
- B3 fenced claim, renew, retry release, stale recovery, and terminal commit,
- I1-B ordinary managed non-stream and stream post-response A1 -> A2 -> B1 -> B2 wiring,
- C1-0 exact claim-correlated protected worker source and one-shot scope,
- C1-1 canonical M3a-M3h compose,
- C1-2 lease-fenced execution of one already-claimed canonical B3 job,
- C1-3 pure RelayMEM-outcome classification,
- C1-4 integrated crash, lease-loss, lock-contention, stale-claim, corruption, and leakage smoke,
- C1-5 source-before-queue durable protected artifact publication and restart rehydration.

C1-5 keeps the queue record content-free. The process-local registry is now only an optional hot cache; a new claim may rehydrate the claim-independent protected capture from the durable artifact and build a fresh C1-0 source/scope.

Current limitations:

- no queue scanner, daemon, or scheduler automatically selects and claims queued work,
- the ordinary runtime still lacks a thin one-job adapter performing B3 claim -> C1-5 rehydrate -> C1-2 execute,
- C1-5 is restart-complete only for protected-source recovery of durably enqueued jobs,
- a process exit after visible response delivery but before the Starlette background finalizer publishes the source and queue record may still lose that turn's deferred work,
- next-turn recall and real SOUL Lab memory observation remain unproven.

### RelayMEM Primary persistence

Implemented direct/helper boundaries:

- M3a Primary MEM formation candidate,
- M3b source lineage, safety, and memory-write preflight,
- M3c deterministic Primary page candidate,
- M3d writer/store-target handoff,
- M3e atomic no-clobber page publication,
- M3f deterministic index/log reconciliation preflight,
- M3g gated index-before-log reconciliation apply,
- M3h read-only receipt/store recovery audit,
- C1-1 exact M3a-M3h composition,
- C1-2 one-active-claim execution,
- C1-4 fault and crash convergence evidence,
- C1-5 restart restoration of exact protected source evidence.

Current limitations:

- ordinary response finalization intentionally does not invoke M3a-M3h inline,
- an explicit one-job claim/rehydrate/execute adapter is required before ordinary queued work reaches C1-2 without test injection,
- successful worker execution does not yet prove that a later ordinary turn retrieves and uses the newly formed memory,
- Secondary MEM consolidation is not implemented,
- durable Lab memory mutation APIs are not implemented.

### SOUL Lab UI

UI-A0 through UI-A7 provide:

- TypeScript/React/Vite browser shell,
- Japanese-default and English-preview localization,
- light/dark themes,
- active-character selection and character-scoped browser state,
- mock Home, Lab Observation, Adoption, Communication, and Pod flows,
- Memory Inspector operation previews,
- shared shell and Settings/runtime-boundary projections,
- loopback-only `GET /lab/api/settings` and `GET /lab/api/characters`,
- exact browser-side allowlist validation and explicit mock fallback,
- secret-free endpoint, capability, character-registry, and content-free diagnostics metadata.

Current limitations:

- no latest-run, formed/held/blocked memory, or used-memory read API,
- no durable character-registry or memory operation,
- no RelaySOUL apply or rollback,
- no persisted transcript,
- no TTS/audio/avatar execution,
- no static serving of the built SOUL Lab bundle from RelayLM.

## Active implementation priority

### Integration Milestone I1: Primary MEM end-to-end runtime loop

```text
ordinary finalized turn
  -> A1/A2/B1/B2 runtime enqueue                complete as I1-B
  -> C1-5 durable protected source              complete
  -> B3 claim/lease/retry lifecycle             complete as direct helpers
  -> one-job claim/rehydrate/execute adapter     next integration boundary
  -> C1-0 protected source                      complete
  -> C1-2 one-claimed worker                    complete
  -> C1-1 M3a-M3h compose                       complete
  -> C1-3 outcome classification                complete
  -> C1-4 crash/fault convergence               complete
  -> B3 retry release or terminal commit
  -> durable page/index/log outcome
  -> later-turn RelayMEM retrieval
  -> RelayCTX injection
  -> response uses formed memory
  -> SOUL Lab reads real latest-run and memory outcome
```

Immediate sequence:

1. Add a thin one-job integration adapter: exact queued record -> B3 claim -> C1-5 source rehydrate -> C1-2 worker.
2. Add an ordinary-runtime integration smoke for enqueue, explicit claim, rehydrate, compose, classify, and B3 transition.
3. Add a two-turn smoke proving next-turn recall and character/namespace isolation.
4. Add real SOUL Lab read APIs for latest run, formed/held/blocked memory, and used memory.
5. Add one auditable Correct operation whose result changes later retrieval behavior.
6. Treat the visible-response-to-background-finalizer crash window as a separate I1 durability boundary; C1-5 does not claim to close it.

I1-B, B3, and C1-0 through C1-5 are complete prerequisites, not the final product goal.

## Safe defaults and compatibility

Current safe defaults remain conservative:

```text
client_history_exclusion_apply_enabled = false
client_history_exclusion_apply_dry_run_only = true
memory.token_budget_truncation_enabled = false
client_instruction_typed_parse_enabled = false
client_instruction_cache_write_enabled = false
client_instruction_cache_write_dry_run_only = true
relayctx_stream_unpack_dry_run_enabled = false
relayctx_stream_unpack_dry_run_only = true
relayctx_tts_adapter_handoff_runtime_enabled = false
relayctx_tts_adapter_handoff_runtime_dry_run_only = true
```

Consequences:

- default `memory_light` compatibility may preserve frontend history until managed apply is intentionally enabled,
- stream suppression and TTS handoff metadata remain default-off,
- Phase 6/B3/RelayMEM apply boundaries remain explicitly gated,
- I1-B never claims or executes a worker inline with visible response delivery,
- UI-A7 routes remain local-only read surfaces.

## Not yet implemented

The runtime does not yet provide:

- complete current-turn-only reconstruction for every compatibility-sensitive request shape,
- active tool-chain reconstruction,
- trusted backend-response instruction-control production and semantic RelaySCN apply,
- parser-versioned cache compatibility,
- a bounded ordinary-runtime one-job claim/rehydrate/execute adapter,
- queue scanner, daemon, or scheduler-driven worker execution,
- restart completion for the pre-enqueue background-finalizer crash window,
- end-to-end next-turn recall proof from newly formed runtime memory,
- Secondary MEM consolidation,
- SOUL Lab latest-run and memory-outcome reads,
- durable correction/forget/pin/merge operations,
- actual RelaySOUL apply, rollback, or persistence execution,
- RelayLM static serving of SOUL Lab,
- adapter transport delivery, TTS, audio generation, or avatar control,
- complete output-side RelayREF and Output-side RelaySCN,
- complete Runtime Compile Gate v1 taxonomy,
- model-specific exact tokenizer integration,
- `/v1/responses` support.

## Work deferred until I1 closes

Unless required to close a concrete I1 defect, defer:

- RelayMEM-M4 Secondary MEM consolidation,
- additional mock-only UI screens,
- broad RelaySOUL execution-gate expansion,
- SOUL Lab Runtime TTS/audio/Live2D implementation,
- protocol expansion,
- model-specific optimization,
- generalized agent functionality.

## Usable runtime path

```text
OpenWebUI
  -> RelayLM http://127.0.0.1:8090/v1
  -> LM Studio http://127.0.0.1:1234/v1
```

The memory write path remains explicitly gated. C1-5 adds restart-safe protected-source recovery for durably enqueued work; it does not make queue scheduling or next-turn recall automatic.
