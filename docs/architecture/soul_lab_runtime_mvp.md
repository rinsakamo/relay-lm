---
relaylm_doc_type: architecture
relaylm_authority: soul_lab_post_mvp_runtime_boundary
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: soul_lab
relaylm_update_trigger:
  - SOUL Lab post-MVP sequencing changes
  - VTuber runtime adapter ownership changes
  - TTS or avatar adapter contract changes
relaylm_not_authoritative_for:
  - RelayLM Core current implementation status
  - RelayEMO exact hint schema
  - Phase 5.5 Stream Unpack implementation status
  - concrete TTS engine or Live2D runtime configuration
relaylm_related_authority:
  - soul_lab_ui_mvp.md
  - soul_lab_ui_a7_management_projection_handoff.md
  - phase_i2_real_soul_lab_observation.md
  - ai_vtuber_pipeline_profile.md
  - relayemo_return_side_expression_design.md
  - ai_character_product_principles.md
  - phase5_5_stream_unpack_bounded_slice.md
  - ../PROJECT_STATUS.md
---
# SOUL Lab Runtime MVP

## Purpose

SOUL Lab Runtime MVP is the post-SOUL-Lab-UI runtime adapter layer for voice and avatar execution.

It consumes RelayLM-approved safe output, Phase 5.5 stream/TTS handoff metadata, and engine-neutral expression hints, then maps them to concrete TTS, audio queue, Live2D/avatar expression, motion, and timing behavior.

This document defines product and ownership boundaries. It does not make TTS, Live2D, avatar execution, or static UI bundle serving part of the current RelayLM Core implementation.

## Current product boundary after Phase I-2

The text-first SOUL Lab path is now implemented through real read-only observation:

```text
RelayLM Core request and memory runtime
  -> Phase I-1 real Primary MEM recall and RelayCTX injection
  -> Phase I-2 bounded durable observation evidence
  -> relaylm.soul_lab_app loopback-only management API
  -> strict browser validation
  -> real Lab Observation UI
```

Phase I-2 does not implement the Runtime MVP adapter layer. Its observation receipts are secondary read-model evidence only and are not TTS, audio, avatar, scheduling, or durable character-state events.

The canonical management/observation ASGI ownership is `relaylm.soul_lab_app`. It preserves Core route behavior while adding local-only Lab reads. Observation capture is best-effort and cannot fail a visible response, roll back Primary MEM, change B3 terminal state, or authorize runtime execution.

The next text-first product boundary is Phase I-3 auditable Correct. Voice/avatar Runtime MVP remains later and independent.

## Sequencing

```text
RelayLM Core MVP
  -> safe LLM runtime, memory, SOUL, RUN, stream boundaries, and content-free TTS handoff metadata

SOUL Lab text-first product
  -> UI-A0 through UI-A7
  -> Phase I-1 real memory recall
  -> Phase I-2 real read-only Lab Observation
  -> Phase I-3 auditable Correct

SOUL Lab Runtime MVP
  -> execute voice/avatar behavior through adapters using RelayLM hints and handoff metadata
```

Phase 5.5 closes the RelayLM Core side of stream safety and TTS handoff preparation. It may provide runtime-private segmentation, handoff, and adapter-facing transport metadata. SOUL Lab Runtime MVP owns any delivery or execution of that metadata.

## Ownership boundary

RelayLM Core owns:

- safe visible stream approval,
- visible/internal output separation,
- TTS-safe segmentation hints,
- runtime-private TTS adapter handoff plans,
- runtime-private adapter-facing transport envelopes,
- Return-side RelayEMO engine-neutral hints,
- RelayRUN emission decisions, recovery state, and duplicate-emission prevention metadata,
- content-free diagnostics and adapter telemetry projections.

The text-first SOUL Lab management app owns:

- loopback-only settings and character projections,
- loopback-only Phase I-2 observation reads,
- exact browser-facing schemas,
- character/namespace-scoped read projection,
- explicit separation of real data and local preview data,
- no adapter execution.

SOUL Lab Runtime MVP owns:

