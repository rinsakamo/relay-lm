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
  - docs/architecture/phase6b0_relayslp_durable_queue_contract.md
  - docs/architecture/phase6b1_relayslp_dispatch_preflight.md
  - docs/architecture/phase6b2_relayslp_atomic_durable_enqueue.md
  - docs/architecture/relaymem_mvp_implementation_plan.md
  - docs/architecture/relaymem_slp_current_target.md
  - docs/architecture/relaymem_m3e_atomic_primary_page_writer.md
  - docs/architecture/relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - docs/architecture/relaymem_m3g_primary_index_log_reconciliation_apply.md
  - docs/architecture/soul_lab_ui_a0_a1_handoff.md
  - docs/architecture/soul_lab_ui_a2_adoption_handoff.md
  - docs/architecture/soul_lab_ui_a3_communication_handoff.md
  - docs/architecture/soul_lab_ui_a4_pod_handoff.md
  - docs/architecture/soul_lab_ui_a5_memory_inspector_handoff.md
  - docs/architecture/soul_lab_ui_a6_shared_shell_settings_handoff.md
  - docs/architecture/soul_lab_ui_a7_management_projection_handoff.md
---
# RelayLM Project Status

Last reviewed: 2026-06-22 JST

Status baseline implementation commit: `6e34348974d1b641d436a7d3f3aade27024d8ba9`

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
Asynchronous RelaySLP orchestration: durable enqueue implementation complete through Phase 6-B2
RelayMEM independent track: M1/M2 foundations complete; Primary MEM path implemented through M3g apply
SOUL Lab UI independent track: UI-A0 through UI-A7 implemented; A7 is loopback-only read server management projection

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

  Phase 6-B0 durable RelaySLP queue contract
  + durable job and content-free queue projection schemas
  + dispatch-idempotency ownership and deterministic derivation inputs
  + atomic enqueue, duplicate/collision, state, claim/lease, restart/corruption, retry-release, and terminal invariants

  Phase 6-B1 RelaySLP dispatch preflight
  + exact direct A2 result and enqueue-candidate revalidation
  + deterministic versioned dispatch-idempotency key
  + separately domain-separated deterministic job ID
  + runtime-private initial queued durable-job candidate
  + content-free relaymem.slp_queue_status_projection.v0
  + default-off, read-only, dry-run-only; no queue I/O, worker, memory write, or SOUL mutation

  Phase 6-B2 atomic durable enqueue
  + exact direct B1 result and durable-job candidate revalidation
  + gated secure create-if-absent canonical JSON publication with durable timestamps
  + duplicate/collision/corruption/write-failure classification
  + content-free relaymem.slp_queue_status_projection.v0
  + no claim, lease, worker, memory write, SOUL mutation, request-runtime wiring, or visible-response change

  RelayMEM-M3c through M3g Primary MEM persistence path
  + M3c deterministic Primary page candidate
  + M3d exact writer-handoff and store-target preflight
  + M3e default-off atomic no-clobber Primary page writer
  + M3f read-only index/log reconciliation preflight and deterministic ordered plan
  + M3g gated index-before-log reconciliation apply with retryable partial progress
  + no request-runtime wiring, RelaySLP worker, or Secondary MEM consolidation

  SOUL Lab UI-A0 through UI-A7
  + TypeScript/React/Vite shell, mock Home, and read-only Lab Observation preview
  + browser-local first-launch and character-adoption draft flow
  + mock Communication with peer classification, autonomous exchange, Soft Stop, and content-free timeline
  + mock Pod intervention with bounded targets, protected-trait locks, candidate diff, comparison, Hold/Discard, and non-executing Apply/Rollback previews
  + Memory Inspector for formed/held/blocked outcomes and browser-local Correct/Merge/Forget/Pin/Unpin/Discard previews
  + A6 shared owner for route/language/theme/character/navigation lock and mock Settings boundary
  + A7 loopback-only read GET /lab/api/settings and GET /lab/api/characters server projections
  + strict browser schema validation, source-state labeling, and explicit mock fallback
  + no peer transport, management mutation, durable RelaySOUL candidate, persisted memory mutation, rollback, RelayRUN/RelaySLP mutation, transcript persistence, TTS, audio, or avatar execution
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

