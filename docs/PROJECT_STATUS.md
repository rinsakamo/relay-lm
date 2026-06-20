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
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - exact schema details
  - historical implementation evidence
relaylm_related_authority:
  - docs/DOCUMENTATION_MODEL.md
  - docs/architecture/pipeline_responsibility_design.md
  - docs/architecture/pipeline_implementation_plan.md
  - docs/architecture/current_target_migration_guide.md
---
# RelayLM Project Status

Last reviewed: 2026-06-19 JST

## Purpose and authority

This page is the concise current-state view for developers and reviewers. It summarizes what works now, what remains gated, and the next implementation choices.

When documents disagree:

1. [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md) owns component responsibilities and canonical target order.
2. [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) owns detailed implementation status and sequencing.
3. Dedicated module and contract documents own exact schemas and bounded behavior.
4. [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) defines compatibility and target interpretation.
5. `docs/mvp/` is historical implementation evidence only.

## Documentation audit closure

The repository-wide documentation audit, audit Phases 1–8, is complete as of 2026-06-17 JST. Documentation-audit numbering is independent of implementation-phase numbering. Future documentation work is maintenance driven by runtime changes.

## Current implementation position

```text
Managed-route correctness boundary: Phase 5-C complete
Pre-stream hardening: Phase 5-D in progress

Latest completed bounded slice:
  Phase 5-C4b validated cache-hit RelaySCN projection
  + read-only cache-hit projection helper
  + content-free RelaySCN projection PipelineNodeResult
  + no backend/RelaySCN apply
  + no raw cache/instruction/role/context/constraint leakage
  + direct and runtime trace smoke coverage
```

Phase 5-C4b exposes a content-free, diagnostics-only RelaySCN projection from validated instruction-cache hits. The projection is read-only and does not change backend forwarding, request payloads, RelaySCN runtime policy, or cache contents.

Next candidates remain independently sequenced:

- Phase 5-C5: typed parse and cache write,
- Phase 5.5: Stream Unpack and output segmentation.

## Current implemented boundary

Current `main` includes:

- OpenAI-compatible `/v1/chat/completions` proxying, routing, and backend forwarding,
- `PipelineContext` and ordered content-free `PipelineNodeResult` collection,
- current profile compilation and RelayCTX Repack phases,
- RelayINT-facing reference-repair compatibility boundary,
- selected RelayMEM retrieval and gated CTX injection,
- pure and gated non-stream RelayCTX Unpack,
- managed-route client-message canonicalization dry-run,
- runtime-private client-instruction identity,
- read-only instruction-cache lookup,
- read-only cache-hit RelaySCN projection diagnostics,
- client-history exclusion preflight,
- `client_history_exclusion_apply.v0` for supported no-instruction requests,
- `client_history_exclusion_apply.v1` for supported instruction-bearing requests,
- deterministic tokenizer-free CJK-aware token estimation,
- additive lazy RelayRUN recovery-detail helper,
- request-runtime lazy RelayRUN recovery-detail wiring,
- request-level RelayRUN diagnostics/checkpoint/recovery foundations,
- RelaySOUL dry-run/preflight governance foundations.

The safe defaults remain unchanged:

```text
client_history_exclusion_apply_enabled = false
client_history_exclusion_apply_dry_run_only = true
memory.token_budget_truncation_enabled = false
```

Default `memory_light` compatibility compilation may therefore still preserve frontend history until the bounded apply path is explicitly enabled. Token-budget truncation also remains opt-in.

## Token estimation boundary

The current estimator is deterministic and model-agnostic. It does not load a backend tokenizer or claim exact model token counts.

`chars_per_token` remains the compatibility ratio for ASCII word characters. The estimator separately counts:

- ASCII punctuation,
- whitespace,
- CJK, Kana, Hangul, and full-width characters,
- symbols and emoji,
- combining and format characters,
- other non-ASCII characters.

The final estimate never falls below the historical whole-string estimate for the same positive `chars_per_token` value. Empty text remains zero.

`estimate_text_tokens_detailed` exposes only character counts and derived totals. It does not expose or persist source text.

Memory candidate assembly and message truncation share this estimator. Existing candidate order, message drop order, protected system/latest-user behavior, fail-closed preserved-message blocking, and feature defaults are unchanged.

## Managed client-history authority

`client_history_exclusion_apply.v0` supports a managed `memory_light` compiled payload with no client `system` or `developer` messages.

