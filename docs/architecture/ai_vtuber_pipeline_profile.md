# AI VTuber Pipeline Profile

## Purpose

This document defines the optional AI VTuber realtime profile for RelayLM.

It complements:

- [Pipeline Responsibility Design](pipeline_responsibility_design.md),
- [Context Packing Design](context_packing_design.md),
- [RelayEMO Return-side Expression Design](relayemo_return_side_style_adapter_design.md),
- [Project Status](../PROJECT_STATUS.md).

Implementation phase/status is not duplicated here.

## Core stance

The initial profile is:

```text
text-in / voice-and-avatar-out
```

ASR remains outside RelayLM's MVP runtime. OS/device/browser speech input may provide text.

RelayLM owns context, memory, visible/internal output separation, and expression hints. It does not own TTS engine execution or Live2D/avatar execution.

## Canonical realtime pipeline

```text
Text input
  -> RelayRUN request shell
  -> PipelineContext
  -> Input-side RelaySCN
  -> Input-side RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval, when allowed
  -> RelayCTX Repack
  -> Runtime Compile Gate
  -> Main LLM streaming response
  -> RelayCTX Stream Unpack
  -> RelayCTX Output Segmenter
  -> RelayREF
  -> Return-side RelayEMO
  -> Output-side RelaySCN
       current-response gate + next-turn observation
  -> RelayRUN approved output / trace / checkpoint summary
  -> caption/text output
  -> TTS adapter queue
  -> Avatar adapter
```

TTS and Avatar consumers must never receive chunks before internal-marker, REF, current-response SCN, and RelayRUN approval gates complete for that chunk/response.

## Latency posture

Priorities:

1. preserve latest input and safe compatible streaming,
2. produce the first safe speakable chunk quickly,
3. keep retrieval bounded,
4. keep expression hint generation deterministic/lightweight,
5. never trade internal-marker or safety gating for lower latency.

A 12GB local profile should reserve headroom for the Main LLM, TTS, and avatar/display path. Exact model choices are deployment guidance, not architecture ownership.

## Stream Unpack

Responsibilities:

- forward only validated visible text,
- suppress internal markers/candidate envelopes,
- collect supported terminal internal candidates,
- preserve usable visible text when candidate parsing fails,
- record content-free parse/leak/partial-stream projections,
- prevent malformed candidates from reaching TTS/Avatar consumers.

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
- bypass Output-side SCN / RelayRUN gates.

## Output-side RelaySCN split

Output-side RelaySCN has two related roles.

### Current-response gate

May block/suppress current emission for:

- internal leakage,
- empty/invalid output,
- safety-critical mismatch,
- recovery-critical invalid state.

This gate must run before external TTS/Avatar emission.

### Next-turn observation

Normally records next-turn scene/recovery/persistence state without rewriting the current response.

## TTS adapter

Conceptual input:

```yaml
tts_adapter_input:
  chunk_id: chunk_001
  text: "..."
  tts_policy: speak
  style_class: gentle
  emoji_hint: "😊"
  caption_text: "..."
```

The adapter maps engine-neutral hints to Irodori-TTS or another configured engine.

## Avatar adapter

Conceptual input:

```yaml
avatar_adapter_input:
  chunk_id: chunk_001
  expression_class: soft_smile
  motion_class: small_nod
  intensity: 0.35
  timing_hint: during_audio
```

The adapter maps classes to runtime-specific expression/motion names.

## Failure behavior

### Segmentation failure

- use conservative plain text only when safe,
- otherwise caption-only,
- never pass suspected internal/structured content to TTS.

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
- prepare next-turn recovery through SCN/RUN.

## ASR and future audio

ASR, speech-to-speech, audio affect, and alternate audio models remain optional adapter-level extensions unless later architecture explicitly changes ownership.

## Non-goals

This profile does not:

- duplicate phase/status roadmaps,
- depend on archived Wake/Sleep designs,
- make TTS/Avatar part of RelayEMO,
- emit text-bearing chunks into generic trace,
- send output to external consumers before current-response safety gates,
- make ASR a core dependency.
