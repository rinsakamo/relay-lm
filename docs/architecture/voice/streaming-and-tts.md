---
relaylm_doc_type: subsystem_architecture
relaylm_authority: streaming_output_and_external_voice_adapter_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: voice
relaylm_update_trigger:
  - streaming visible/internal output boundary changes
  - TTS-safe segmentation or adapter handoff ownership changes
  - adapter transport or concrete voice execution boundary changes
  - return-side expression hints or realtime frontend integration changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - exact SSE, sentinel, hint, handoff, transport, or adapter schemas
  - response semantic generation, scene classification, affect estimation, or context selection
  - concrete TTS engine, audio queue, lip-sync, avatar, or frontend implementation details
  - runtime checkpoint/recovery, persistence, or memory lifecycle behavior
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../pipeline-responsibilities.md
  - ../runtime/request-response-pipeline.md
  - ../phase5_5_stream_unpack_bounded_slice.md
  - ../phase55c1_tts_adapter_handoff_contract.md
  - ../phase55c3_tts_adapter_transport_contract.md
  - ../emotion/affect-modulation.md
  - ../open_llm_vtuber_integration.md
  - ../../planning/documentation-target-architecture-graph.md
relaylm_related_contracts:
  - ../../contracts/pipeline_node_result_contract.md
  - ../../contracts/runtime_compile_artifact_contract.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - streaming runtime and RelayCTX maintainers
  - realtime frontend and adapter maintainers
  - TTS, avatar, latency, privacy, and output-safety reviewers
relaylm_authority_level: subsystem
---
# Voice Streaming and TTS Architecture

## Purpose

This page is the canonical responsibility map for RelayLM's streaming-output-to-voice boundary.

The stable architecture separates four concerns:

```text
backend stream
  -> safe visible/internal separation
  -> TTS-safe segmentation
  -> engine-neutral adapter handoff / transport metadata
  -> external TTS / audio / avatar execution
```

RelayLM Core owns the safety-preserving preparation boundary. Concrete speech generation and avatar execution remain downstream adapter/runtime responsibilities.

The central invariant is:

```text
visible output
  != internal candidate material
  != TTS segmentation metadata
  != adapter transport metadata
  != executed audio/avatar behavior
```

No later voice stage may reinterpret an earlier artifact as broader semantic or persistence authority.

## Current versus target implementation

Current Phase 5.5 implements the RelayLM Core preparation boundary through bounded, gated streaming helpers and runtime wiring:

- stream sentinel observation;
- internal-sentinel suppression on the optional safe stream path;
- TTS-safe segmentation hints;
- TTS adapter handoff planning;
- adapter-facing transport-envelope construction;
- content-free node-result diagnostics.

The current path remains default-compatible: ordinary backend SSE forwarding is preserved unless the relevant guarded stream path is explicitly enabled.

RelayLM Core currently does **not** deliver transport to a TTS endpoint, synthesize audio, queue/play audio, drive lip-sync, control Live2D/avatar motion, or persist semantic state from this path.

Those execution responsibilities remain external/later runtime work. Project Status remains authoritative for exact enablement and completion.

## Voice preparation begins only from safe visible output

TTS preparation must consume output that has already passed the owning visible/internal separation boundary.

It must not derive speech segments directly from raw backend chunks when those chunks may still contain internal RelayCTX markers, incomplete internal candidates, or ambiguous structured material.

The stable order is:

```text
raw backend stream
  -> RelayCTX stream-safe observation/suppression
  -> safe visible stream
  -> segmentation
  -> handoff
  -> transport metadata
```

If safe visible output cannot be established, downstream voice preparation fails closed rather than attempting to recover text from internal or malformed material.

## Streaming compatibility is preserved by default

RelayLM remains an OpenAI-compatible streaming proxy.

A voice-oriented path must not silently change ordinary streaming behavior merely because TTS support exists.

When optional stream safety/TTS gates are disabled or dry-run-only, the implementation preserves the documented compatibility behavior and does not claim concrete voice execution.

Architecture must therefore distinguish:

- compatible visible SSE forwarding;
- optional safe-stream observation/suppression;
- voice preparation metadata;
- external voice execution.

A metadata-ready state is not proof that audio was generated or delivered.

## RelayCTX owns visible/internal separation

RelayCTX Unpack and its streaming safety helpers own the distinction between user-visible response content and bounded internal candidate material.

