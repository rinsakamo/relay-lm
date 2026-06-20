---
relaylm_doc_type: implementation_plan
relaylm_authority: implementation_status_and_phase_sequencing
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - phase lands
  - sequencing changes
  - target-only schema gains producer consumer apply skip block contract projection and smoke coverage
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - exact schema details
  - historical MVP authority
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - pipeline_responsibility_design.md
  - current_target_migration_guide.md
---
# RelayLM Pipeline Implementation Plan

## Purpose

This document owns implementation status, phase sequencing, and dependency boundaries. Component ownership remains in [Pipeline Responsibility Design](pipeline_responsibility_design.md), and current/target interpretation remains in [Current / Target / Migration Guide](current_target_migration_guide.md).

## Status legend

- **complete**: bounded contract, runtime wiring, and smoke coverage exist.
- **mostly complete**: the main boundary exists with bounded follow-up remaining.
- **planned**: design exists without a complete runtime producer/consumer/apply path.
- **deferred**: intentionally not a gate for the active boundary.

## Current position

```text
Phase 5-C managed-route correctness: complete
Phase 5-D1 CJK-aware token estimation: complete
Phase 5-D2 lazy RelayRUN recovery detail: complete

Completed bounded slices:
  Phase 1 PipelineContext/app stabilization
  Phase 2 documentation consolidation
  Phase 3 RelayCTX Repack separation
  Phase 4 RelayINT compatibility boundary
  Phase 4.5 PipelineNodeResult
  Phase 5-A pure non-stream RelayCTX Unpack
  Phase 5-B gated non-stream RelayCTX Unpack
  Phase 5-C1 through C3 authority foundations
  Phase 5-C1a no-instruction managed apply
  Phase 5-C4a instruction-bearing managed apply
  Phase 5-C4b cache-hit RelaySCN projection
  Phase 5-C5a typed parse/cache-write preflight
  Phase 5-D1 CJK-aware conservative token estimation
  Phase 5-D2a lazy RelayRUN recovery-detail helper
  Phase 5-D2b lazy RelayRUN recovery-detail runtime wiring

Next candidates:
  Phase 5-C5b actual cache writer safety boundary
  Phase 5.5 Stream Unpack

Later:
  Phase 6 asynchronous RelaySLP
```

Phase 5-C4b and C5 are optimizations and do not invalidate the completed Phase 5-C correctness boundary. Phase 5-C4b is complete as a read-only diagnostics projection. Phase 5-C5a is complete as typed parse validation plus cache-write preflight only; actual filesystem cache writing remains Phase 5-C5b or later. Phase 5-D1 hardens the shared budget estimator before streaming work without making C4b/C5 prerequisites. Phase 5-D2 is complete as a bounded pre-stream hardening step: helper plus request-runtime wiring.

## Current caveats

- Managed apply remains default-off and dry-run-only by default.
- Current profile compilation still precedes normalized target SCN/INT/Retrieval handoffs.
- Complete Runtime Compile Gate v1 route-authority/fallback/source taxonomy is not implemented.
- Active tool transactions remain blocked because minimum-chain reconstruction is absent.
- Instruction-cache lookup and RelaySCN projection are read-only.
- Phase 5-C5a adds typed parse validation and cache-write preflight only; response/control-envelope extraction and actual cache filesystem writes remain absent.
- RelayCTX Unpack is non-stream only.
- Token estimation is deterministic and CJK-aware but remains tokenizer-free and model-agnostic rather than exact.
- RelayRUN lazy recovery detail is wired into the request-runtime checkpoint builder, but cross-cutting per-node orchestration remains later work.
- RelayREF output observation, RelaySLP persistence, and RelaySOUL actual apply remain later work.

## Phase 1: PipelineContext/app — mostly complete

Implemented request-local original/forwarded payload separation, explicit mutation reasons, runtime-private candidates, ordered node results, and grouped diagnostics. New semantic ownership should remain outside `app.py`.

## Phase 2: documentation consolidation — substantially complete

Current, compatibility, target, migration, and historical material are separated. Documentation maintenance follows runtime changes.

## Phase 3: RelayCTX Repack — mostly complete

