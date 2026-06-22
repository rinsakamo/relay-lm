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
  - docs/architecture/phase6b0_relayslp_durable_queue_contract.md
  - docs/architecture/phase6b1_relayslp_dispatch_preflight.md
  - docs/architecture/phase6b2_relayslp_atomic_durable_enqueue.md
  - docs/architecture/relaymem_mvp_implementation_plan.md
  - docs/architecture/relaymem_slp_current_target.md
  - docs/architecture/relaymem_m3g_primary_index_log_reconciliation_apply.md
  - docs/architecture/relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - docs/architecture/soul_lab_ui_mvp.md
  - docs/architecture/soul_lab_ui_a6_shared_shell_settings_handoff.md
  - docs/architecture/soul_lab_runtime_mvp.md
---
# RelayLM Project Status

Last reviewed: 2026-06-22 JST

Status baseline `main` commit: `96001c8c88ac6b11ac1a9cfb6d60c4752e2e3433`

## Purpose and authority

This page is the concise current-state view for developers and reviewers. It records what works now, what remains gated or disconnected, and the immediate implementation priority.

When documents disagree:

1. [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md) owns component responsibilities and canonical target order.
2. [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) owns detailed implementation status and sequencing.
3. Dedicated module and contract documents own exact schemas and bounded behavior.
4. [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) defines compatibility and target interpretation.
5. `docs/mvp/` and implementation handoffs are historical or bounded implementation evidence.

## Current implementation position

```text
Managed-route correctness: Phase 5-C complete
Pre-stream hardening: Phase 5-D complete through D2
Stream safety / TTS handoff preparation: Phase 5.5 complete for RelayLM Core
Asynchronous RelaySLP orchestration: durable enqueue implementation complete through Phase 6-B2
RelayMEM Primary path: M1/M2 complete; M3a through M3h implemented as direct/helper boundaries
SOUL Lab UI: UI-A0 through UI-A6 implemented as browser-local mock/presentation slices
```

### Core request/runtime foundation

Current `main` includes:

- OpenAI-compatible `/v1/chat/completions` proxying, routing, and backend forwarding,
- `PipelineContext` and ordered content-free `PipelineNodeResult` collection,
- profile compilation and RelayCTX Repack foundations,
- RelayINT-facing reference-repair compatibility,
- selected RelayMEM retrieval and gated RelayCTX injection,
- pure and gated non-stream RelayCTX Unpack,
- gated stream sentinel/suppression runtime handling,
- TTS-safe segmentation and adapter handoff/transport metadata construction,
- managed-route client-history exclusion through no-instruction and instruction-bearing apply contracts,
- CJK-aware deterministic token estimation,
- lazy RelayRUN recovery-detail request-runtime wiring,
- RelaySOUL dry-run/preflight governance foundations.

### Phase 6 RelaySLP orchestration

Implemented:

- A1 deferred job-admission preflight,
- A2 finalized-turn handoff and runtime-private enqueue candidate,
- B0 durable queue schema and state-machine contract,
- Phase 6-B1 RelaySLP dispatch preflight,
- Phase 6-B2 atomic durable enqueue with duplicate/collision/corruption classification.

Current limitation:

- A1/A2/B1/B2 are not called automatically from ordinary request finalization,
- no queue claim, lease, retry-release, stale recovery, or terminal transition helper is wired,
- no scheduler or worker invokes RelayMEM processing,
- queue persistence does not yet lead to memory persistence.

### RelayMEM Primary persistence

Implemented direct/helper boundaries:

- M3a Primary MEM formation candidate,
- M3b source lineage, safety, and memory-write preflight,
- M3c deterministic Primary page candidate,
- M3d writer-handoff/store-target preflight,
- M3e default-off atomic no-clobber page publication,
- M3f deterministic index/log reconciliation preflight,
- M3g gated index-before-log reconciliation apply with retryable partial progress,
- M3h read-only receipt/store recovery audit and recovery classification.

Current limitation:

- the ordinary request runtime and Phase 6 worker do not invoke M3a-M3h,
- successful helper execution does not prove autonomous turn-end memory formation,
- Secondary MEM consolidation is not implemented,
- Lab memory mutation APIs are not implemented.

### SOUL Lab UI

UI-A0 through UI-A6 provide:

- TypeScript/React/Vite browser shell,
- Japanese-default and English-preview localization,
- light/dark themes,
- active-character selection and character-scoped browser state,
- mock Home and Lab Observation,
- browser-local Adoption,
- mock Communication with Soft Stop,
- mock Pod intervention and non-executing SOUL candidate previews,
- Memory Inspector with non-persistent Correct/Merge/Forget/Pin/Unpin/Discard previews,
- shared shell and Settings/runtime-boundary projections.

