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
  - docs/architecture/client_history_authority_contract.md
  - docs/architecture/client_instruction_authority_contract.md
  - docs/architecture/phase5_5_stream_unpack_bounded_slice.md
  - docs/architecture/phase6_async_relayslp_bounded_slice.md
  - docs/architecture/phase6b0_relayslp_durable_queue_contract.md
  - docs/architecture/phase6b1_relayslp_dispatch_preflight.md
  - docs/architecture/phase6b2_relayslp_atomic_durable_enqueue.md
  - docs/architecture/phase6b3_relayslp_queue_state_helpers.md
  - docs/architecture/relaymem_mvp_implementation_plan.md
  - docs/architecture/relaymem_slp_current_target.md
  - docs/architecture/relaymem_m3g_primary_index_log_reconciliation_apply.md
  - docs/architecture/relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - docs/architecture/soul_lab_ui_mvp.md
  - docs/architecture/soul_lab_ui_a7_management_projection_handoff.md
  - docs/architecture/soul_lab_runtime_mvp.md
---
# RelayLM Project Status

Last reviewed: 2026-06-22 JST

Status reviewed through:

- Phase 6-B3 fenced queue state transitions,
- RelayMEM-M3h recovery audit,
- SOUL Lab UI-A7 read-only management projection,
- PR #359 merge commit `1ee67b4f5a8c20cfbdbef79e99f3cb4e6e90a5b1`.

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
Managed-route correctness: Phase 5-C complete through bounded v0/v1 apply and C5 runtime plumbing
Pre-stream hardening: Phase 5-D complete through D2
Stream safety / TTS handoff preparation: Phase 5.5 complete for RelayLM Core
Asynchronous RelaySLP orchestration: queue lifecycle helpers complete through Phase 6-B3
RelayMEM Primary path: M1/M2 complete; M3a through M3h implemented as direct/helper boundaries
SOUL Lab UI: UI-A0 through UI-A7 implemented; A7 adds local-only read management projections
```

### Core request/runtime foundation

Current `main` includes:

- OpenAI-compatible `/v1/chat/completions` proxying, routing, and backend forwarding,
- `PipelineContext` and ordered content-free `PipelineNodeResult` collection,
- profile compilation and RelayCTX Repack foundations,
- RelayINT-facing reference-repair compatibility,
- selected RelayMEM retrieval and gated RelayCTX injection,
- pure and gated non-stream RelayCTX Unpack,
- Phase 5.5-B2 gated request-runtime stream suppression,
- Phase 5.5-C0 through C4 segmentation, handoff, and transport-envelope metadata construction,
- `client_history_exclusion_apply.v0` for bounded no-instruction managed requests,
- `client_history_exclusion_apply.v1` for bounded explicit-provenance instruction-bearing managed requests,
- strict read-only client-instruction cache lookup,
- C4b content-free RelaySCN-facing cache-hit diagnostics projection,
- C5 runtime-private typed-parse validation and default-off cache-writer wiring,
- CJK-aware deterministic token estimation,
- lazy RelayRUN recovery-detail request-runtime wiring,
- RelaySOUL dry-run/preflight governance foundations.

Current managed-history limitations:

- history-exclusion apply remains default-off and dry-run-only by default,
- v1 requires exact `client_instruction_source.v1` provenance,
- role, wording, and position alone are not provenance,
- active tool transactions remain blocked because minimum-chain reconstruction is absent,
- C4b does not semantically apply RelaySCN state,
- C5 does not parse arbitrary backend visible text or trust frontend metadata as a typed-parse source,
- parser-versioned cache lookup/write compatibility is not implemented.

### Phase 6 RelaySLP orchestration

Implemented:

- A1 deferred job-admission preflight,
- A2 finalized-turn handoff and runtime-private enqueue candidate,
- B0 durable queue schema and state-machine contract,
- Phase 6-B1 RelaySLP dispatch preflight,
- Phase 6-B2 atomic durable enqueue with duplicate/collision/corruption classification,
- Phase 6-B3 fenced queue state transitions for claim, renew, retry release, stale recovery, and terminal commit.

B3 is default-off and dry-run-first. It revalidates complete canonical B2 records, uses revision/state/owner/generation/token fencing, applies nonblocking shared/exclusive queue locking, detects inode and byte CAS conflicts, preserves terminal immutability, and never generates `dead_letter`.

Current limitation:

- A1/A2/B1/B2 are not called automatically from ordinary request finalization,
- B3 is a direct helper and no scheduler or worker invokes it automatically,
- Phase 6-C worker execution is not implemented,
- no worker invokes RelayMEM processing,
- queue persistence and lifecycle control do not yet lead to memory persistence.

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

UI-A0 through UI-A7 provide:

- TypeScript/React/Vite browser shell,
- Japanese-default and English-preview localization,
- light/dark themes,
- active-character selection and character-scoped browser state,
- mock Home and Lab Observation,
- browser-local Adoption,
- mock Communication with Soft Stop,
- mock Pod intervention and non-executing SOUL candidate previews,
- Memory Inspector with non-persistent Correct/Merge/Forget/Pin/Unpin/Discard previews,
- shared shell and Settings/runtime-boundary projections,
- local-only read `GET /lab/api/settings` and `GET /lab/api/characters` server projections,
- exact browser-side allowlist validation with explicit UI-A6 mock fallback,
- configured-listen and actual transport-peer loopback enforcement,
- secret-free endpoint, capability, character-registry, and content-free diagnostics metadata.

Current limitation:

- UI-A7 exposes only bounded runtime configuration and character-registry metadata,
- no latest-run, formed/held/blocked memory, or used-memory read API,
- no peer network request,
- no durable character-registry or memory operation,
- no RelaySOUL apply or rollback,
- no persisted transcript,
- no TTS/audio/avatar execution,
- no static serving of the built SOUL Lab bundle from RelayLM.

## Active implementation priority

The project is integration-first.

### Integration Milestone I1: Primary MEM end-to-end runtime loop

```text
ordinary finalized turn
  -> A1/A2/B1/B2 runtime enqueue
  -> B3 claim/lease/retry lifecycle
  -> Phase 6-C worker execution
  -> M3a-M3h Primary MEM processing
  -> durable page/index/log outcome
  -> later-turn RelayMEM retrieval
  -> RelayCTX injection
  -> response uses formed memory
  -> SOUL Lab reads real latest-run and memory outcome