- adapter bridge consumption of RelayLM runtime-private handoff metadata,
- concrete TTS adapter mapping and execution,
- audio queueing,
- speech interruption and cancellation,
- caption/voice timing coordination,
- runtime-private audio-feature or viseme extraction when used for lip-sync,
- Live2D or avatar expression mapping,
- avatar motion scheduling,
- lip-sync timing when supported,
- mouth-state smoothing and audio/avatar clock synchronization,
- blink, gaze, idle-motion, and render-frame scheduling,
- runtime preview, calibration, and mapping UI,
- adapter failure handling and user-facing runtime status.

RelayLM Core and Phase I-2 observation must not directly call TTS engines, Live2D runtimes, avatar motion systems, audio playback queues, or OBS/streaming integrations.

## Observation versus execution evidence

Phase I-2 may report bounded statuses such as RelayRUN completion or RelayCTX Repack application. These are inspection results, not commands.

```text
Lab observation receipt
  = read-only evidence of an already completed runtime path

Runtime adapter event
  = request-local execution input for TTS/audio/avatar adapters
```

The two must not be substituted for each other. Observation receipts:

- are not RelayRUN checkpoints,
- are not TTS transport envelopes,
- are not audio queue records,
- are not avatar motion events,
- are not retrieval candidates,
- cannot replay output,
- cannot repair runtime state.

## Runtime adapter inputs

The Runtime MVP should consume request-local runtime-private artifacts from RelayLM or a dedicated SOUL Lab-managed adapter bridge. Conceptual input shape:

```yaml
runtime_adapter_event:
  chunk_id: chunk_001
  emission_decision: emitted
  tts_policy: speak
  segmentation_hint:
    boundary_kind: sentence
    flush_recommended: true
  expression_hints:
    style_class: gentle
    tts_emoji_hint: "😊"
    avatar_expression_class: soft_smile
    avatar_motion_class: small_nod
    expression_intensity: 0.35
  safety:
    internal_marker_detected: false
    protected: false
    blocked_reason_ids: []
```

Phase 5.5 transport-envelope metadata is content-free and offset/count based inside RelayLM Core. Concrete segment text may be present only in runtime-private adapter input owned by the Runtime MVP bridge. Generic trace, audit, public errors, observation APIs, or long-lived diagnostics must not expose concrete segment text.

## Adapter responsibilities

### TTS adapter

The TTS adapter maps safe visible text and engine-neutral style hints to the configured speech engine. It owns engine selection, capability probing, style/prosody mapping, pronunciation fallback, cancellation, audio buffer construction, and failure recovery that preserves caption/text output when safe.

It must not reinterpret internal RelayCTX candidates, bypass RelayRUN emission decisions, use Lab observation receipts as execution input, or treat RelayEMO hints as permission to override safety policy.

### Audio-driven avatar handoff

Generated TTS audio may drive lip-sync through a runtime-private bridge between the audio runtime and avatar adapter. This bridge is owned entirely by SOUL Lab Runtime MVP.

Transient signals may include amplitude/envelope values, coarse frequency energy, optional phoneme/viseme classes, playback-clock correlation, cancellation, and end-of-audio events. They are execution inputs, not durable character state, and must not be copied into generic trace, audit, prompt, MEM, SOUL, SLP, or Phase I-2 observation receipts.

When analysis or lip-sync fails, the runtime should degrade to text/TTS without avatar mouth motion. It must not block already approved text merely because lip-sync is unavailable.

### Avatar adapter

The avatar adapter owns Live2D/avatar connection, expression/motion preset mapping, intensity mapping, timing relative to audio, lip-sync coordination, and fallback that preserves text/TTS output when safe.

It must not call privileged RelayLM mutation APIs or infer SOUL changes from transient expression hints.

### Audio and timing runtime

The runtime owns first-speakable-chunk timing, queue order, cancellation, interruption, duplicate replay prevention, stop-response behavior, and partial-stream failure behavior after already approved chunks. Recovery must not enqueue the same chunk twice.

## UI requirements

