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
  - docs/architecture/phase6_async_relayslp_bounded_slice.md
  - docs/architecture/phase6a1_relayslp_job_admission_contract.md
  - docs/architecture/phase6a2_relayslp_response_handoff_contract.md
---
# RelayLM Project Status

Last reviewed: 2026-06-21 JST

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
Pre-stream hardening: Phase 5-D complete through D2
Stream safety / TTS handoff preparation: Phase 5.5 complete for RelayLM Core
Asynchronous RelaySLP orchestration: Phase 6 complete through helper-only A2

Latest completed bounded slices:
  Phase 5.5-B2 request-runtime SSE suppression wiring
  + gated runtime wrapper for backend SSE bytes
  + default-off ordinary backend forwarding preserved
  + dry-run-only byte-for-byte pass-through diagnostics
  + apply-mode internal marker/candidate suppression
  + visible prefix preservation when safe
  + content-free relayctx_stream_suppression_gate node result

  Phase 5.5-C2 runtime TTS adapter handoff wiring
  + observes only B2 apply-mode safe visible SSE output
  + passes stream bytes through unchanged
  + invokes C0 segmentation and C1 handoff planning at stream end
  + records C0/C1 content-free node results
  + default-off runtime gate and dry-run-only default
  + no TTS execution, audio generation, avatar control, or persistence

  Phase 5.5-C3 TTS adapter transport contract
  + helper-only adapter-facing transport envelope construction
  + consumes C1 runtime-private handoff plans
  + records relayctx_tts_adapter_transport content-free node results
  + no adapter delivery, TTS execution, audio generation, avatar control, or persistence

  Phase 5.5-C4 runtime TTS adapter transport-envelope construction
  + extends C2 stream-final planning to C3 transport-envelope construction
  + records C0/C1/C3 content-free node results in stream-final trace
  + preserves backend SSE bytes unchanged
  + no adapter delivery, TTS execution, audio generation, avatar control, or persistence

  Phase 6-A1 deferred RelaySLP job-admission preflight
  + exact bounded source-lineage and policy validation
  + content-free admission projection
  + no queue I/O, worker, memory write, or SOUL mutation

  Phase 6-A2 response-finalization handoff
  + exact A1 private-result/public-projection validation
  + finalized turn_end dry-run enqueue candidate
  + content-free relaymem_slp_response_handoff node result
  + no durable enqueue, dispatch key, worker, memory write, or SOUL mutation
