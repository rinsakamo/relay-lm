---
relaylm_doc_type: subsystem_architecture
relaylm_authority: soul_lab_voice_avatar_runtime_adapter_architecture
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: soul_lab_runtime
relaylm_update_trigger:
  - voice/TTS/avatar runtime ownership changes
  - RelayLM Core TTS transport handoff boundary changes
  - runtime adapter interruption, queue, or timing responsibility changes
  - SOUL Lab runtime preview/calibration ownership changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - current text-first SOUL Lab browser/server authority
  - exact TTS transport, RelayEMO hint, RelayRUN checkpoint, or adapter event schemas
  - concrete provider credentials, endpoint configuration, Live2D asset formats, or engine-specific APIs
  - RelayMEM, RelaySOUL, RelayREL, RelaySCN, RelayEMO, or RelayCTX durable semantic mutation
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - soul-lab.md
  - ../voice/streaming-and-tts.md
  - ../emotion/affect-modulation.md
  - ../runtime/request-response-pipeline.md
  - ../soul_lab_runtime_mvp.md
  - ../phase5_5_stream_unpack_bounded_slice.md
  - ../relayemo_return_side_expression_design.md
  - ../ai_vtuber_pipeline_profile.md
  - ../../planning/documentation-target-architecture-graph.md
relaylm_related_contracts:
  - ../../contracts/runtime/tts-transport.md
  - ../../contracts/relayrun-checkpoint-and-recovery.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - SOUL Lab runtime and realtime frontend maintainers
  - TTS, audio, avatar, streaming, RelayRUN, and RelayEMO maintainers
  - product, privacy, safety, latency, and adapter reviewers
relaylm_authority_level: subsystem
---
# SOUL Lab Runtime Architecture

## Purpose

This page is the canonical target architecture for SOUL Lab's voice and avatar execution runtime.

It begins **after** RelayLM Core has produced safe, governed runtime outputs and engine-neutral handoff metadata.

The stable separation is:

```text
RelayLM Core
  -> safe visible response stream
  -> TTS-safe segmentation / handoff / transport metadata
  -> engine-neutral expression and runtime decisions

SOUL Lab Runtime
  -> concrete TTS adapter execution
  -> audio queue/playback timing
  -> interruption/cancellation
  -> avatar expression/motion/lip-sync mapping
  -> runtime preview/calibration and adapter health
```

SOUL Lab Runtime is an execution adapter layer. It is not a second semantic model, memory system, persona writer, scene authority, or browser-side substitute for RelayLM Core.

## Relationship to text-first SOUL Lab

The canonical text-first SOUL Lab browser/server boundary lives in [SOUL Lab UI Architecture](soul-lab.md).

That subsystem owns conversation, Character Workspace visibility, observation, lifecycle projection, and explicit governance-action surfaces.

It explicitly does not own TTS, audio, or avatar execution.

SOUL Lab Runtime therefore remains separately evolvable from the text-first management UI.

A Runtime status panel may be presented inside the same product, but product co-location does not merge authority.

## Runtime execution boundary

The target runtime consumes only artifacts that have crossed the owning RelayLM Core safety and emission boundaries.

Conceptually:

```text
approved visible output
  + runtime-private TTS handoff metadata
  + bounded expression/presentation hints
  + emission/cancellation/recovery state
  -> adapter bridge
  -> concrete voice/avatar execution
```

The adapter layer must not reconstruct hidden RelayCTX material, choose memory, reinterpret a blocked response, or create a second semantic response path.

## RelayLM Core remains upstream authority

RelayLM Core retains ownership of:

- request routing and backend execution;
- visible/internal output separation;
- safe-visible stream approval;
- stream suppression/unpack policy;
- TTS-safe segmentation preparation;
- runtime-private TTS handoff and transport metadata;
- engine-neutral affect/expression hints where provided;
- RelayRUN/checkpoint decisions and duplicate-emission protection where applicable;
- content-free diagnostics emitted by those boundaries.

SOUL Lab Runtime may execute approved output. It does not revise those upstream decisions.

## Current Core transport boundary

The current Core TTS transport contract intentionally stops before delivery.

Its `ready` state means that runtime-private offset/count transport metadata is available in memory. It does not mean a provider was contacted, speech was synthesized, audio was produced, or an avatar was moved.

The target SOUL Lab Runtime owns the next step if and when concrete delivery is implemented.

This architecture does not claim that the repository currently contains that concrete execution adapter.

## Runtime-private content boundary

RelayLM Core's generic diagnostics remain content-free.

Concrete TTS execution, however, eventually requires access to approved visible segment text or an equivalent runtime-private content handle.

That content may cross only into the dedicated adapter bridge after the safe-visible boundary.

It must not be copied into:

- generic runtime trace;
- observation receipts;
- public error payloads;
- long-lived adapter telemetry;
- RelayMEM or RelaySOUL merely for speech execution;
- browser diagnostics by default.

The adapter bridge is therefore a runtime-private content-bearing execution domain with content-free outward diagnostics.

## TTS adapter responsibility

The concrete TTS adapter owns provider/engine-specific execution after upstream approval.

