# Current / Target / Migration Guide

## Purpose

This guide prevents active RelayLM documents from being read as proof that every described target boundary is already implemented.

Use:

1. [Project Status](../PROJECT_STATUS.md) for the concise current capability view.
2. [Pipeline Implementation Plan](pipeline_implementation_plan.md) for phase status and sequencing.
3. [Pipeline Responsibility Design](pipeline_responsibility_design.md) for stable ownership and canonical target order.
4. Dedicated contracts for exact current schemas and bounded behavior.

## Standard labels

Active documents use these labels:

- **Current implemented** — emitted, consumed, or enforced by current code.
- **Current compatibility** — implemented historical schema, naming, ordering, or allowlist retained until migration.
- **Target architecture** — intended ownership, order, schema, or behavior not fully wired yet.
- **Required migration** — modules, consumers, compatibility handling, and smoke scope that must change together.
- **Historical only** — superseded rationale retained in an archive or redirect.

A `v1` example is not a current wire contract unless the document identifies an implemented producer, consumer, runtime position, and schema.

## Current repository-wide boundaries

Current implementation includes:

- OpenAI-compatible proxy and route handling,
- current profile compiler and RelayCTX Repack phases,
- `CompileApplyDecision` plus the current `mvp-ctx-apply-0` compile-decision diagnostics artifact,
- RelaySCN v0 diagnostics-oriented policy artifact,
- RelayINT compatibility/reference-repair boundary,
- RelayMEM Retrieval v0 and selected gated context injection,
- non-stream RelayCTX Unpack behind gates,
- request-level RelayRUN artifacts,
- dry-run/preflight RelaySOUL governance artifacts,
- no-instruction `client_history_exclusion_apply.v0` behind default-off apply gates.

Current implementation does not yet include:

- the complete instruction-bearing managed-route authority path,
- target RelaySCN v1 runtime order and schemas,
- the complete route-authority-aware Runtime Compile Gate taxonomy,
- explicit forwarded-payload-source typing and a managed fallback builder,
- Stream Unpack and TTS-safe segmentation,
- dedicated output-side RelayREF,
- complete output-side RelaySCN,
- cross-cutting per-node RelayRUN orchestration,
- asynchronous RelaySLP persistence apply,
- actual RelaySOUL apply, rollback, or persistence execution.

## Boundary matrix

| Boundary | Current implemented or compatibility | Target architecture | Required migration |
|---|---|---|---|
| RelaySCN | `relayscn.scene_state.v0`, `relayscn.scene_policy.v0`, diagnostics-oriented helper; current EMO-to-SCN compatibility order | typed v1 scene state/policy and SCN before EMO | `relayscn.py`, EMO fallback, app/PipelineContext ordering, downstream consumers, SCN/EMO smoke |
| Context compiler | current profile compiler uses incoming messages and configured profile/seed memory before target SCN/INT/MEM handoffs | RelayCTX-owned managed compiler over canonicalized evidence | compiler/Repack ordering, typed handoffs, fallback, integration smoke |
| Client history apply | `client_history_exclusion_apply.v0`, no-instruction only, default-off, dry-run by default | supported instruction-bearing managed requests with bounded low-trust evidence | apply contract/runtime, Repack, compatibility gates, smoke |
| Runtime Compile Gate | typed `CompileApplyDecision`; content-free `mvp-ctx-apply-0` compile-decision diagnostics; narrow history-apply backend gate | route-authority-aware plan/result/decision projections, forwarded-payload source, managed fallback, complete state taxonomy | compile gate, fallback builder, PipelineContext source tracking, RelayRUN and authority smoke |
| RelayMEM Retrieval | `relaymem_retrieval.v0`, compatibility INT/REF-shaped input, broad runtime-private artifact | typed INT handoff plus separate runtime-private result and content-free projection | Retrieval API, consumers, projectors, smoke |
| RelaySLP | dry-run/preflight foundations only | deferred candidate compiler and gated page/index/log apply | worker/orchestration, storage, idempotency, persistence smoke |
| Open-LLM-VTuber | optional OpenAI-compatible frontend; current streaming is primarily backend forwarding | managed context reconstruction plus safe Stream Unpack/output pipeline | instruction-aware history apply, streaming stages, external end-to-end smoke |
| RelayRUN recovery generator | diagnostics-only generator-intent artifact exists with execution fixed off | output-pipeline-gated visible recovery generation | generator, output-side gates, user-action handling, recovery smoke |
| RelaySOUL | `mvp-soul-0` five-file compatibility chain; actual execution disabled | three durable persona sources and no normal-chat apply | all candidate/revision/approval/apply/rollback/storage schemas and smoke |

