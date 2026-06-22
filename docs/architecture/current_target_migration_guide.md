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
  - pipeline_implementation_plan.md
  - client_history_authority_contract.md
  - client_instruction_authority_contract.md
  - phase5_5_stream_unpack_bounded_slice.md
  - phase6_async_relayslp_bounded_slice.md
---
# RelayLM Current / Target / Migration Guide

## Purpose

This guide distinguishes implemented runtime behavior from target architecture. Detailed component responsibility remains in `pipeline_responsibility_design.md`; implementation sequencing remains in `pipeline_implementation_plan.md`.

## Interpretation rule

Use these labels consistently:

- **Current implemented**: code path, schema, producer, consumer, and smoke coverage exist for the bounded behavior described.
- **Compatibility**: intentionally retained behavior that is not the final architecture.
- **Target**: design intent without a complete current producer/consumer/apply path.
- **Migration**: bounded work required to move from current or compatibility behavior to target behavior.

A helper, diagnostics projection, or gated writer may be current without implying that its broader semantic consumer or default-on product loop exists.

Historical material under `docs/mvp/` or `docs/architecture/archive/` is evidence, not current authority.

## Current pipeline boundary

The canonical target order remains defined by [Pipeline Responsibility Design](pipeline_responsibility_design.md). Current runtime still contains compatibility ordering, default-off gates, and diagnostics-only helpers. Do not infer complete target ownership solely from function names or trace order.

## Boundary matrix

| Boundary | Current implemented or compatibility | Target architecture | Required migration |
|---|---|---|---|
| RelaySCN | v0 scene policy plus diagnostics-only cache-hit projection; no cache projection semantic apply | typed input/output scene controller | typed v1 handoffs, semantic consumers, ordering migration |
| Context compiler | profile compiler plus current RelayCTX/RelayMEM compatibility phases | RelayCTX-owned compiler over canonicalized evidence | typed ownership, managed fallback, complete source taxonomy |
| Client history apply | v0 no-instruction and v1 explicit-provenance instruction-bearing apply; default-off/dry-run-only by default | managed context reconstructed from approved RelayLM state and current evidence | broader compatibility shapes and active transaction preservation |
| Instruction cache | strict read-only lookup, C4b content-free RelaySCN-facing diagnostics projection, C5 runtime-private typed-parse validation and gated writer wiring | validated scene interpretation with typed producer, semantic RelaySCN apply, versioned lookup/write | trusted control-artifact producer, parser-version compatibility, semantic apply |
| Runtime Compile Gate | `CompileApplyDecision`, content-free diagnostics, bounded history-apply exact-forward gate | route-authority-aware plan/result/decision projections and managed fallback | source tracking, fallback builder, complete state taxonomy |
| RelayMEM Retrieval | current v0 retrieval and gated runtime injection | typed INT handoff and separate runtime-private/content-free projections | API and consumer migration plus I1 end-to-end recall |
| RelaySLP / Phase 6 | A1/A2/B1 helpers and B2 atomic durable enqueue | deferred worker orchestration and gated memory apply | B3 lifecycle, request-runtime enqueue wiring, worker execution |
| Streaming / Phase 5.5 | default-compatible forwarding plus gated B2 suppression and C0-C4 handoff metadata construction | complete default-on output pipeline and runtime adapter delivery | RelayREF/output-SCN consumers, adapter delivery, partial recovery |
| RelayRUN recovery | checkpoint/recovery foundations and diagnostics | runtime orchestration with gated visible recovery generation | output gates and user-action handling |
| RelaySOUL | compatibility dry-run/preflight governance | three durable persona sources with explicit approval/apply/rollback | schema and storage migration |

## Client history exclusion apply

### Current no-instruction contract

```text
schema:
  client_history_exclusion_apply.v0

request class:
  bounded managed request with no client system/developer messages
```

### Current instruction-bearing contract

```text
schema:
  client_history_exclusion_apply.v1

source provenance:
  client_instruction_source.v1
```

