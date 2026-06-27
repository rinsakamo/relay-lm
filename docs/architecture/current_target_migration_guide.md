---
relaylm_doc_type: current_target_migration
relaylm_authority: current_target_compatibility_interpretation
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - current implemented boundary changes
  - compatibility behavior changes
  - target interpretation changes
  - migration requirement changes
relaylm_not_authoritative_for:
  - phase sequencing
  - component responsibility and canonical target order
  - exact schema details
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - pipeline_responsibility_design.md
  - project_execution_plan.md
  - relaymem_slp_current_target.md
  - e1_evaluation_consolidation.md
  - wave4_cross_slice_convergence_audit.md
  - phase_i4e_forget_api_ui.md
  - o1d2_scheduler_policy.md
---
# RelayLM Current / Target / Migration Guide

Last reviewed: 2026-06-27 JST

## Purpose

This guide distinguishes implemented runtime behavior from target architecture. It is intentionally compact: Detailed RelayMEM/RelaySLP status lives in [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md), MVP sequencing and roadmap ordering live in [Project Execution Plan](project_execution_plan.md), and repository-wide current status lives in [Project Status](../PROJECT_STATUS.md).

## Interpretation rule

Use these labels consistently:

- **Current implemented**: code path, schema, producer, consumer, and smoke coverage exist for the bounded behavior described.
- **Compatibility**: intentionally retained behavior that is not the final architecture.
- **Target**: design intent without a complete current producer/consumer/apply path.
- **Migration**: bounded work required to move from current or compatibility behavior to target behavior.

A helper, diagnostics projection, or gated writer may be current without implying that its broader semantic consumer or default-on product loop exists. Conversely, completed producer/consumer paths must not remain listed as required migration.

Historical material under `docs/mvp/` or `docs/architecture/archive/` is evidence, not current authority.

## Boundary matrix

| Boundary | Current implemented or compatibility | Target architecture | Required migration |
|---|---|---|---|
| RelaySCN | v0 scene policy plus diagnostics-only cache-hit projection; no cache projection semantic apply | typed input/output scene controller | typed v1 handoffs, semantic consumers, ordering migration |
| Context compiler | profile compiler plus current RelayCTX/RelayMEM compatibility phases | RelayCTX-owned compiler over canonicalized evidence | typed ownership, managed fallback, complete source taxonomy |
| Client history apply | v0 no-instruction and v1 explicit-provenance instruction-bearing apply; default-off/dry-run-only by default | managed context reconstructed from approved RelayLM state and current evidence | broader compatibility shapes and active transaction preservation |
| Instruction cache | strict read-only lookup, C4b content-free RelaySCN-facing diagnostics projection, C5 runtime-private typed-parse validation and gated writer wiring | validated scene interpretation with typed producer, semantic RelaySCN apply, versioned lookup/write | trusted control-artifact producer, parser-version compatibility, semantic apply |
| Runtime Compile Gate | `CompileApplyDecision`, content-free diagnostics, bounded history-apply exact-forward gate | route-authority-aware plan/result/decision projections and managed fallback | source tracking, fallback builder, complete state taxonomy |
| RelayMEM Retrieval | M2 retrieval, strict Primary current-state verification, I-4D lifecycle/prior-revision exclusion, and gated bounded RelayCTX injection | typed RelayINT handoff and separate runtime-private/content-free projections | RelayINT API and consumer migration; Phase I-1 recall and I-4D filtering are complete |
| RelaySLP / Phase 6 / I1-G / O1 | A1/A2/B0-B3, I1-B, C1-0 through C1-5, C2, O0, I1-GA through I1-GE, O1A/B/C/D1, and O1D2 bounded policy wrapper; see `relaymem_slp_current_target.md` for exact state | durable deferred orchestration with automatic operational scheduling and bounded observation/correction | O1E/O1F, O2/O3, and quality/evaluation work; completed C1/C2/I-1/I1-G/O0/O1D1/O1D2 behavior does not require remigration |
| SOUL Lab text product | UI-A0 through UI-A7, Phase I-2 observation, Phase I-3 Correct, UI-B0 real Home conversation, I-4D read-only lifecycle overlay, I-4E loopback Forget API/UI, UI-B1A read-only lifecycle visibility, and E1 evaluation consolidation | full management product for observation, Correct, Forget, Pin, Held review, Merge, RelaySOUL intervention, and optionally trusted Home scene admission | I-4F, Pin/Unpin runtime API/UI/ranking, Held runtime API/UI/evidence, I-6/I-8/I-9; completed I-2/I-3/UI-B0/I-4D/I-4E/UI-B1A/I-5A/I-7A/B/E1 behavior does not require remigration |
| E1 evaluation | E1 evaluation consolidation is current docs/evidence only | local MVP evaluation flow with repeatable bootstrap, provenance-safe formation, and evidence-grounded recall; direct Home trusted scene admission only if later accepted | Direct Home-origin trusted scene admission remains target work; E1-R2/E1-R3/E1-R4 remain quality/ergonomics migrations |
| Pin / Unpin governance | I-5A contract and read-only preflight only | durable Pin / Unpin apply, API/UI, retrieval policy, and ranking behavior | I-5B or equivalent runtime apply/API/UI/ranking work |
| Held outcome governance | I-7A/B contract and read-only Apply / Discard preflight only | explicit Apply / Discard runtime, API/UI, and durable governance evidence | I-7C or equivalent runtime/API/UI/evidence work |
| Streaming / Phase 5.5 | default-compatible forwarding plus gated B2 suppression and C0-C4 handoff metadata construction | complete default-on output pipeline and runtime adapter delivery | RelayREF/output-SCN consumers, adapter delivery, partial recovery |
| RelaySOUL | compatibility dry-run/preflight governance | three durable persona sources with explicit approval/apply/rollback | schema and storage migration |

