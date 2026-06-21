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

This document defines product and ownership boundaries. It does not make TTS, Live2D, or avatar execution part of the RelayLM Core MVP.

## Sequencing

```text
RelayLM Core MVP
  -> safe LLM runtime, memory, SOUL, RUN, stream boundaries, and content-free TTS handoff metadata

Post-MVP Phase 1: SOUL Lab UI MVP
  -> observe, review, edit, compare, apply, rollback, and audit character state

Post-MVP Phase 2: SOUL Lab Runtime MVP
  -> execute voice/avatar behavior through adapters using RelayLM hints and handoff metadata
```

SOUL Lab UI MVP remains text-first. Runtime MVP starts only after the UI MVP proves character creation/adoption, Home conversation, communication, Lab Observation, and Pod / SOUL Intervention.

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

SOUL Lab Runtime MVP owns:

- adapter bridge consumption of RelayLM runtime-private handoff metadata,
- concrete TTS adapter mapping,
- TTS execution,
- audio queueing,
- speech interruption and cancellation,
- caption / voice timing coordination,
- runtime-private audio-feature or viseme extraction when used for lip-sync,
- Live2D or avatar expression mapping,
- avatar motion scheduling,
- lip-sync timing when supported,
- mouth-state smoothing and audio/avatar clock synchronization,
- blink, gaze, idle-motion, and render-frame scheduling,
- runtime preview, calibration, and mapping UI,
- adapter failure handling and user-facing runtime status.

RelayLM Core must not directly call TTS engines, Live2D runtimes, avatar motion systems, audio playback queues, or OBS/streaming integrations.

## Runtime adapter inputs

The Runtime MVP should consume request-local runtime-private artifacts from RelayLM or SOUL Lab-managed APIs. Conceptual input shape:

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

Phase 5.5 transport-envelope metadata is content-free and offset/count based inside RelayLM Core. Concrete segment text may be present only in runtime-private adapter input owned by the Runtime MVP bridge. Generic trace, audit, public errors, or long-lived diagnostics must use content-free projections.

## Adapter responsibilities

### TTS adapter

The TTS adapter maps safe visible text and engine-neutral style hints to the configured speech engine.

It owns:

- engine selection and capability probing,
- style/prosody mapping,
- pronunciation or caption-only fallback policy,
- request cancellation,
- audio buffer construction,
- TTS failure recovery that preserves caption/text output when safe.

It must not reinterpret internal RelayCTX candidates, bypass RelayRUN emission decisions, or treat RelayEMO hints as permission to override TTS safety policy.

### Audio-driven avatar handoff

Generated TTS audio may drive lip-sync through a runtime-private bridge between the audio runtime and avatar adapter. This bridge is owned entirely by SOUL Lab Runtime MVP, not RelayLM Core.

The runtime may derive bounded transient signals such as:

- amplitude or envelope values,
- coarse frequency-band energy,
- optional phoneme or viseme classes when supported,
- playback-clock position and chunk correlation,
- cancellation, end-of-audio, and interruption events.

These signals are execution inputs, not RelayLM semantic hints or durable character state. They must remain request-local or adapter-local unless a separate protected runtime requirement explicitly justifies retention. They must not be copied into generic RelayLM trace, audit, prompt, MEM, SOUL, or SLP artifacts.

The audio-feature extractor may be a dedicated runtime component or an internal part of the TTS, audio-player, or avatar bridge. The avatar side owns mapping these signals to mouth parameters or discrete mouth states, including smoothing, hysteresis, interpolation, and frame timing.

When audio analysis or lip-sync support is absent or fails, the runtime should degrade to text/TTS without avatar mouth motion. It must not block already-approved text merely because lip-sync is unavailable.

The common boundary intentionally does not define avatar assets, sprite sheets, mouth-position files, model paths, video preparation, or engine-specific authoring formats. Those are implementation details of a selected avatar runtime and are outside the SOUL Lab Runtime MVP contract.

### Avatar adapter

The avatar adapter maps expression and motion classes to runtime-specific names.

It owns:

- Live2D / avatar runtime connection,
- expression preset mapping,
- motion preset mapping,
- intensity-to-parameter mapping,
- timing relative to audio playback,
- lip-sync coordination when supported,
- avatar failure fallback that preserves text/TTS output when safe.

It must not call privileged RelayLM mutation APIs or infer SOUL changes from transient expression hints.

### Audio and timing runtime

The runtime owns:

- first-speakable-chunk enqueue timing,
- queue order and cancellation,
- interruption behavior,
- duplicate replay prevention,
- stop response handling,
- partial-stream failure behavior after already-approved chunks.

Recovery or resume must not enqueue the same chunk twice.

## UI requirements

SOUL Lab Runtime MVP should expose a bounded control surface:

- adapter connection status,
- TTS engine status,
- avatar runtime status,
- current queued chunk count,
- current speaking chunk id,
- current expression/motion class,
- interruption/cancel controls,
- mapping preview for style, expression, and motion classes,
- content-free adapter error reasons.

The UI may preview hint mappings without executing speech or avatar motion. Preview mode must be explicit.

## Failure behavior

TTS failure:

```text
TTS failure
  -> keep caption/text output when safe
  -> stop or skip affected audio item
  -> record content-free adapter failure
  -> continue only when queue state remains valid
```

Avatar failure:

```text
Avatar failure
  -> preserve approved text/TTS path
  -> omit expression or motion
  -> record content-free adapter failure
```

RelayLM stream or safety failure:

```text
stream/safety failure
  -> do not execute new adapter output for blocked chunks
  -> preserve already approved/emitted chunks
  -> prevent duplicate replay during recovery
```

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
- avatar asset creation, alignment, sprite-sheet/video generation, or model-authoring workflows,
- a common asset manifest or engine-specific mouth-tracking file format,
- RelayLM-side audio analysis or viseme extraction,
- engine-specific config as RelayLM architecture authority.

## Relationship to existing documents

- [SOUL Lab UI MVP](soul_lab_ui_mvp.md) owns the text-first Lab product loop and intentionally defers TTS/Live2D/runtime execution.
- [Phase 5.5 Stream Unpack Bounded Slice](phase5_5_stream_unpack_bounded_slice.md) owns RelayLM Core stream safety and TTS handoff metadata preparation through C4, without adapter delivery or execution.
- [AI VTuber Pipeline Profile](ai_vtuber_pipeline_profile.md) defines the RelayLM realtime profile and per-chunk conceptual path.
- [RelayEMO Return-side Expression Design](relayemo_return_side_expression_design.md) owns engine-neutral expression hint boundaries.
- [AI Character Product Principles](ai_character_product_principles.md) owns the broad product invariant that RelayLM is not the frontend, TTS, ASR, or avatar runtime.

This document provides the post-UI-MVP adapter ownership target and should avoid restating exact RelayEMO schemas or Phase 5.5 implementation status.