## Schema rules

### RelaySCN

Current:

```text
relayscn.scene_state.v0
relayscn.scene_policy.v0
relayscn.scene_policy_artifact.v0
relaylm.relayscn.build_relayscn_scene_policy_artifact
```

The richer v1 examples are target schemas.

### Client history exclusion apply

Current:

```text
client_history_exclusion_apply.v0
relaylm.client_history_exclusion_apply.build_client_history_exclusion_apply
relaylm.client_history_exclusion_apply_runtime.run_client_history_exclusion_apply_runtime
```

The runtime-private result may contain a rebuilt payload. The persisted projection contains only typed counts, booleans, status, and bounded reason IDs.

### Runtime Compile Gate

Current typed apply decision:

```text
relaylm.compile_gate.CompileApplyDecision
fields:
  should_apply
  mode_applied
  profile_compile_ready
  reason
```

Current content-free diagnostics artifact:

```text
producer:
  relaylm.diagnostics.build_compile_decision_dry_run
schema_version:
  mvp-ctx-apply-0
current request-path states:
  COMPILE_APPLY
  COMPILE_DRY_RUN
```

The diagnostics artifact also carries request-local IDs, apply/diagnostics booleans, selected route/mode/backend metadata, counts, and bounded reason lists. It does not implement explicit route-authority or forwarded-payload-source fields.

The following remain target forms:

```text
relaylm.compile_plan_projection.v1
relaylm.compile_result_projection.v1
relaylm.compile_decision_projection.v1
explicit COMPILE_SHADOW_ONLY
managed COMPILE_FALLBACK
complete BLOCKED taxonomy
route_authority
forwarded_payload_source
```

Current use of `COMPILE_APPLY` or `COMPILE_DRY_RUN` in `mvp-ctx-apply-0` does not prove implementation of the complete target taxonomy.

### RelayMEM and RelaySLP

The following are target forms unless a dedicated current contract says otherwise:

```text
relaymem.retrieval_runtime.v1
relaymem.retrieval_projection.v1
relaymem.slp_projection.v1
scheduled/background RelaySLP execution
complete page/index/log apply
```

### RelaySOUL

Current compatibility:

```text
schema family: mvp-soul-0
target files:
  SOUL.md
  OUTPUT_POLICY.md
  RELATIONSHIP_ANCHOR.md
  STABLE_MEMORY_SUMMARY.md
  SCENE_STATE.md
actual apply / rollback / persistence: not implemented
```

Target ownership:

```text
SOUL.md
OUTPUT_POLICY.md
RELATIONSHIP_ANCHOR.md
```

## Default and execution posture

Current documents should identify whether behavior is:

- default-on or default-off,
- diagnostics-only,
- runtime-private,
- dry-run-only,
- preflight-only,
- read-only,
- shadow-only,
- apply-capable,
- actually applied on the current request path.

A helper or schema existing in code does not by itself prove that its execution is enabled by default or that it mutates runtime state.

## Content boundary

Runtime-private or protected objects may contain semantic content needed for execution, retrieval, compilation, or calibration.

Default persisted trace/audit projections must not contain:

- raw client or user messages,
- backend payload or response text,
- prompt blocks,
- memory snippets or page bodies,
- scene role, setting, task, participant, or constraint values,
- patch text or freeform feedback,
- local paths or secret-bearing URLs,
- arbitrary nested runtime artifacts.

Use typed allowlists rather than generic recursive copying.

## Migration documentation requirement

A target section should identify:

1. current schema/artifact and producer,
2. current consumer/runtime position,
3. target schema/artifact,
4. consumers that must migrate,
5. runtime-order or authority changes,
6. compatibility/version handling,
7. default/dry-run/apply posture,
8. runtime-private versus content-free boundaries,
9. smoke and integration coverage.