## Current Wave 4 and E1 compatibility interpretation

Wave 4 adds current implemented boundaries but does not silently promote their follow-on runtime targets:

```text
O1D2 is current implemented as bounded policy wrapper.
O1E/O1F remain target/unimplemented.
I-4E is current implemented as loopback Forget API/UI.
I-4F remains target/unimplemented validation.
UI-B1A is current implemented read-only visibility.
I-5A is current implemented contract/read-only preflight only.
I-7A/B is current implemented contract/read-only preflight only.
E1 evaluation consolidation is current docs/evidence only.
Direct Home-origin trusted scene admission remains target work.
```

## Client history exclusion apply

Current no-instruction schema remains `client_history_exclusion_apply.v0`. Current instruction-bearing schema remains `client_history_exclusion_apply.v1` with `client_instruction_source.v1` provenance. Both remain default-off and dry-run-only by default. Active tool transactions remain blocked until a minimum-chain reconstruction contract exists.

## Client instruction cache and typed parse

Current accepted cache-entry schema remains `relaylm.client_instruction_cache.v0` with strict read-only lookup validation. Current bounded implementation also includes Phase 5-C4b `client_instruction_relayscn_projection.v0`, typed-parse candidate validation and content-free node results, runtime-private one-shot typed-parse source consumption, and gated cache-writer planning/apply behind explicit default-off flags.

Current implementation does not parse arbitrary backend visible responses, trust frontend metadata as a typed-parse source, inject opaque cache bodies into backend context, apply cache projection semantics to RelaySCN, support parser-versioned lookup/write compatibility, or make cache writing default-on.

## Streaming boundary

Current default behavior remains compatible backend SSE forwarding.

Current gated Phase 5.5 behavior includes B2 request-runtime internal-sentinel suppression, C0 TTS-safe segmentation hints, C1 adapter-handoff planning, C2 runtime observation/wiring, C3 adapter-facing transport-envelope construction, and C4 runtime transport-envelope wiring.

These boundaries are default-off, content-free on public diagnostics, and do not deliver transport, execute TTS, generate audio, control an avatar, or persist MEM/SOUL/SLP state. Complete RelayREF and output-side RelaySCN processing, adapter delivery, TTS/audio/avatar execution, and generalized partial-stream recovery remain target work.

## RelaySLP and Primary MEM migration

The current detailed boundary is owned by [RelayMEM / RelaySLP Current / Target Boundary](relaymem_slp_current_target.md). This document records only the compatibility interpretation:

```text
ordinary finalized turn
  -> I1-B source-before-queue publication and B2 enqueue
  -> C2 / C1 worker path or O0 / O1D1 caller path
  -> O1D2 bounded policy hints for later caller decisions
  -> M3a-M3h Primary MEM formation
  -> Phase I-1 later-turn M2 retrieval
  -> I-4D current-state lifecycle filtering
  -> I-4E loopback Forget API/UI over existing authorities
  -> UI-B1A read-only lifecycle visibility
  -> I-5A/I-7A/B read-only governance preflight
  -> E1 evidence consolidation over the proven local lane
  -> RelayCTX bounded injection
```

Completed behavior must not be re-listed as migration work:

- Phase I-1 next-turn recall and character/namespace isolation are complete.
- Phase I-2 real SOUL Lab observation is complete.
- Phase I-3 auditable Correct is complete.
- I1-GA through I1-GE are complete at the durable-finalization boundary.
- O0 is complete as one operator-invoked queue job.
- O1D1 is complete as one accepted-gate replay-before-queue production round.
- O1D2 is complete as bounded scheduler policy/fairness/pacing.
- I-4D retrieval exclusion and historical lifecycle overlay are complete.
- I-4E loopback Forget API/UI is complete.
- UI-B1A read-only lifecycle visibility is complete.
- I-5A contract/read-only Pin / Unpin preflight is complete.
- I-7A/B contract/read-only Held Apply / Discard preflight is complete.
- E1 evaluation consolidation is complete as docs/evidence.

Remaining migration is deliberately narrower:

```text
O1E stale recovery/cancellation/shutdown
  -> O1F operational validation
  -> O2 supervised worker service, if required
  -> O3 always-on operation, if required

I-4F Forget validation

Pin/Unpin runtime apply/API/UI/ranking work
Held Apply/Discard runtime/API/UI/durable evidence work

E1-R1 trusted Home scene-admission path
E1-R2 idempotent character-store bootstrap command
E1-R3 provenance-preserving Primary MEM formation summary
E1-R4 retrieval-response grounding and unsupported-detail suppression

RelayINT / RelayREF / RelaySCN ownership migrations
TTS/audio/avatar runtime adapter execution
```

Queue creation, helper availability, one-round scheduling, or O1D2 policy output is not evidence for recurring automatic processing. O1D1 returns after one round without sleeping, and O1D2 returns recommendations without executing another round.

## Safe defaults

```text
client_history_exclusion_apply_enabled=false
client_history_exclusion_apply_dry_run_only=true
client_instruction_typed_parse_enabled=false
client_instruction_cache_write_enabled=false
client_instruction_cache_write_dry_run_only=true
relayctx_stream_unpack_dry_run_enabled=false
relayctx_stream_unpack_dry_run_only=true
relayctx_tts_adapter_handoff_runtime_enabled=false
relayctx_tts_adapter_handoff_runtime_dry_run_only=true
relaymem_slp_runtime_enqueue_enabled=false
relaymem_slp_runtime_enqueue_dry_run_only=true
relaymem_slp_runtime_enqueue_apply_enabled=false
relaymem_slp_durable_finalization_enabled=false
relaymem_slp_durable_finalization_dry_run_only=true
relaymem_slp_durable_finalization_apply_enabled=false
relaymem_slp_durable_finalization_retention_enabled=false
relaymem_slp_durable_finalization_retention_dry_run_only=true
relaymem_slp_durable_finalization_retention_apply_enabled=false
relaymem_local_worker_enabled=false
relaymem_local_worker_dry_run_only=true
relaymem_local_worker_apply_enabled=false
relaymem_local_scheduler_enabled=false
relaymem_local_scheduler_dry_run_only=true
relaymem_local_scheduler_apply_enabled=false
```

No migration step may silently enable actual apply, restore raw history after failure, treat client instruction evidence as RelaySOUL authority, expose content-bearing runtime state in generic diagnostics, reconstruct incomplete tool transactions without a dedicated contract, imply recurring scheduling/TTS/avatar execution from helper or handoff metadata alone, or treat Home-origin browser metadata as trusted scene admission without a dedicated trust-boundary phase.
