# AI VTuber Pipeline Profile

## Purpose

This document defines the optional AI VTuber realtime profile for RelayLM.

It complements:

- [Pipeline Responsibility Design](pipeline_responsibility_design.md),
- [Context Packing Design](context_packing_design.md),
- [RelayEMO Return-side Expression Design](relayemo_return_side_expression_design.md),
- [Project Status](../PROJECT_STATUS.md).

Implementation phase/status is not duplicated here.

## Core stance

The initial profile is:

```text
text-in / voice-and-avatar-out
```

ASR remains outside RelayLM's MVP runtime. OS/device/browser speech input may provide text.

RelayLM owns relationship-conditioned context, scene policy, memory, visible/internal output separation, and engine-neutral expression hints. It does not own TTS engine execution or Live2D/avatar execution.

## Request and generation path

```text
Text input
  -> RelayRUN request shell
  -> PipelineContext
  -> RelayREL
  -> Input-side RelaySCN
  -> Input-side RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval, when allowed
  -> RelayCTX Repack
  -> Runtime Compile Gate
  -> Main LLM streaming response
```

After streaming starts, RelayLM uses two timing domains:

1. per-chunk validation and emission,
2. end-of-turn aggregation and next-turn state.

Do not place end-of-turn work on the critical path for the first safe TTS chunk.

## Per-chunk emission path

```text
backend stream delta
  -> RelayCTX Stream Unpack
  -> RelayCTX Output Segmenter
  -> chunk-level RelayREF observation
  -> Return-side RelayEMO hints
  -> current-response safety gate
       internal leakage / invalid chunk / safety-critical mismatch
  -> RelayRUN chunk emission decision
  -> caption/text output
  -> TTS adapter queue
  -> Avatar adapter
```

Every externally emitted chunk must pass the current-response gate and RelayRUN emission decision first.

Chunk-level processing must not wait for:

- next-turn scene classification,
- full-response summary,
- final checkpoint/index update,
- deferred RelaySLP work.

## End-of-turn finalization path

```text
stream complete / terminal event
  -> response-level RelayREF aggregation
  -> Output-side RelaySCN next-turn observation
  -> RelayRUN final artifact / checkpoint summary
  -> persistence-block and recovery-transition summaries
  -> optional deferred RelaySLP scheduling
```

End-of-turn finalization must not replay already emitted chunks.

## Output-side RelaySCN split

Output-side RelaySCN has two timing-specific responsibilities.

### Current-response safety gate

This gate is used before each external emission and may block/suppress a chunk for:

- internal marker/candidate leakage,
- empty or malformed visible content,
- safety-critical mismatch,
- recovery-critical invalid state.

It must remain lightweight enough for streaming.

### Next-turn observation

This runs after the response is complete and normally records:

- next scene candidate,
- recovery/context-repair state,
- persistence block reasons,
- user-confirmation requirement,
- next-turn expression/memory policy.

It does not retroactively rewrite or delay already approved chunks.

## Latency posture

Priorities:

1. preserve latest input and compatible streaming,
2. produce the first safe speakable chunk quickly,
3. keep current-response gates lightweight and fail-closed,
4. keep retrieval bounded,
5. keep expression hint generation deterministic/lightweight,
6. defer response-level observation and persistence work until turn end.

A 12GB local profile should reserve headroom for Main LLM, TTS, and avatar/display paths. Exact model choices are deployment guidance, not architecture ownership.

## Stream Unpack

Responsibilities:

- forward only validated visible text,
- suppress internal markers/candidate envelopes,
- collect supported terminal internal candidates,
- preserve usable visible text when candidate parsing fails,
- record content-free parse/leak/partial-stream projections,
- prevent malformed candidates from reaching external consumers.

```text
visible text valid + internal candidate invalid
  -> preserve visible text
  -> block candidate
```

## Output Segmenter

The segmenter creates runtime-private TTS-safe chunks.

```yaml
segmented_output_chunk:
  chunk_id: chunk_001
  kind: normal_sentence
  display_text: "..."
  tts_text: "..."
  tts_policy: speak
  caption_text: "..."
  replacement_text: null
  protected: false
```

This artifact is content-bearing and request-local.

Possible kinds:

```text
normal_sentence
quoted_text
parenthetical_note
code_block
inline_code
url
json_yaml
table
command_or_file_path
internal_marker
```

Flush boundaries may include Japanese/Latin sentence endings, newline, maximum character count, or maximum pending time.

## TTS policy

```text
normal_sentence       -> speak
quoted_text           -> speak or caption_only by policy
parenthetical_note    -> speak with reduced emphasis when supported
code_block            -> caption_only or substitute
inline_code           -> short/pronounceable only
url                    -> caption_only or domain substitute
json_yaml              -> caption_only
table                 -> caption_only or summary substitute
command_or_file_path   -> caption_only unless explicitly useful
internal_marker        -> blocked
```

When uncertain, prefer `caption_only` over noisy or unsafe speech.

Return-side RelayEMO cannot override the segmenter's TTS safety policy.

## Content-free chunk projection

Default trace/audit receives no text bodies.

```yaml
segmented_chunk_projection:
  schema_version: relayctx.segmented_chunk_projection.v1
  chunk_id: chunk_001
  kind: normal_sentence
  char_count: 32
  tts_policy: speak
  protected: false
  internal_marker_detected: false
  emission_decision: emitted
  emitted_to_caption: true
  emitted_to_tts: true
  emitted_to_avatar: true
  blocked_reason_ids: []
  content_free: true
```

Do not include `display_text`, `tts_text`, `caption_text`, `replacement_text`, or visible response text in generic trace records.

## Return-side RelayEMO output

RelayEMO emits engine-neutral hints only:

```yaml
return_expression_hints:
  style_class: gentle
  tts_emoji_hint: "😊"
  avatar_expression_class: soft_smile
  avatar_motion_class: small_nod
  expression_intensity: 0.35
```

It does not:

- control TTS or Live2D directly,
- alter semantic meaning,
- rewrite protected segments,
- override segmenter policy,
- bypass the current-response safety gate or RelayRUN emission decision.

## TTS adapter

Conceptual per-chunk input:

```yaml
tts_adapter_input:
  chunk_id: chunk_001
  text: "..."
  tts_policy: speak
  style_class: gentle
  emoji_hint: "😊"
  caption_text: "..."
```

The external adapter maps engine-neutral hints to Irodori-TTS or another configured engine.

## Avatar adapter

Conceptual per-chunk input:

```yaml
avatar_adapter_input:
  chunk_id: chunk_001
  expression_class: soft_smile
  motion_class: small_nod
  intensity: 0.35
  timing_hint: during_audio
```

The adapter maps classes to runtime-specific expression/motion names.

## Streaming state and idempotency

RelayRUN should track at least:

- emitted chunk IDs,
- pending chunk state,
- stream completion/abort state,
- current-response block state,
- terminal candidate state,
- finalization status.

Recovery/resume must not enqueue the same TTS or avatar chunk twice.

## Failure behavior

### Segmentation failure

- use conservative plain text only when safe,
- otherwise use caption-only,
- never pass suspected internal/structured content to TTS.

### Chunk safety-gate failure

- block the affected external emission,
- retain content-free reason IDs,
- escalate to response-level recovery when required.

### TTS failure

```text
TTS failure
  -> keep caption/text output
  -> record content-free adapter failure
  -> continue when safe
```

### Avatar failure

- preserve text/TTS output,
- omit motion/expression,
- record content-free adapter failure.

### Partial stream failure

- preserve already approved/emitted chunks,
- block incomplete internal candidates,
- prevent duplicate replay on recovery,
- finalize response-level REF/SCN/RUN state once the abort is known.

## ASR and future audio

ASR, speech-to-speech, audio affect, and alternate audio models remain optional adapter-level extensions unless later architecture explicitly changes ownership.

## Current implementation status

This document defines the target realtime timing contract. Stream Unpack, chunk-level gates, response-level aggregation, and external adapter integration may remain partially implemented or future work; current status belongs in [Project Status](../PROJECT_STATUS.md).

## Non-goals

This profile does not:

- duplicate phase/status roadmaps,
- depend on archived Wake/Sleep designs,
- make TTS/Avatar part of RelayEMO,
- emit text-bearing chunks into generic trace,
- make next-turn observation block the first safe TTS chunk,
- send output to external consumers before per-chunk safety approval,
- make ASR a core dependency.