Phase 6-B0 remains the authoritative durable queue design and state-machine contract. Phase 6-B1 implements exact direct A2 validation, deterministic dispatch/job identities, fixed initial queue/retry metadata, one runtime-private queued durable-job candidate, and a content-free status projection. Phase 6-B2 now consumes only that exact B1 result, assigns durable timestamps, atomically publishes a canonical create-if-absent record, and classifies duplicate/collision/corruption/write failure. B2 performs no claim, lease, retry transition, worker invocation, memory apply, or SOUL mutation.

RelayMEM-M3c through M3g are complete as independent bounded slices. M3e can durably publish a Primary MEM page, M3f reopens and derives a deterministic index/log reconciliation plan, and M3g applies required control-file updates with index-before-log ordering and retryable partial progress.

SOUL Lab UI-A0 through UI-A7 are complete as bounded UI slices. UI-A0 through A6 remain presentation or browser-local interaction surfaces. UI-A7 adds only server-owned, read-only, secret-free runtime-config and character-registry projections and refuses them when RelayLM is configured with a non-loopback listen host. It performs no endpoint health probe, settings write, registry mutation, peer transport, SOUL/MEM inspection, persistence, or process action. If either response fails exact schema validation, including the loopback-only flag, the browser discards the bundle and explicitly shows the UI-A6 mock fallback.

Next boundaries remain independently sequenced:

- Phase 6-B3: claim/lease/retry-release/stale-recovery/terminal-state helpers with no worker execution,
- later RelayMEM Secondary MEM consolidation and Lab-persisted memory operations,
- later SOUL Lab static bundle serving or narrowly scoped management mutation preflights,
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
- RelayMEM-M3c deterministic Primary MEM page-candidate helper,
- RelayMEM-M3d Primary writer-handoff preflight,
- RelayMEM-M3e default-off atomic Primary page writer,
- RelayMEM-M3f read-only Primary index/log reconciliation preflight,
- RelayMEM-M3g gated Primary index/log reconciliation apply,
- SOUL Lab UI-A0/A1 shell, mock Home, and read-only Lab Observation preview,
- SOUL Lab UI-A2 browser-local first-launch and adoption draft flow,
- SOUL Lab UI-A3 browser-local mock Communication session surface,
- SOUL Lab UI-A4 browser-local mock Pod / SOUL Intervention workflow,
- SOUL Lab UI-A5 browser-local Memory Inspector,
- SOUL Lab UI-A6 shared shell and mock Settings boundary,
- SOUL Lab UI-A7 loopback-only read `/lab/api/settings` and `/lab/api/characters` projections with strict browser validation,
- Phase 6-A1 RelaySLP job-admission preflight helper,
- Phase 6-A2 RelaySLP response-finalization handoff helper,
- Phase 6-B0 durable RelaySLP queue contract,
- Phase 6-B1 dispatch/job-record preflight helper,
- Phase 6-B2 atomic durable enqueue helper.

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

Phase 6-A1, A2, B1, and B2 are direct helper gates rather than route configuration fields. No request runtime invokes them automatically. B1 creates only a runtime-private dry-run durable-job candidate; B2 separately defaults to `enabled=false`, `apply_enabled=false`, and `dry_run_only=true` and persists only under all explicit apply gates. RelayMEM-M3e and M3g remain separate direct-helper persistence boundaries.

UI-A7 read routes are enabled by the canonical `relaylm` entry point and are intrinsically read-only. They are also fail-closed for non-loopback configured listen hosts and do not add mutation flags, network probes, browser credential loading, or runtime side effects.

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

`relaylm.client_history_exclusion_apply.v0` supports a managed `memory_light` compiled payload with no client `system` or `developer` messages.

`relaylm.client_history_exclusion_apply.v1` supports bounded instruction-bearing managed requests only when explicit `client_instruction_source.v1` provenance is present.

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

Phase 6-B0 assigns durable queue records, duplicate prevention, queue state, claim/lease fencing, retry-release, terminal-state, restart/corruption, and content-free queue projection to Phase 6 / RelayRUN orchestration.

Phase 6-B1 directly consumes and revalidates the exact runtime-private A2 result. It generates `relaymem.slp_dispatch_key.v0` dispatch identity from the fixed B0 canonical tuple, derives a separate deterministic job ID, initializes an exact queued `relaymem.slp_durable_job.v0` candidate, and emits only the allowlisted content-free queue projection. It does not perform queue I/O.

Phase 6-B2 directly consumes and revalidates the exact B1 result and candidate. It securely opens a dedicated absolute queue root, assigns durable timestamps only for new records, atomically publishes canonical JSON by no-clobber create-if-absent semantics, and never overwrites malformed or colliding records. Its public/default projection remains content-free.