Voice preparation consumes that result; it does not become a second parser of internal semantic envelopes.

The voice boundary must not:

- expose complete or partial internal sentinels to speech consumers;
- infer that malformed internal material is safe visible prose;
- recreate hidden candidate semantics from surrounding text;
- persist internal candidate bodies for later TTS recovery;
- treat an adapter's willingness to speak text as evidence that the text is safe to expose.

When the stream boundary blocks material, downstream TTS stages remain blocked for that material.

## Partial-stream safety is irreversible

Streaming creates a special failure constraint: already emitted visible output cannot be un-emitted or silently replayed as a replacement response.

The safe streaming boundary therefore preserves visible prefixes while failing closed around incomplete or internal material.

A failure after visible emission must not cause:

- duplicate replay of previously emitted text;
- fallback to the raw unsuppressed backend stream;
- reconstruction from excluded internal candidates;
- a second semantic response path;
- TTS playback of content that the visible-output boundary rejected.

Runtime recovery remains owned by RelayRUN and the request/response pipeline.

## TTS-safe segmentation is structural, not semantic rewriting

Segmentation exists to split already-approved visible text into bounded speech-friendly units.

It may use deterministic boundaries such as:

- sentence punctuation;
- newline boundaries;
- configured maximum-length boundaries;
- stream-final boundaries;
- language-appropriate punctuation recognized by the owning helper.

Segmentation does not own response meaning.

It must not:

- paraphrase or summarize the assistant response;
- add emotional wording;
- delete semantically meaningful content to improve speech flow;
- change facts, commitments, refusals, or safety language;
- reinterpret scene, intent, relationship, or memory state.

A segment range or segmentation hint is a delivery artifact, not a new response-authority artifact.

## Segmentation remains subordinate to suppression

A candidate segment is eligible only when its source text is part of the safe visible output.

Internal sentinel detection, malformed observation, or blocked upstream status must propagate conservatively.

The voice layer cannot route around a blocked stream boundary by re-reading raw SSE, backend payloads, frontend history, or internal trace content.

This preserves one visible-output authority rather than creating a TTS-specific disclosure path.

## Adapter handoff is engine-neutral

RelayLM Core may prepare bounded runtime-private handoff metadata for a downstream voice adapter.

The handoff may identify approved segment ordering and bounded delivery hints, but it does not execute speech.

Engine-neutral handoff keeps RelayLM semantics independent from a specific TTS provider, audio library, avatar engine, or frontend.

The handoff must not acquire:

- durable persona authority;
- scene authority;
- relationship authority;
- memory authority;
- final response wording authority;
- endpoint credential authority;
- audio-device ownership.

Adapter-specific mapping happens outside the semantic core.

## Transport envelope is not transport delivery

A runtime-private transport envelope is a prepared message for a future/downstream adapter bridge.

Envelope construction and envelope delivery are separate lifecycle states.

```text
safe segment
  -> handoff candidate
  -> transport envelope candidate
  -> external delivery
  -> external execution
```

Current RelayLM Core stops before external delivery/execution.

A `ready` transport-envelope state means the bounded metadata is eligible for the downstream bridge. It does not mean:

- an endpoint was contacted;
- credentials were used;
- audio was synthesized;
- playback occurred;
- an avatar moved;
- lip-sync completed.

Generic diagnostics must preserve this distinction.

## Concrete TTS execution remains external

Concrete TTS execution belongs to a dedicated external adapter/runtime boundary, such as the later SOUL Lab Runtime path or another explicitly governed realtime frontend adapter.

That execution boundary may own:

- TTS engine/provider selection;
- endpoint and credential handling;
- synthesis request mapping;
- audio generation;
- audio queueing/playback;
- caption/audio timing coordination;
- retry/cancellation appropriate to the adapter;
- engine-specific voice calibration.

None of those responsibilities make the adapter authoritative for RelayLM semantic state.

The adapter consumes approved output; it does not decide what RelayLM meant to say.

## Avatar execution is adjacent but separate

Return-side affect or expression hints may be useful to avatar/display adapters, but voice architecture does not make TTS and avatar control one semantic authority.

An avatar adapter may consume engine-neutral expression/motion hints under its own mapping rules.

It must not infer disclosure permission, scene truth, relationship state, or durable emotion from speech segments or delivery timing.