Its responsibilities may include:

- configured engine selection;
- capability probing;
- mapping engine-neutral style/prosody hints to supported provider controls;
- pronunciation handling;
- request construction;
- cancellation;
- audio buffer/stream acquisition;
- provider-specific retry or fallback under separately governed policy;
- content-free failure classification.

The adapter does not own whether the underlying response was safe to speak.

## No raw-output fallback

If the Core safe-visible/TTS handoff path is unavailable or blocked, Runtime must not recover by speaking raw backend output.

The stable rule is:

```text
approved safe-visible adapter input available
  -> execution may proceed

safe-visible authority absent or blocked
  -> no new speech execution
```

Availability of a TTS provider is never permission to bypass RelayCTX suppression, output safety, or runtime emission gates.

## Expression and affect hints

RelayEMO or Return-side presentation logic may provide engine-neutral expression hints.

SOUL Lab Runtime may map those hints to concrete provider/avatar controls.

The hints are advisory presentation inputs, not permission to:

- rewrite semantic text;
- weaken a safety boundary;
- mutate durable emotion state;
- mutate SOUL;
- infer a new relationship or scene state.

Unsupported hints should degrade to a neutral/supported presentation rather than create new semantic content.

## Audio queue ownership

Once TTS output is accepted for playback, SOUL Lab Runtime owns the transient audio execution queue.

The queue may track bounded runtime information such as:

- queued speech units;
- current speaking unit;
- playback ordering;
- cancellation state;
- end-of-audio state;
- adapter failure class;
- local playback clock correlation.

This is transient execution state, not RelayMEM, RelayCTX, or durable character state.

## Ordering and duplicate prevention

The runtime must preserve the order of approved speech units unless an explicit interruption/cancellation policy says otherwise.

Recovery must not enqueue or play the same approved unit twice merely because an adapter request was retried or a UI reconnected.

Where RelayRUN/checkpoint metadata provides an emission identity or decision, Runtime must respect that authority rather than invent an independent conflicting replay model.

Exact durable checkpoint fields remain contract authority.

## Interruption and cancellation

Runtime owns concrete interruption behavior for speech/audio/avatar execution.

A bounded interruption may include:

```text
stop accepting new speech units
  -> cancel provider request where supported
  -> stop or drain queued audio according to policy
  -> stop current playback
  -> reset/settle avatar mouth/expression execution
  -> retain content-free cancellation result
```

Interruption does not retroactively change text that RelayLM already emitted to the user.

It also does not erase memory, roll back SOUL, or change the semantic conversation transcript by itself.

## Partial-stream boundary

Voice/avatar execution can begin before a full textual response completes when an approved speakable segment is available.

That creates an irreversible execution boundary similar to visible streaming:

- already played audio cannot be unplayed;
- already shown text cannot be retracted by the adapter;
- later failure must not trigger duplicate speech for already completed units;
- blocked future units must not be spoken merely to keep audio continuity.

Runtime recovery therefore operates on execution state, not by regenerating semantic content.

## TTS failure degradation

When TTS fails after text has been safely approved, the preferred degradation direction is toward less presentation functionality:

```text
approved text remains available
TTS for affected unit stops/skips/fails
avatar may degrade to non-speaking or neutral state
content-free adapter failure is recorded
```

A TTS failure must not make Runtime replace the approved text with provider-generated or fallback semantic text.

Whether later units continue depends on bounded queue validity and runtime policy.

## Avatar adapter responsibility

The concrete avatar adapter owns mapping engine-neutral presentation state into a specific avatar runtime.

Responsibilities may include:

- connection/session with the avatar engine;
- expression preset mapping;
- motion preset mapping;
- intensity mapping;
- lip-sync input mapping;
- audio-relative timing;
- fallback to neutral pose/expression;
- content-free adapter failure classification.

The avatar adapter must not call privileged RelayLM mutation APIs as a side effect of a transient expression.

## Lip-sync and audio features

Runtime may derive transient audio features for lip-sync when the target engine supports them.

Examples include:

- amplitude/envelope;
- coarse energy bands;
- phoneme/viseme classes;
- playback-clock position;
- audio-start/audio-end markers.

These signals are runtime execution data only.

They must not be persisted into SOUL, MEM, REL, SCN, generic trace, or observation receipts as durable character facts.

If analysis fails, the runtime should degrade by omitting mouth motion rather than blocking otherwise valid text/TTS.

## Avatar failure degradation

Avatar failure must not suppress safe text merely because visual presentation is unavailable.

Where TTS remains valid, the runtime may continue with text + voice and omit avatar motion/expression.

Where TTS is also unavailable, text remains the final safe product fallback unless an upstream authority already blocked it.

## Runtime timing ownership

SOUL Lab Runtime owns presentation timing after an adapter event becomes execution-eligible.

This may include:

- first-speakable-chunk timing;
- audio queue timing;
- caption/voice coordination;
- expression/motion timing relative to speech;
- mouth-state smoothing;
- blink/gaze/idle animation scheduling;
- local render-frame scheduling where the avatar engine requires it.

These presentation clocks do not redefine RelayRUN or request-time semantic ordering.