Instruction-bearing actual apply is explicit-only. A request must carry the reserved `relaylm.instruction_evidence` control envelope with selected message indices.

Validation requires that selected indices:

- are non-empty, strictly increasing, non-duplicated, and bounded,
- point to in-range `system` or `developer` messages,
- occur before the latest current user turn,
- match request-local `ClientInstructionIdentity` candidates.

Role, content, and position do not establish provenance. Unselected system/developer messages are excluded, including frontend summaries, memory notes, and replayed persona material.

The successful v1 candidate contains one RelayLM-owned compiled system message plus the exact validated current user message. It excludes prior history, raw instruction objects, unselected instruction candidates, opaque cache content, and the reserved control envelope.

Both v0 and v1 remain default-off and dry-run-only by default. Active tool transactions remain blocked until a minimum-chain reconstruction contract exists.

## Client instruction cache and typed parse

Current accepted cache-entry schema remains `relaylm.client_instruction_cache.v0` with strict read-only lookup validation.

Current bounded implementation also includes:

- Phase 5-C4b `client_instruction_relayscn_projection.v0`, which emits a detached content-free diagnostics summary from a validated hit,
- typed-parse candidate validation and content-free node results,
- runtime-private one-shot typed-parse source consumption,
- gated cache-writer planning and apply behind explicit default-off flags.

Current implementation does **not**:

- parse arbitrary backend visible responses,
- trust frontend metadata as a typed-parse source,
- inject opaque cache bodies into backend context,
- apply cache projection semantics to RelaySCN,
- support parser-versioned lookup/write compatibility,
- make cache writing default-on.

With `client_instruction_cache_write_dry_run_only=true`, the writer remains planning-only. With dry-run disabled, it may write only after exact schema, policy, scope, identity, and runtime-private source validation succeeds.

## Runtime Compile Gate

Current typed apply decision remains `CompileApplyDecision`, with content-free `mvp-ctx-apply-0` diagnostics and a narrow managed history-apply forward gate.

The following remain target forms:

```text
relaylm.compile_plan_projection.v1
relaylm.compile_result_projection.v1
relaylm.compile_decision_projection.v1
explicit route_authority
forwarded_payload_source
managed COMPILE_FALLBACK
complete BLOCKED taxonomy
```

For v1 history apply, the adapter verifies that the actual forwarded payload exactly equals the selected request-local candidate. Downstream mutation blocks forwarding.

## Streaming boundary

Current default behavior remains compatible backend SSE forwarding.

Current gated Phase 5.5 behavior includes:

- B2 request-runtime internal-sentinel suppression,
- C0 TTS-safe segmentation hints,
- C1 adapter-handoff planning,
- C2 runtime observation/wiring,
- C3 adapter-facing transport-envelope construction,
- C4 runtime transport-envelope wiring.

These boundaries are default-off, content-free on public diagnostics, and do not deliver transport, execute TTS, generate audio, control an avatar, or persist MEM/SOUL/SLP state.

Complete RelayREF and Output-side RelaySCN processing, adapter delivery, TTS/audio/avatar execution, and generalized partial-stream recovery remain target work.

## RelaySLP and Primary MEM migration

Phase 6 currently reaches B2 atomic durable enqueue. RelayMEM M3a-M3h currently provides direct/helper Primary MEM formation, publication, reconciliation, and recovery-audit boundaries.

The active migration is:

```text
ordinary finalized turn
  -> A1/A2/B1/B2 request-runtime enqueue
  -> B3 claim/lease/retry lifecycle
  -> worker invokes M3a-M3h
  -> later-turn RelayMEM retrieval
  -> RelayCTX injection
```

Queue creation or helper-level memory publication alone does not complete this product loop.

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
```

No migration step may silently enable actual apply, restore raw history after failure, treat client instruction evidence as RelaySOUL authority, expose content-bearing runtime state in generic diagnostics, reconstruct incomplete tool transactions without a dedicated contract, or imply concrete TTS/avatar execution from handoff metadata alone.