TTS success/failure must not mutate the response meaning or durable character state.

## RelayEMO provides hints, not executable truth

RelayEMO may provide bounded return-side expression hints after response content exists.

Those hints can influence external presentation such as speaking style, display expression, or avatar motion where supported.

They remain subordinate to the already-approved response and scene/privacy boundaries.

RelayEMO does not directly call the TTS engine and does not turn a transient affect estimate into a durable voice/persona rewrite.

A voice adapter must not treat an affect hint as permission to alter the semantic text.

## Durable voice/persona policy stays upstream

Stable character voice, style, and output policy remain part of approved character/source authority and the normal semantic/context pipeline.

The TTS boundary may map approved style hints to engine controls, but it does not become the editable source of personality.

Changing a TTS voice model, prosody control, or avatar expression mapping does not by itself change RelaySOUL, relationship state, memory, or output policy.

Likewise, adapter telemetry must not silently train or rewrite durable persona policy.

## Streaming transport remains protocol-preserving

RelayLM must preserve the expected OpenAI-compatible streaming protocol outside explicitly governed transformations.

The stream safety layer may buffer the minimum material required to distinguish safe visible content from internal/incomplete content, but it does not own arbitrary protocol rewriting.

Malformed UTF-8, malformed SSE JSON, ambiguous content fields, backend iterator failure, or incomplete internal material must follow the owning fail-closed behavior.

Voice preparation cannot reinterpret malformed transport as valid assistant prose simply to maintain speech continuity.

## Non-stream responses do not require a fake stream

The architecture does not require all non-stream responses to be converted into synthetic stream frames merely for TTS.

A downstream adapter may consume a bounded approved visible response through an appropriate owning interface.

The same semantic invariants still apply:

- only approved visible content is eligible;
- segmentation is delivery-only;
- adapter execution is downstream;
- diagnostics remain content-free;
- voice execution creates no durable semantic authority.

Exact non-stream adapter interfaces remain outside this architecture page.

## Content-bearing runtime artifacts stay private

Visible text is necessarily content-bearing within the active response path.

Segmentation and adapter preparation may require runtime-private access to that text or bounded references to it.

That requirement does not authorize content-bearing generic traces, checkpoint summaries, generated indexes, or public status artifacts.

Runtime-private artifacts and public/content-free projections remain separate.

## Public diagnostics are content-free

Default streaming/TTS diagnostics may expose bounded values such as:

- enabled/dry-run state;
- stream-safe status;
- suppression detected/blocked booleans;
- candidate/emitted segment counts;
- handoff candidate/emitted counts;
- transport candidate/emitted counts;
- segment length bands or bounded counts;
- execution-request booleans;
- reason/validation IDs;
- adapter-stage status.

They must not expose by default:

- visible response text;
- raw SSE frames;
- internal marker literals;
- internal candidate bodies;
- raw segment arrays;
- handoff/transport item arrays containing content-bearing material;
- endpoint URLs or credentials;
- audio bytes;
- avatar commands;
- free-form model rationale.

Content-free status must never become a second transcript.

## No persistence from the voice preparation path

The streaming/TTS preparation path does not own durable writes to:

- MEM;
- SOUL;
- REL;
- SCN;
- RelayCTX working state;
- SLP queues or candidates;
- Character Workspace sources.

Voice preparation may produce transient/runtime-private artifacts required for the current response delivery only.

A speech error, segmentation decision, or adapter result does not itself justify a memory, relationship, scene, or persona mutation.

If adapter telemetry is ever retained, its governance requires a separate evidence/observability decision.

## Cancellation and interruption remain explicit owners

Realtime voice systems may need cancellation, interruption, barge-in, or playback-stop behavior.

Those effects are not inferred from TTS segmentation metadata alone.

Runtime/adapter owners must define which authenticated event can cancel generation, stop queued audio, or discard pending adapter work.

The voice preparation layer does not invent an interruption authority from user text, attention scores, or avatar state.

Already emitted response text and already played audio remain observable history; cancellation cannot pretend they never occurred.

## Frontend integration does not transfer semantic authority

Open-LLM-VTuber and similar realtime frontends may own ASR, TTS engines, playback, avatar runtime, and visible conversation UI.

On RelayLM-managed routes they do not become durable persona, context, scene, relationship, or memory authorities merely because they render or speak the response.

RelayLM owns the managed backend-bound context and safe visible/internal output boundary; the frontend owns its local execution surfaces.