```

Phase 5.5-B2 is complete as gated request-runtime SSE suppression wiring. Runtime request handling still preserves ordinary backend SSE forwarding by default. The wrapper is used only when `relayctx_stream_unpack_dry_run_enabled=true`; dry-run-only mode remains byte-for-byte pass-through, and apply mode suppresses RelayCTX internal marker/candidate material from user-visible SSE output.

Phase 5.5-C2 is complete as default-off runtime TTS adapter handoff wiring. It runs only after B2 safe visible output is available, observes the already-emitted safe visible SSE content, and records C0/C1 content-free node results without mutating stream bytes or executing TTS/audio/avatar behavior.

Phase 5.5-C3 is complete as a helper-only adapter-facing TTS transport contract. It converts C1 runtime-private handoff plans into content-free runtime-private transport envelopes and node results without adapter transport delivery, TTS/audio/avatar execution, or persistence.

Phase 5.5-C4 is complete as default-off runtime TTS adapter transport-envelope construction. It reuses the existing C2 runtime gate, runs only after B2 safe visible output is available, and records the C3 transport node result after C0/C1 while leaving stream bytes unchanged and performing no adapter delivery or TTS/audio/avatar execution.

Phase 5.5-C1 adds a pure helper for deriving a runtime-private downstream adapter handoff plan from C0 content-free TTS segmentation hints.

Phase 5.5-C0 adds a pure helper for deriving TTS-safe character-range hints from already-safe visible text.

Phase 5.5-B1 adds a pure helper for preserving safe visible stream text while suppressing or blocking RelayCTX internal candidate material.

Phase 5.5 is now closed for RelayLM Core. Concrete TTS execution, audio queueing, Live2D/avatar mapping, motion scheduling, lip-sync, runtime preview, calibration, and adapter failure handling belong to [SOUL Lab Runtime MVP](architecture/soul_lab_runtime_mvp.md), not to Phase 5.5.

Phase 5-C5c is complete as request-local cache-writer wiring for trusted in-process typed parse sources. Runtime request handling still does not parse backend responses, trust frontend metadata as typed parse source, or mutate backend/user-visible payloads. Non-null typed parse `parser_version` values are blocked before writer invocation until parser-versioned lookup/write compatibility exists.

Phase 6-A1 is complete as a default-off, dry-run-first helper-only deferred job-admission preflight. Phase 6-A2 is complete as a default-off, dry-run-only response-finalization handoff that may construct one runtime-private metadata candidate from an accepted finalized `turn_end` A1 result. Neither slice is request-runtime wired or performs queue I/O.

Next candidates remain independently sequenced:

- Phase 6-B: bounded durable RelaySLP queue and dispatch idempotency,
- later SOUL Lab Runtime MVP adapter bridge/runtime work for TTS/audio/avatar execution.

New RelaySOUL execution-gate design documents should still be avoided unless they directly unblock a current runtime safety issue or are part of the later SOUL Lab runtime adapter boundary.

## Current implemented boundary

Current `main` includes:

- OpenAI-compatible `/v1/chat/completions` proxying, routing, and backend forwarding,
- `PipelineContext` and ordered content-free `PipelineNodeResult` collection,
- current profile compilation and RelayCTX Repack phases,
- RelayINT-facing reference-repair compatibility boundary,
- selected RelayMEM retrieval and gated CTX injection,
- pure and gated non-stream RelayCTX Unpack,
- stream sentinel buffer dry-run helper for RelayCTX internal markers,
- stream suppression gate helper for visible prefix preservation and internal marker suppression,
- gated request-runtime stream suppression wrapper for backend SSE bytes,
- TTS-safe segmentation helper for safe visible output range hints,
- TTS adapter handoff contract helper for runtime-private downstream plans,
- runtime TTS adapter handoff observer for B2 safe visible output,
- TTS adapter transport contract helper for runtime-private adapter-facing envelopes,
- runtime TTS adapter transport-envelope construction after stream-final handoff planning,
- managed-route client-message canonicalization dry-run,
- runtime-private client-instruction identity,
- read-only instruction-cache lookup,
- read-only cache-hit RelaySCN projection diagnostics,
- runtime-private typed client-instruction parse validation,
- gated direct cache-write helper for validated typed parse artifacts,
- runtime-private typed parse source gate and cache-writer node wiring,
- client-history exclusion preflight,
- `client_history_exclusion_apply.v0` for supported no-instruction requests,
- `client_history_exclusion_apply.v1` for supported instruction-bearing requests,
- deterministic tokenizer-free CJK-aware token estimation,
- additive lazy RelayRUN recovery-detail helper,
- request-runtime lazy RelayRUN recovery-detail wiring,
- request-level RelayRUN diagnostics/checkpoint/recovery foundations,
- RelaySOUL dry-run/preflight governance foundations,
- RelayMEM-M3a Primary MEM formation candidate helper,
- RelayMEM-M3b Primary MEM source-lineage/write-preflight helper,
- Phase 6-A1 RelaySLP job-admission preflight helper,
- Phase 6-A2 RelaySLP response-finalization handoff helper.

The safe defaults remain unchanged:

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

Default `memory_light` compatibility compilation may therefore still preserve frontend history until the bounded apply path is explicitly enabled. Token-budget truncation also remains opt-in. Client-instruction cache writing remains opt-in and dry-run-only unless an explicit caller disables the dry-run gate and a trusted in-process producer supplies a runtime-private typed parse source. Runtime stream suppression and runtime TTS adapter handoff/transport planning are default-off. RelayLM still does not execute TTS, generate audio, control avatars, or deliver adapter transport.

Phase 6-A1 and A2 are direct helper gates rather than route configuration fields. Their call defaults are disabled and dry-run-only. No request runtime invokes them automatically.

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

## Typed parse and gated cache-write boundary

`relaylm.client_instruction_typed_parse` validates `client_instruction_parse.v1` runtime-private candidates and emits only content-free diagnostics to persisted surfaces.

`relaylm.client_instruction_cache_write` consumes typed parse and instruction identity results to build a runtime-private cache-entry candidate in dry-run mode. With dry-run-only disabled and an explicit existing cache root, it validates reader compatibility and writes one cache entry through a gated atomic writer.

`relaylm.client_instruction_cache_write_runtime` wires the typed parse and writer path into `PipelineContext` using an in-process runtime-private source gate. Missing source blocks writing; disabled typed-parse/cache-write gates clear any pending source; non-null typed parse `parser_version` values are blocked before writer invocation. External request metadata and backend visible response text are not trusted as sources.

This boundary does not parse backend responses or control envelopes, trust frontend metadata as typed parse source, apply RelaySCN policy, mutate backend payloads, or mutate user-visible responses.

## Stream sentinel, suppression, and TTS segmentation boundary

`relaylm.relayctx_stream_unpack` provides a pure Phase 5.5-A helper that observes streamed text fragments for RelayCTX internal sentinels across chunk boundaries.

The Phase 5.5-B1 suppression helper returns runtime-private visible `output_chunks` behind explicit `enabled` and `dry_run_only` gates. It preserves safe visible text before the first internal sentinel and suppresses or blocks internal candidate material when dry-run-only is disabled.

`relaylm.relayctx_stream_suppression_runtime` provides Phase 5.5-B2 gated request-runtime SSE suppression wiring. It wraps backend stream bytes only when stream unpack is explicitly enabled on the route, preserves byte-for-byte forwarding when disabled or dry-run-only, and records content-free suppression diagnostics.

`relaylm.relayctx_tts_segmentation` provides a pure Phase 5.5-C0 helper that derives content-free character-range segmentation hints from already-safe visible chunks. It blocks complete and terminal-partial RelayCTX sentinels and never stores visible text in diagnostics.

`relaylm.relayctx_tts_adapter_handoff` provides a pure Phase 5.5-C1 helper that converts C0 hint results into runtime-private downstream adapter handoff plans. Diagnostics expose only counts, booleans, status values, and reason IDs; visible text, raw hint arrays, and handoff item arrays are omitted.

`relaylm.relayctx_tts_adapter_handoff_runtime` provides Phase 5.5-C2/C4 default-off runtime wiring. It observes only B2 apply-mode safe visible output, invokes C0/C1/C3 at stream end, and records content-free node results while leaving SSE bytes unchanged and performing no adapter delivery.

`relaylm.relayctx_tts_adapter_transport` provides Phase 5.5-C3 adapter-facing transport envelope construction. It consumes only C1 runtime-private handoff plans and records content-free transport diagnostics without adapter delivery, TTS/audio/avatar execution, or persistence. C4 wires this helper into the existing stream-final runtime observer.

## RelayRUN lazy recovery-detail boundary

`relaylm.relayrun_lazy_recovery` provides an additive helper that can construct a minimal content-free runtime checkpoint artifact on ordinary completed paths without constructing the full recovery diagnostic chain.

The `/v1/chat/completions` request-runtime RelayRUN checkpoint builder now calls the lazy helper and lets automatic status/gate detection decide whether full detail is required. It does not force `include_recovery_details=False` from the request runtime.

The helper constructs full detail when blocked, failed, waiting-user, checkpoint-write, checkpoint-index, resume, recovery, visible recovery, output RelaySCN recovery gate, visible apply, or user-action diagnostics require it.

The lazy summary exposes only schema/status/reason IDs and safety booleans. It must not expose raw user/model text, backend payloads, prompt text, response text, snippets, instruction bodies, cache bodies, hashes, or runtime-private candidates.

## RelayMEM / RelaySLP Phase 6 boundary

RelayMEM owns memory candidate meaning, safety scope, source lineage, memory-write preflight, memory-write idempotency, consolidation meaning, and durable page/index/log apply semantics.

Phase 6 owns deferred execution orchestration. Phase 6-A1 validates bounded admission metadata and emits a content-free admission projection. Phase 6-A2 consumes the exact A1 private result and matching projection for finalized `turn_end` results and may create one runtime-private metadata-only dry-run enqueue candidate.

A2 validates that no queue, worker, RelaySLP, memory-write, RelaySOUL, or visible-response side effect has already occurred and that both dispatch and memory-write idempotency keys remain absent. Its public node result omits the candidate, identifiers, namespace value, lineage fingerprint, and both idempotency-key domains.

Dispatch idempotency and memory-write idempotency remain distinct. Phase 6-B will own the former; RelayMEM persistence owns the latter. RelaySLP never directly mutates RelaySOUL.

## Fail-closed and diagnostics posture

Actual managed apply requires an exact typed `applied` result. For v1, the adapter input must exactly equal the selected request-local candidate; downstream mutation causes backend blocking.

Active tool transactions remain blocked because minimum-chain reconstruction is not implemented.

Runtime-private candidates may contain content. Persisted trace, audit, public errors, estimator breakdowns, and node-result projections expose only bounded counts, booleans, status values, source mode, and reason IDs. Source indices, instruction text, token-estimated text, hashes, cache bodies, payload candidates, stream output chunks, TTS segment hints, TTS adapter handoff items, TTS adapter transport items, RelaySLP enqueue candidates, and internal marker text are not persisted.

## Not yet implemented

The runtime does not yet provide:

- response/control-envelope extraction for typed client-instruction parse candidates,
- frontend metadata trust as typed parse source,
- parser-versioned runtime lookup/write compatibility,
- complete Runtime Compile Gate v1 route-authority/fallback/source taxonomy,
- active tool-chain reconstruction,
- cancellation-specific partial-stream recovery beyond the bounded B2 fail-closed stream summary,
- adapter transport delivery,
- TTS execution, audio generation, or avatar control,
- dedicated output-side RelayREF and complete output-side RelaySCN,
- cross-cutting per-node RelayRUN orchestration,
- request-runtime Phase 6-A1/A2 wiring,
- durable RelaySLP queue and dispatch idempotency,
- scheduler/background worker, claim, lease, retry, or terminal execution,
- RelaySLP worker invocation,
- Secondary MEM consolidation runtime,
- Phase 6 page/index/log persistence apply,
- actual RelaySOUL apply, rollback, or persistence execution,
- model-specific exact tokenizer integration.

TTS execution, audio generation, Live2D/avatar control, audio queueing, lip-sync, and adapter failure handling are intentionally not RelayLM Core work items; they belong to SOUL Lab Runtime MVP.

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

RelayLM does not own frontend UI, ASR, TTS execution, transport delivery, or avatar execution. Current streaming remains backend SSE forwarding by default; gated runtime Stream Unpack suppression and runtime TTS adapter handoff/transport planning exist only when their gates are explicitly enabled.

## Where to read next

- [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md)
- [Phase 6 Asynchronous RelaySLP Bounded Slice](architecture/phase6_async_relayslp_bounded_slice.md)
- [Phase 6-A1 RelaySLP Job Admission Contract](architecture/phase6a1_relayslp_job_admission_contract.md)
- [Phase 6-A2 RelaySLP Response-Finalization Handoff Contract](architecture/phase6a2_relayslp_response_handoff_contract.md)
- [Phase 5.5 Stream Unpack Bounded Slice](architecture/phase5_5_stream_unpack_bounded_slice.md)
- [Phase 5.5-C4 Runtime TTS Transport Envelope Wiring](architecture/phase55c4_runtime_tts_transport_envelope_wiring.md)
- [Phase 5.5-C3 TTS Adapter Transport Contract](architecture/phase55c3_tts_adapter_transport_contract.md)
- [Phase 5.5-C2 Runtime TTS Adapter Handoff Wiring](architecture/phase55c2_runtime_tts_adapter_handoff_wiring.md)
- [SOUL Lab Runtime MVP](architecture/soul_lab_runtime_mvp.md)
- [Phase 5.5-B2 Stream Suppression Runtime Wiring Handoff](architecture/phase55b2_stream_suppression_runtime_handoff.md)
- [Phase 5.5-C1 TTS Adapter Handoff Contract](architecture/phase55c1_tts_adapter_handoff_contract.md)
- [Phase 5.5-C0 TTS Segmentation Helper Handoff](architecture/phase55c0_tts_segmentation_helper_handoff.md)
- [Phase 5.5-B1 Stream Suppression Gate Handoff](architecture/phase55b1_stream_suppression_gate_handoff.md)
- [Phase 5.5-A Stream Sentinel Buffer Dry-Run Handoff](architecture/phase55a_stream_sentinel_buffer_dry_run_handoff.md)
- [Phase 5-C5c Runtime Cache-Writer Boundary Handoff](architecture/phase5c5c_runtime_cache_writer_boundary_handoff.md)
- [Phase 5-C5b Gated Client-Instruction Cache Writer Handoff](architecture/phase5c5b_gated_cache_writer_handoff.md)
- [Phase 5-C5a Typed Parse and Cache-Write Preflight Handoff](architecture/phase5c5a_typed_parse_cache_write_preflight_handoff.md)
- [Phase 5-C4b Cache-Hit RelaySCN Projection Handoff](architecture/phase5c4b_cache_hit_relayscn_projection_handoff.md)
- [Phase 5-D2 Lazy RelayRUN Recovery Detail Handoff](architecture/phase5d2_lazy_relayrun_recovery_detail_handoff.md)
- [Phase 5-D1 CJK-Aware Token Estimation Handoff](architecture/phase5d1_cjk_token_estimation_handoff.md)
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md)
- [Client History Authority Contract](architecture/client_history_authority_contract.md)
- [Client Instruction Authority Contract](architecture/client_instruction_authority_contract.md)
- [Runtime Compile Current / Target Boundary](contracts/runtime_compile_current_target.md)
- [Smoke and validation docs](smoke/README.md)

## Update rule

Update this page whenever a boundary moves between design, dry-run, read-only, and apply; a default changes; a supported request shape changes; or a current schema/producer/consumer changes. Later sequencing belongs in the implementation plan.