Current limitation:

- no authoritative `/lab/api/*` integration,
- no peer network request,
- no durable character registry or memory operation,
- no RelaySOUL apply or rollback,
- no persisted transcript or latest-run observation source,
- no TTS/audio/avatar execution.

## Active implementation priority

The project is now integration-first.

### Integration Milestone I1: Primary MEM end-to-end runtime loop

```text
ordinary finalized turn
  -> A1/A2/B1/B2 runtime enqueue
  -> B3 claim/lease/retry lifecycle
  -> bounded worker
  -> M3a-M3h Primary MEM processing
  -> durable page/index/log outcome
  -> later-turn RelayMEM retrieval
  -> RelayCTX injection
  -> response uses formed memory
  -> SOUL Lab reads real latest-run and memory outcome
```

Immediate sequence:

1. Phase 6-B3 claim, lease, retry-release, stale-recovery, and terminal-state helpers.
2. Request-runtime wiring from finalized turn through B2 durable enqueue.
3. Worker execution that invokes existing M3a-M3h boundaries without redefining memory semantics.
4. End-to-end smoke proving next-turn recall and character/namespace isolation.
5. Real SOUL Lab read APIs for latest run, formed/held/blocked memory, and used memory.
6. One auditable Correct operation whose result changes later retrieval behavior.

B3 is a prerequisite, not the final product goal. Helper-only completion does not close I1.

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

- default `memory_light` compatibility may preserve frontend history until managed apply is enabled,
- stream suppression and TTS handoff planning remain default-off,
- RelayLM Core does not deliver adapter transport or execute TTS/audio/avatar behavior,
- Phase 6 and RelayMEM persistence apply remain explicit gated boundaries rather than ordinary default runtime behavior.

## Not yet implemented

The runtime does not yet provide:

- request-runtime A1/A2/B1/B2 invocation,
- Phase 6-B3 queue lifecycle behavior,
- scheduler/background worker execution,
- worker invocation of RelayMEM M3a-M3h,
- end-to-end next-turn recall proof from newly formed runtime memory,
- Secondary MEM consolidation,
- real SOUL Lab management APIs,
- durable memory correction/forget/pin/merge operations,
- actual RelaySOUL apply, rollback, or persistence execution,
- adapter transport delivery,
- TTS execution, audio generation, or avatar control,
- complete output-side RelayREF and output-side RelaySCN,
- complete Runtime Compile Gate v1 taxonomy,
- active tool-chain reconstruction,
- model-specific exact tokenizer integration,
- `/v1/responses` support.

## Work deferred until I1 closes

Unless required to fix a concrete I1 safety defect, defer:

- RelayMEM-M4 Secondary MEM consolidation,
- additional mock-only UI screens,
- broad RelaySOUL execution-gate design expansion,
- SOUL Lab Runtime TTS/audio/Live2D implementation,
- protocol expansion,
- model-specific optimization,
- generalized agent functionality.

The architecture documents for these areas remain valid; they are not the immediate sequencing priority.

## Usable runtime paths

Primary local path:

```text
OpenWebUI
  -> RelayLM http://127.0.0.1:8090/v1
  -> LM Studio http://127.0.0.1:1234/v1
```

Optional frontend path:

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> OpenAI-compatible backend
```

The current SOUL Lab app can be built and reviewed as a presentation prototype, but it is not yet an authoritative runtime control surface.

## Where to read next

- [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md)
- [Phase 6 Asynchronous RelaySLP Bounded Slice](architecture/phase6_async_relayslp_bounded_slice.md)
- [Phase 6-B0 Durable Queue Contract](architecture/phase6b0_relayslp_durable_queue_contract.md)
- [Phase 6-B1 Dispatch Preflight](architecture/phase6b1_relayslp_dispatch_preflight.md)
- [Phase 6-B2 Atomic Durable Enqueue](architecture/phase6b2_relayslp_atomic_durable_enqueue.md)
- [RelayMEM MVP Implementation Plan](architecture/relaymem_mvp_implementation_plan.md)
- [RelayMEM / RelaySLP Current / Target Boundary](architecture/relaymem_slp_current_target.md)
- [RelayMEM-M3g Reconciliation Apply](architecture/relaymem_m3g_primary_index_log_reconciliation_apply.md)
- [RelayMEM-M3h Recovery Audit](architecture/relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md)
- [SOUL Lab UI MVP](architecture/soul_lab_ui_mvp.md)
- [SOUL Lab UI-A6 Shared Shell / Settings](architecture/soul_lab_ui_a6_shared_shell_settings_handoff.md)
- [SOUL Lab Runtime MVP](architecture/soul_lab_runtime_mvp.md)