Dispatch idempotency and memory-write idempotency remain distinct. Phase 6 / RelayRUN owns the former; RelayMEM persistence owns the latter. RelaySLP never directly mutates RelaySOUL.

## Fail-closed and diagnostics posture

Actual managed apply requires an exact typed `applied` result. For v1, the adapter input must exactly equal the selected request-local candidate; downstream mutation causes backend blocking.

Active tool transactions remain blocked because minimum-chain reconstruction is not implemented.

Runtime-private candidates may contain content. Persisted trace, audit, public errors, estimator breakdowns, and node-result projections expose only bounded counts, booleans, status values, source mode, and reason IDs. Source indices, instruction text, token-estimated text, hashes, cache bodies, payload candidates, stream output chunks, TTS segment hints, TTS adapter handoff items, TTS adapter transport items, RelaySLP enqueue candidates, durable job candidates, dispatch/job identifiers, lease tokens, and internal marker text are not persisted.

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
- request-runtime Phase 6-A1/A2/B1/B2 wiring,
- scheduler/background worker, claim, lease, retry, or terminal execution,
- RelaySLP worker invocation,
- Secondary MEM consolidation runtime,
- RelayMEM Secondary MEM consolidation and broader Phase 6 persistence apply,
- actual RelaySOUL apply, rollback, or persistence execution,
- SOUL Lab settings or character mutation endpoints,
- SOUL Lab backend connectivity probes or process lifecycle actions,
- RelayLM static serving of the built SOUL Lab UI,
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

RelayLM Core request runtime does not own frontend rendering, ASR, TTS execution, transport delivery, or avatar execution. The repository includes SOUL Lab UI-A0 through UI-A7 under `apps/soul-lab`. UI-A0 through A6 remain mock/browser-local presentation slices; UI-A7 adds only the two loopback-only read Lab management projections. Current streaming remains backend SSE forwarding by default; gated runtime Stream Unpack suppression and runtime TTS adapter handoff/transport planning exist only when their gates are explicitly enabled.

## Where to read next

- [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md)
- [Phase 6 Asynchronous RelaySLP Bounded Slice](architecture/phase6_async_relayslp_bounded_slice.md)
- [Phase 6-A1 RelaySLP Job Admission Contract](architecture/phase6a1_relayslp_job_admission_contract.md)
- [Phase 6-A2 RelaySLP Response-Finalization Handoff Contract](architecture/phase6a2_relayslp_response_handoff_contract.md)
- [Phase 6-B0 RelaySLP Durable Queue Contract](architecture/phase6b0_relayslp_durable_queue_contract.md)
- [Phase 6-B1 RelaySLP Dispatch Preflight](architecture/phase6b1_relayslp_dispatch_preflight.md)
- [Phase 6-B2 RelaySLP Atomic Durable Enqueue](architecture/phase6b2_relayslp_atomic_durable_enqueue.md)
- [RelayMEM MVP Implementation Plan](architecture/relaymem_mvp_implementation_plan.md)
- [RelayMEM / RelaySLP Current / Target Boundary](architecture/relaymem_slp_current_target.md)
- [RelayMEM-M3e Atomic Primary MEM Page Writer](architecture/relaymem_m3e_atomic_primary_page_writer.md)
- [RelayMEM-M3f Primary MEM Index/Log Reconciliation Preflight](architecture/relaymem_m3f_primary_index_log_reconciliation_preflight.md)
- [RelayMEM-M3g Primary MEM Index/Log Reconciliation Apply](architecture/relaymem_m3g_primary_index_log_reconciliation_apply.md)
- [SOUL Lab UI-A0 / UI-A1 Handoff](architecture/soul_lab_ui_a0_a1_handoff.md)
- [SOUL Lab UI-A2 Adoption Handoff](architecture/soul_lab_ui_a2_adoption_handoff.md)
- [SOUL Lab UI-A3 Communication Handoff](architecture/soul_lab_ui_a3_communication_handoff.md)
- [SOUL Lab UI-A4 Pod Handoff](architecture/soul_lab_ui_a4_pod_handoff.md)
- [SOUL Lab UI-A5 Memory Inspector Handoff](architecture/soul_lab_ui_a5_memory_inspector_handoff.md)
- [SOUL Lab UI-A6 Shared Shell / Settings Handoff](architecture/soul_lab_ui_a6_shared_shell_settings_handoff.md)
- [SOUL Lab UI-A7 Read-only Management Projection Handoff](architecture/soul_lab_ui_a7_management_projection_handoff.md)
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