```

Immediate sequence:

1. Wire finalized managed turns through A1/A2/B1/B2 while keeping visible response delivery independent.
2. Implement Phase 6-C worker execution under the exact active B3 owner/generation/token fence.
3. Invoke existing M3a-M3h boundaries without redefining memory semantics.
4. Add an end-to-end smoke proving next-turn recall and character/namespace isolation.
5. Add real SOUL Lab read APIs for latest run, formed/held/blocked memory, and used memory.
6. Add one auditable Correct operation whose result changes later retrieval behavior.

UI-A7 already supplies the bounded settings/characters read foundation. It does not satisfy I1 memory observation or correction criteria.

B3 is complete as a prerequisite, not as the final product goal. Helper-only completion does not close I1.

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
- stream suppression and TTS handoff metadata construction remain default-off,
- RelayLM Core does not deliver adapter transport or execute TTS/audio/avatar behavior,
- Phase 6 and RelayMEM persistence apply remain explicit gated boundaries rather than ordinary default runtime behavior,
- B3 defaults to `enabled=false`, `dry_run_only=true`, and `apply_enabled=false`,
- UI-A7 management routes are read-only and fail closed unless both configured listen scope and actual transport peer are loopback.

## Not yet implemented

The runtime does not yet provide:

- complete current-turn-only reconstruction for all compatibility-sensitive request shapes,
- active tool-chain reconstruction,
- a trusted backend-response instruction-control artifact producer,
- semantic RelaySCN apply from the C4b cache projection,
- parser-versioned cache lookup/write compatibility,
- request-runtime A1/A2/B1/B2 invocation,
- Phase 6-C worker execution,
- scheduler/background worker execution,
- worker invocation of RelayMEM M3a-M3h,
- end-to-end next-turn recall proof from newly formed runtime memory,
- Secondary MEM consolidation,
- SOUL Lab latest-run and memory-outcome read APIs,
- SOUL Lab settings or character mutation APIs,
- durable memory correction/forget/pin/merge operations,
- actual RelaySOUL apply, rollback, or persistence execution,
- RelayLM static serving of the built SOUL Lab UI,
- adapter transport delivery,
- TTS execution, audio generation, or avatar control,
- complete output-side RelayREF and output-side RelaySCN,
- complete Runtime Compile Gate v1 taxonomy,
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

The SOUL Lab app can be built as a presentation prototype and can read the bounded UI-A7 management projections through the canonical local RelayLM entry point. It is not yet an authoritative runtime control surface or a real memory-observation surface.

## Where to read next

- [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md)
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md)
- [Client History Authority Contract](architecture/client_history_authority_contract.md)
- [Client Instruction Authority Contract](architecture/client_instruction_authority_contract.md)
- [Phase 5.5 Stream Unpack Bounded Slice](architecture/phase5_5_stream_unpack_bounded_slice.md)
- [Phase 6 Asynchronous RelaySLP Bounded Slice](architecture/phase6_async_relayslp_bounded_slice.md)
- [Phase 6-B2 Atomic Durable Enqueue](architecture/phase6b2_relayslp_atomic_durable_enqueue.md)
- [Phase 6-B3 Fenced Queue State Helpers](architecture/phase6b3_relayslp_queue_state_helpers.md)
- [RelayMEM MVP Implementation Plan](architecture/relaymem_mvp_implementation_plan.md)
- [RelayMEM-M3h Recovery Audit](architecture/relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md)
- [SOUL Lab UI-A7 Read-only Management Projection](architecture/soul_lab_ui_a7_management_projection_handoff.md)
- [SOUL Lab Runtime MVP](architecture/soul_lab_runtime_mvp.md)