## Observation is not execution

SOUL Lab observation/lifecycle projections describe what another runtime path already did.

They are not adapter commands.

The stable distinction is:

```text
observation receipt
  = read-only evidence / projection

runtime adapter event
  = transient execution input
```

Runtime must never treat an observation receipt as a replay command, TTS transport envelope, audio queue record, or avatar motion event.

## Runtime preview and calibration

SOUL Lab Runtime may expose an explicit preview/calibration surface for adapter-specific presentation mapping.

Examples include:

- connection status;
- TTS engine health;
- avatar engine health;
- expression/motion mapping preview;
- voice/style mapping preview;
- lip-sync calibration;
- queue status;
- interruption/cancel controls.

Preview must be visibly distinct from real conversation execution.

A local preview must not create durable SOUL, memory, relationship, or scene state merely because it exercised an adapter.

## Browser authority remains bounded

A browser control may request connect, preview, cancel, or mapping actions through a bounded local/server API.

The browser must not directly become credential authority or bypass server-side/runtime validation.

Credentials, provider endpoints, local process handles, and privileged adapter state remain server/runtime-owned and should not be exposed in generic browser projections.

## Local-first execution boundary

The target SOUL Lab Runtime is a local execution layer unless a separately governed remote architecture is introduced.

A loopback/local product may communicate with local TTS/avatar processes, but this does not authorize arbitrary network endpoints or cloud credential forwarding.

Remote provider use requires explicit configuration/security authority separate from browser-provided URLs or tokens.

## Failure isolation

Adapter failure is downstream presentation failure.

It must not:

- roll back a completed RelayMEM mutation;
- change a B3 terminal state;
- rewrite a completed RelaySOUL source;
- change RelayREL/RelaySCN current truth;
- make Phase I-2 observation fail a visible response;
- authorize a second backend generation;
- bypass blocked Core output.

The runtime records bounded failure and degrades presentation where possible.

## Content-free operational diagnostics

Generic runtime diagnostics should prefer bounded values such as:

- adapter connected/disconnected;
- engine class;
- queued-unit count;
- speaking/not-speaking;
- expression/motion class;
- cancellation state;
- retryable/non-retryable class;
- bounded reason IDs;
- latency/timing aggregates that do not reveal content.

They should not expose:

- spoken text by default;
- provider credentials;
- endpoint secrets;
- audio bytes;
- avatar asset content;
- hidden RelayCTX material;
- private memory/source bodies;
- raw provider exceptions containing sensitive values.

## Persistence boundary

SOUL Lab Runtime state is primarily transient execution state.

Durable persistence, when needed for configuration or recovery, must be explicitly scoped and must not convert audio/avatar telemetry into character memory or persona truth.

A voice selection or avatar mapping may be durable product configuration, but it remains presentation/runtime configuration rather than `SOUL.md` identity unless separately modeled and approved as character source.

## No automatic SOUL learning

Transient execution feedback such as provider prosody, avatar motion, lip-sync quality, or playback failure must not directly mutate RelaySOUL.

Explicit user calibration feedback may become protected evidence for a later governed proposal, but adapter telemetry is not automatic persona training.

## Stable invariants

- SOUL Lab Runtime begins after RelayLM Core safe-output and handoff authority.
- Concrete TTS/audio/avatar execution is outside the current Core TTS transport contract.
- Runtime never speaks raw backend output as a fallback for missing/blocked safe-visible authority.
- Runtime-private content may enter the dedicated adapter bridge but generic diagnostics remain content-free.
- TTS providers do not gain semantic rewrite or safety authority.
- RelayEMO/presentation hints are advisory mapping inputs, not durable-state mutation permission.
- Audio queues, lip-sync signals, playback clocks, and avatar motions are transient execution state.
- Interruption changes presentation execution, not already-emitted semantic history.
- Recovery prevents duplicate speech/execution for already completed units.
- TTS/avatar failure degrades toward safe text and reduced presentation functionality.
- Observation receipts are not execution commands.
- Browser controls request bounded runtime actions but do not own credentials or privileged adapter state.
- Adapter execution cannot mutate RelayMEM/SOUL/REL/SCN merely as a presentation side effect.
- Preview/calibration is explicit and remains distinct from real conversation execution.
- Current implementation status remains Project Status; this target page does not claim concrete adapter delivery is already implemented.

## Non-goals

This page does not define:

- exact adapter event or queue schemas;
- a specific TTS provider or SDK;
- a provider credential format;
- exact audio codec/buffer implementation;
- exact Live2D/avatar APIs or asset formats;
- ASR/microphone ownership;
- OBS/public-stream integration;
- multi-avatar rendering;
- semantic response generation;
- memory/persona/relationship/scene mutation;
- current implementation-completion claims;
- repository-level sequencing.

## Related architecture

- [SOUL Lab UI](soul-lab.md)
- [Voice Streaming and TTS](../voice/streaming-and-tts.md)
- [Affect Modulation](../emotion/affect-modulation.md)
- [Request / Response Pipeline](../runtime/request-response-pipeline.md)
- [SOUL Lab Runtime MVP source](../soul_lab_runtime_mvp.md)