SOUL Lab Runtime MVP should expose a bounded control surface for adapter connection, TTS/avatar status, queued chunk count, current speaking chunk, expression/motion class, interruption/cancel controls, mapping preview, and content-free adapter errors.

Preview mode must be explicit. Runtime preview must not be confused with Phase I-2 local observation preview or server-owned observation data.

## Failure behavior

TTS failure preserves approved text/caption output when safe, stops or skips affected audio, records a content-free adapter failure, and continues only when queue state remains valid.

Avatar failure preserves approved text/TTS, omits expression or motion, and records a content-free adapter failure.

RelayLM stream or safety failure prevents new adapter execution for blocked chunks, preserves already approved/emitted chunks, and prevents duplicate replay during recovery.

Observation receipt failure is different: it affects only later Lab inspection and must not change text, memory, queue, TTS, audio, or avatar semantics.

## Non-goals

SOUL Lab Runtime MVP does not implement:

- new RelayLM Core semantic rewriting,
- RelaySOUL automatic mutation,
- universal content moderation,
- ASR ownership,
- OBS or public streaming integration,
- multi-avatar rendering,
- cloud sync,
- frontend-independent always-on background communication,
- avatar asset authoring workflows,
- a common engine-specific mouth-tracking asset format,
- RelayLM-side audio analysis or viseme extraction,
- engine-specific configuration as RelayLM architecture authority.

Phase I-2 additionally does not complete:

- static serving of the built SOUL Lab bundle,
- TTS/audio/avatar adapter delivery or execution,
- Correct/forget/pin/merge/held-review mutation,
- queue scanner/scheduler/daemon lifecycle.

## Relationship to existing documents

- [SOUL Lab UI MVP](soul_lab_ui_mvp.md) owns the text-first Lab product loop.
- [SOUL Lab UI-A7 Management Projection](soul_lab_ui_a7_management_projection_handoff.md) owns the original content-free loopback management read boundary.
- [Phase I-2 Real SOUL Lab Observation](phase_i2_real_soul_lab_observation.md) owns real bounded observation integration and explicitly does not own runtime adapter execution.
- [Phase 5.5 Stream Unpack Bounded Slice](phase5_5_stream_unpack_bounded_slice.md) owns RelayLM Core stream safety and TTS handoff metadata preparation through C4.
- [AI VTuber Pipeline Profile](ai_vtuber_pipeline_profile.md) defines the realtime profile and per-chunk conceptual path.
- [RelayEMO Return-side Expression Design](relayemo_return_side_expression_design.md) owns engine-neutral expression hint boundaries.
- [AI Character Product Principles](ai_character_product_principles.md) owns the broad product invariant that RelayLM is not the frontend, TTS, ASR, or avatar runtime.

<!-- phase-i3-auditable-primary-mem-correct -->
## Phase I-3 auditable Primary MEM Correct — complete (2026-06-24)

Phase I-3 completes the first real observe/correct/retrieve loop. A formed Primary MEM observed through Phase I-2 can be corrected through read-only preflight, bounded semantic diff, explicit short-lived-token apply, immutable successor-page publication through the existing M3e boundary, canonical M3f/M3g index/log convergence, and immutable audit receipt finalization. Existing M2 retrieval resolves only the corrected current revision and existing RelayCTX injection remains the sole prompt path.

Character/namespace isolation, stable logical memory identity, no-clobber publication, exact operation idempotency, one-winner revision fencing, crash recovery, and historical used-memory integrity are preserved. Correction reason, audit receipt, paths, digests, lineage, queue/lease state, and prior full pages are not retrieval inputs or public prompt content.

Authority and exact contracts: `docs/architecture/phase_i3_auditable_primary_mem_correct.md`.

Still separate and unresolved: the I1-G process-exit window after visible-response delivery but before background-finalizer protected-source and B2 queue publication. Phase I-3 does not implement forget, pin/unpin, merge, held apply/discard, Secondary MEM consolidation, RelaySOUL mutation, queue scanner/scheduler/daemon, static UI serving, or TTS/audio/avatar execution.