`client_history_exclusion_apply.v1` supports bounded instruction-bearing managed requests only when explicit `client_instruction_source.v1` provenance is present.

Role, content, and position alone are not accepted as provenance. Missing or invalid provenance blocks actual apply. Unselected frontend summaries, memory notes, and replayed persona blocks are excluded from bounded evidence.

A successful managed candidate contains one RelayLM-owned compiled system message plus the exact validated current user message. Prior client history, raw instruction objects, unselected instruction candidates, opaque cache content, and the reserved `relaylm` control envelope are excluded.

## Cache-hit RelaySCN projection boundary

`relaylm.client_instruction_relayscn_projection` consumes the request-local runtime-private cache lookup result and emits a detached `client_instruction_relayscn_projection` PipelineNodeResult.

The projection exposes only enum/count/boolean-style values such as projected scene type, role scope/source, confidence bucket, context/participant/constraint counts, status, and reason IDs.

It must not expose cache hashes, raw instruction text, raw cache JSON, role names, scene setting/task text, participant names, constraint type/value text, filesystem paths, backend payloads, or response text.

The projection is diagnostics-only and read-only. It does not apply RelaySCN policy, mutate backend payloads, or write cache entries.

## RelayRUN lazy recovery-detail boundary

`relaylm.relayrun_lazy_recovery` provides an additive helper that can construct a minimal content-free runtime checkpoint artifact on ordinary completed paths without constructing the full recovery diagnostic chain.

The `/v1/chat/completions` request-runtime RelayRUN checkpoint builder now calls the lazy helper and lets automatic status/gate detection decide whether full detail is required. It does not force `include_recovery_details=False` from the request runtime.

The helper constructs full detail when blocked, failed, waiting-user, checkpoint-write, checkpoint-index, resume, recovery, visible recovery, output RelaySCN recovery gate, visible apply, or user-action diagnostics require it.

The lazy summary exposes only schema/status/reason IDs and safety booleans. It must not expose raw user/model text, backend payloads, prompt text, response text, snippets, instruction bodies, cache bodies, hashes, or runtime-private candidates.

## Fail-closed and diagnostics posture

Actual managed apply requires an exact typed `applied` result. For v1, the adapter input must exactly equal the selected request-local candidate; downstream mutation causes backend blocking.

Active tool transactions remain blocked because minimum-chain reconstruction is not implemented.

Runtime-private candidates may contain content. Persisted trace, audit, public errors, estimator breakdowns, and node-result projections expose only bounded counts, booleans, status values, source mode, and reason IDs. Source indices, instruction text, token-estimated text, hashes, cache bodies, and payload candidates are not persisted.

## Not yet implemented

The runtime does not yet provide:

- typed client-instruction response parsing or cache write,
- complete Runtime Compile Gate v1 route-authority/fallback/source taxonomy,
- active tool-chain reconstruction,
- Stream Unpack and TTS-safe segmentation,
- dedicated output-side RelayREF and complete output-side RelaySCN,
- cross-cutting per-node RelayRUN orchestration,
- asynchronous RelaySLP persistence apply,
- actual RelaySOUL apply, rollback, or persistence execution,
- model-specific exact tokenizer integration.

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

RelayLM does not own frontend UI, ASR, TTS execution, or avatar execution. Current streaming remains primarily backend SSE forwarding; safe Stream Unpack is not implemented.

## Where to read next

- [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md)
- [Phase 5-C4b Cache-Hit RelaySCN Projection Handoff](architecture/phase5c4b_cache_hit_relayscn_projection_handoff.md)
- [Phase 5-D2 Lazy RelayRUN Recovery Detail Handoff](architecture/phase5d2_lazy_relayrun_recovery_detail_handoff.md)
- [Phase 5-D1 CJK-Aware Token Estimation Handoff](architecture/phase5d1_cjk_token_estimation_handoff.md)
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md)
- [Client History Authority Contract](architecture/client_history_authority_contract.md)
- [Client Instruction Authority Contract](architecture/client_instruction_authority_contract.md)
- [Phase 5-C4a implementation handoff](architecture/phase5c4a_instruction_bearing_managed_apply_handoff.md)
- [Runtime Compile Current / Target Boundary](contracts/runtime_compile_current_target.md)
- [Smoke and validation docs](smoke/README.md)

## Update rule

Update this page whenever a boundary moves between design, dry-run, read-only, and apply; a default changes; a supported request shape changes; or a current schema/producer/consumer changes. Later sequencing belongs in the implementation plan.
