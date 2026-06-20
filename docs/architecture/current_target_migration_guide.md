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
---
# RelayLM Current / Target / Migration Guide

## Purpose

This guide distinguishes implemented runtime behavior from target architecture. Detailed component responsibility remains in `pipeline_responsibility_design.md`; implementation sequencing remains in `pipeline_implementation_plan.md`.

## Interpretation rule

Use these labels consistently:

- **Current implemented**: code path, schema, producer, consumer, and smoke coverage exist.
- **Compatibility**: intentionally retained behavior that is not the final architecture.
- **Target**: design intent without a complete current producer/consumer/apply path.
- **Migration**: bounded work required to move from current or compatibility behavior to target behavior.

Historical material under `docs/mvp/` or `docs/architecture/archive/` is evidence, not current authority.

## Current pipeline boundary

The canonical target order remains:

```text
User input
  -> Input-side RelaySCN
  -> Input-side RelayEMO
  -> RelayCTX Repack
  -> Main LLM
  -> RelayCTX Unpack
  -> Return-side RelayEMO
  -> Output-side RelaySCN
  -> User output
```

Current runtime still contains compatibility ordering and diagnostics-only helpers. Do not infer complete target ownership solely from function names or trace order.

## Boundary matrix

| Boundary | Current implemented or compatibility | Target architecture | Required migration |
|---|---|---|---|
| RelaySCN | v0 scene state/policy diagnostics and compatibility consumers | typed input/output scene controller | typed v1 handoffs, ordering migration, downstream consumers |
| Context compiler | profile compiler plus current RelayCTX/RelayMEM compatibility phases | RelayCTX-owned compiler over canonicalized evidence | typed ownership, fallback, complete source taxonomy |
| Client history apply | v0 no-instruction apply and v1 explicit-provenance instruction-bearing apply; default-off | managed context reconstructed only from approved RelayLM state and current evidence | broader compatibility shapes and active transaction preservation |
| Instruction cache | runtime-private identity and strict read-only cache lookup; no writer or projection apply | validated allowlisted RelaySCN projection, then typed parse/write | Phase 5-C4b projection and Phase 5-C5 parse/write |
| Runtime Compile Gate | `CompileApplyDecision`, content-free diagnostics, bounded history-apply forward gate | route-authority-aware plan/result/decision projections and managed fallback | source tracking, fallback builder, complete state taxonomy |
| RelayMEM Retrieval | current v0 retrieval and gated runtime injection | typed INT handoff and separate runtime-private/content-free projections | API and consumer migration |
| RelaySLP | dry-run/preflight foundations | deferred candidate compiler and gated storage apply | orchestration, idempotency, persistence smoke |
| Open-LLM-VTuber | optional OpenAI-compatible frontend; backend SSE forwarding | managed context plus safe Stream Unpack/output pipeline | external E2E and streaming stages |
| RelayRUN recovery | checkpoint/recovery foundations and diagnostics | runtime orchestration with gated visible recovery generation | output gates and user-action handling |
| RelaySOUL | compatibility dry-run/preflight governance | three durable persona sources with explicit approval/apply/rollback | schema and storage migration |

## Client history exclusion apply

### Current no-instruction contract

```text
schema:
  client_history_exclusion_apply.v0

producer/runtime:
  relaylm.client_history_exclusion_apply
  relaylm.client_history_exclusion_apply_runtime
```

The v0 path supports bounded no-instruction managed requests and retains its existing semantics.

### Current instruction-bearing contract

```text
schema:
  client_history_exclusion_apply.v1

source provenance:
  client_instruction_source.v1

producer/runtime:
  relaylm.client_instruction_source
  relaylm.client_history_exclusion_apply_v1_prepare
  relaylm.managed_apply_finalize
  relaylm.pipeline_context
```

Instruction-bearing actual apply is explicit-only. A request must carry the reserved `relaylm.instruction_evidence` control envelope with selected message indices.

Validation requires that selected indices:

- are non-empty, strictly increasing, non-duplicated, and bounded,
- point to in-range `system` or `developer` messages,
- occur before the latest current user turn,
- match request-local `ClientInstructionIdentity` candidates.

Role, content, and position do not establish provenance. Unselected system/developer messages are excluded, which prevents frontend summaries, memory notes, and replayed persona material from being promoted solely because of role encoding.

The successful v1 candidate contains one RelayLM-owned compiled system message plus the exact validated current user message. It excludes prior history, raw instruction objects, unselected instruction candidates, opaque cache content, and the reserved `relaylm` control envelope.

The runtime-private result may contain a rebuilt payload. Persisted projections expose only bounded counts, booleans, status values, source mode, and reason IDs.

## Client instruction evidence rendering

The identity/evidence builder owns canonical raw JSON and source-role labels. The managed compiler renderer owns XML escaping and the final rendered-size bound. The typed legacy `incoming_system_prompt` block is replaced exactly once; rendered output is not searched or rewritten.

## Client instruction cache

Current accepted entry schema remains `relaylm.client_instruction_cache.v0` with strict read-only validation. Current runtime supports hit, miss, blocked, and skipped evidence but does not:

- write cache entries,
- apply cache-hit RelaySCN projections,
- inject opaque cache entries into backend context.

Phase 5-C4b may add an allowlisted RelaySCN projection. Phase 5-C5 may add typed parsing and an independent cache-write gate. A writer must preserve the existing v0 schema exactly or introduce a new version and migrate all producers/consumers together.

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

For v1 history apply, the adapter additionally verifies that the actual forwarded payload exactly equals the selected request-local candidate. Downstream mutation blocks forwarding.

## Streaming boundary

Current streaming primarily forwards backend bytes. Input-side v1 apply uses the same fail-closed authority gate for stream and non-stream requests. Output-side Stream Unpack, internal-envelope suppression, safe segmentation, and TTS-aware forwarding remain target work.

## Safe defaults

```text
client_history_exclusion_apply_enabled=false
client_history_exclusion_apply_dry_run_only=true
```

No migration step may silently enable actual apply, restore raw history after failure, treat client instruction evidence as RelaySOUL authority, expose content-bearing runtime state in generic diagnostics, or reconstruct incomplete tool transactions without a dedicated contract.