Main backend-bound mutation phases are grouped under RelayCTX Repack, including RelayMEM/CTX injection and token-budget application. No new prompt mutation may bypass owned Repack or managed-authority gates.

## Phase 4: RelayINT compatibility boundary — complete

Input-side reference repair is exposed through RelayINT-facing wrappers. Historical RelayREF names remain only where compatibility requires them.

## Phase 4.5: PipelineNodeResult — complete

Frozen request-local node results, deterministic ordering, and typed content-free projections are implemented. Universal routing/retry control remains later work.

## Phase 5-A and 5-B: non-stream RelayCTX Unpack — complete

The pure parser and gated runtime boundary support one bounded trailing update envelope, preserve ordinary visible output, fail closed on malformed candidates, and do not persist CTX/MEM/SOUL/SLP state.

## Phase 5-C: managed-route client authority — correctness complete

### C1 canonicalization — complete as dry-run

Content-free inspection identifies the current user turn, instruction/history counts, multimodal shape, and active tool transactions without mutating payloads.

### C1a no-instruction apply — complete

`client_history_exclusion_apply.v0` supports bounded no-instruction `memory_light` requests. It retains one RelayLM-owned compiled prefix plus the exact current user message. Existing v0 semantics, pass-through exemption, idempotency, and backend gate remain unchanged.

### C2 instruction identity and read-only cache lookup — complete

Deterministic normalized instruction identity, route/character-scoped hashes, request-local content-bearing state, bounded read-only lookup, and content-free diagnostics are implemented. Cache writing is not.

### C3 history-exclusion preflight — complete

Typed original-payload preflight provides current-turn candidates, exclusion counts, resolution classification, active-transaction blocking, and non-mutating content-free projection.

### C4a instruction-bearing managed apply — complete

Implemented contracts:

```text
client_history_exclusion_apply.v1
client_instruction_source.v1
```

Implemented behavior:

- actual apply requires explicit request-local provenance through `relaylm.instruction_evidence`,
- selected indices must be bounded, strictly increasing, in range, before the current user, and match instruction identity,
- role, wording, and message position alone do not establish provenance,
- unselected system/developer messages are excluded, including frontend summaries and memory notes,
- selected candidates preserve source order and source-role labels,
- one typed evidence block replaces exactly one legacy `incoming_system_prompt` block,
- the managed renderer owns escaping and the rendered-size limit,
- the exact text or multimodal current user message is preserved,
- prior history, raw instruction objects, unselected candidates, opaque cache bodies, and the reserved control envelope are excluded,
- cache disabled, miss, and hit have identical correctness behavior,
- active tool transactions remain fail-closed,
- stream and non-stream requests share the input-side authority gate,
- the adapter requires the exact v1 applied candidate,
- persisted diagnostics expose only bounded content-free metadata,
- v0 and pass-through behavior remain unchanged.

Safe defaults remain:

```text
client_history_exclusion_apply_enabled=false
client_history_exclusion_apply_dry_run_only=true
```

### Phase 5-C4b: cache-hit RelaySCN projection — complete

Implemented:

- `client_instruction_relayscn_projection.v0`,
- a read-only helper that consumes only the request-local runtime-private validated cache lookup result,
- a `client_instruction_relayscn_projection` PipelineNodeResult inserted after `client_instruction_cache_lookup`,
- allowlisted enum/count/boolean projection fields for scene type, role scope/source, confidence bucket, context/participant/constraint counts, status, and reason IDs,
- explicit blocking/miss/skipped projection states,
- no raw cache/instruction/role/context/constraint values, cache hashes, paths, backend payloads, or response text in persisted diagnostics,
- no backend forwarding, request payload, RelaySCN policy, or cache write mutation,
- focused direct/runtime smoke and cache lookup regression coverage.

See [Phase 5-C4b Cache-Hit RelaySCN Projection Handoff](phase5c4b_cache_hit_relayscn_projection_handoff.md).

### Phase 5-C5a: typed parse and cache-write preflight — complete

Implemented:

- `client_instruction_parse.v1` runtime-private typed parse validation helper,
- strict fail-closed parse validation for unknown keys, forbidden content-bearing key names, invalid scene/scope/confidence values, path/URL-like content, malformed durable candidates, malformed constraints, and duplicate blocked instruction kinds,
- `client_instruction_cache_write` dry-run/no-op preflight helper,
- default-off `client_instruction_typed_parse_enabled` and `client_instruction_cache_write_enabled` gates,
- default-on `client_instruction_cache_write_dry_run_only`,
- diagnostics-only cache save planning through the existing instruction-cache dry-run `save_requested` plan,
- content-free diagnostics for typed parse and cache-write preflight,
- focused smoke coverage.

Phase 5-C5a does not implement response/control-envelope extraction, RelaySCN apply, backend payload mutation, user-visible response mutation, or filesystem cache writes. Disabling dry-run-only blocks with `cache_writer_not_implemented`.

See [Phase 5-C5a Typed Parse and Cache-Write Preflight Handoff](phase5c5a_typed_parse_cache_write_preflight_handoff.md).

### Phase 5-C5b: actual cache writer — planned

Planned work should add the actual writer only after a separate review of atomic write safety, symlink/out-of-root checks, temp-file replacement, fsync behavior, max entry bytes, and reader compatibility.

## Phase 5-D: pre-stream hardening — complete through D2

### Phase 5-D1: CJK-aware conservative token estimation — complete

Implemented:

- tokenizer-free deterministic character classification,
- ASCII compatibility ratio retention,
- conservative CJK/Kana/Hangul/full-width, punctuation, symbol/emoji, combining/format, and other non-ASCII accounting,
- final estimates that never fall below the historical whole-string estimate,
- content-free detailed count diagnostics,
- shared use by memory assembly and message truncation,
- unchanged feature defaults, ownership, candidate/drop order, and protected-message behavior,
- dedicated Japanese/mixed/code/emoji/memory/truncation regression coverage.

See [Phase 5-D1 CJK-Aware Token Estimation Handoff](phase5d1_cjk_token_estimation_handoff.md).

### Phase 5-D2a: lazy RelayRUN recovery detail helper — complete

Implemented:

- additive `relaylm.relayrun_lazy_recovery` helper module,
- content-free `relayrun.recovery_detail.lazy.v0` summary,
- ordinary completed-path minimal runtime checkpoint artifact construction,
- full-detail fallback for blocked, failed, waiting-user, checkpoint-write, checkpoint-index, resume, recovery, visible recovery, output RelaySCN recovery gate, visible apply, and user-action diagnostics paths,
- explicit include/skip override for tests and narrowly bounded future callers,
- direct smoke coverage and a dedicated CI workflow.

Existing `build_runtime_checkpoint_dry_run_artifact(...)` behavior remains unchanged for direct callers and existing smoke coverage.

### Phase 5-D2b: lazy RelayRUN recovery detail runtime wiring — complete

Implemented:

- `/v1/chat/completions` request-runtime RelayRUN checkpoint construction now calls the lazy helper,
- request runtime passes `backend_forward_status`, `relayrun_checkpoint_write_enabled`, and `relayrun_checkpoint_dry_run_only` into the helper,
- ordinary completed request paths can emit `recovery_detail.constructed=false`,
- failed, blocked, checkpoint, and recovery diagnostics paths still build full recovery detail through automatic status/gate detection,
- request runtime does not force `include_recovery_details=False`,
- dedicated runtime wiring smoke coverage and CI workflow.

See [Phase 5-D2 Lazy RelayRUN Recovery Detail Handoff](phase5d2_lazy_relayrun_recovery_detail_handoff.md).

## Phase 5.5: Stream Unpack — planned

Planned work includes safe visible chunk forwarding, sentinel buffering, internal-envelope suppression, incomplete-candidate blocking, cancellation handling, and TTS-safe segmentation. C4b and C5 are not prerequisites.

## Phase 6: asynchronous RelaySLP — planned

Deferred candidate processing, gated MEM page/index/log updates, idempotency, retry policy, and persistence safety classification belong here. RelaySLP must not directly mutate SOUL.

## Update rule

Update this plan whenever a phase lands, sequencing changes, or a target-only schema gains an implemented producer, consumer, apply/skip/block contract, content-free projection, and smoke coverage.