Pass-through routes remain an explicit delegated-authority mode and are not evidence that managed routes should trust arbitrary frontend persona/history content.

## Failure behavior

Voice preparation fails toward less execution and no broader semantic authority.

```text
unsafe or ambiguous stream material
  -> block affected downstream TTS preparation
  -> do not expose internal content

segmentation invalid
  -> no affected handoff emission
  -> visible response authority unchanged

handoff blocked/invalid
  -> no transport candidate for affected item

transport metadata blocked/invalid
  -> no external-delivery implication

external TTS failure
  -> adapter/runtime failure handling
  -> no semantic response rewrite or memory fallback
```

A failure must never cause fallback from safe visible output to raw backend/internal content.

## Relationship to perceived latency

Streaming and TTS strongly affect perceived latency, but the voice subsystem does not own the repository-wide latency budget.

This page owns safe voice preparation and adapter boundaries. The performance architecture owns measurement categories, timing budgets, and optimization tradeoffs.

A latency optimization cannot weaken internal-content suppression, scene/privacy policy, output safety, or semantic authority separation.

## Stable authority flow

```text
Main LLM/backend
  -> RelayCTX stream/output safety
  -> approved visible output
  -> TTS-safe segmentation
  -> engine-neutral handoff
  -> transport metadata
  -> external adapter/runtime
       -> TTS/audio
       -> optional avatar/display execution

RelayRUN owns orchestration/recovery.
RelayEMO may supply bounded presentation hints.
RelaySCN/privacy/safety remain authoritative upstream.
No voice stage writes durable semantic state.
```

## Stable invariants

- Safe visible output is the only source eligible for TTS preparation.
- Internal and incomplete candidate material never becomes speech merely because a TTS adapter can consume text.
- Streaming compatibility remains preserved by default unless an explicit governed gate changes the path.
- Already emitted visible output is not duplicated or replaced after partial-stream failure.
- TTS segmentation is structural delivery preparation, not semantic rewriting.
- Segmentation remains subordinate to the owning suppression/output-safety boundary.
- Adapter handoff metadata is engine-neutral and non-authoritative for semantic state.
- Transport-envelope construction is not external delivery.
- RelayLM Core's current Phase 5.5 boundary does not execute TTS, audio, avatar, or transport I/O.
- Concrete voice/avatar execution remains in the external adapter/runtime boundary.
- RelayEMO expression hints do not grant response-rewrite or durable emotion authority.
- Durable voice/persona policy remains upstream in approved character/output authority.
- Voice preparation does not write MEM/SOUL/REL/SCN/CTX/SLP state.
- Default diagnostics are content-free and exclude text, internal candidates, credentials, and audio.
- Adapter/TTS failure cannot restore raw unsafe content or trigger memory-family fallback.
- Cancellation/interruption requires an explicit owning runtime/adapter authority.
- Latency optimization never overrides output/privacy/safety boundaries.
- Current implementation status is interpreted through Project Status and current gates, not inferred from metadata readiness.

## Non-goals

This architecture does not define:

- exact SSE frame schemas or parser implementation;
- exact internal sentinel literals;
- exact TTS hint/handoff/transport object schemas;
- exact segmentation punctuation tables or length thresholds;
- concrete TTS provider selection or credentials;
- audio codec/device/queue implementation;
- avatar/Live2D engine implementation;
- lip-sync algorithms;
- ASR or microphone capture;
- response semantic generation;
- scene, relationship, intent, memory, or context authority;
- runtime checkpoint/recovery details;
- durable adapter telemetry retention;
- repository-level implementation sequencing.

## Related architecture

- [RelayLM Pipeline Responsibilities](../pipeline-responsibilities.md)
- [Request / Response Pipeline](../runtime/request-response-pipeline.md)
- [Phase 5.5 Stream Unpack Bounded Slice](../phase5_5_stream_unpack_bounded_slice.md)
- [Phase 5.5-C1 TTS Adapter Handoff Contract](../phase55c1_tts_adapter_handoff_contract.md)
- [Phase 5.5-C3 TTS Adapter Transport Contract](../phase55c3_tts_adapter_transport_contract.md)
- [RelayEMO Affect Modulation](../emotion/affect-modulation.md)
- [Open-LLM-VTuber Integration](../open_llm_vtuber_integration.md)
