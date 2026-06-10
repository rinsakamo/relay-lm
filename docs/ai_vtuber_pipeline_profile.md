# AI VTuber Pipeline Profile

## Purpose

This document defines the AI VTuber MVP pipeline profile for RelayLM.

It is a profile-specific companion to:

- `docs/pipeline_responsibility_design.md`
- `docs/pipeline_implementation_plan.md`
- `docs/relayctx_wake_loop_design.md`
- `docs/relayemo_return_side_style_adapter_design.md`

The goal is to keep the core RelayLM responsibility model generic while documenting the VTuber-specific text-to-voice/avatar runtime contract separately.

## Core stance

The initial AI VTuber target is:

```text
text-in / voice-out
```

RelayLM should not treat ASR as an MVP runtime dependency.

Voice input may be delegated to OS, device, browser, or IME speech input so RelayLM still receives text.

RelayLM remains a text, context, memory, and expression proxy. It is not an ASR system, a TTS engine, or a Live2D runtime.

## MVP pipeline profile

```text
Text input
  - chat message
  - UI text input
  - streaming comment
  - OS / device / browser speech input converted to text

  -> RelayRUN request shell
  -> PipelineContext
  -> Input-side RelaySCN
  -> Input-side RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval
  -> RelayCTX Repack
  -> Main LLM streaming response
  -> RelayCTX Stream Unpack
  -> RelayCTX Output Segmenter
  -> RelayREF diagnostics-only observer
  -> Return-side RelayEMO
  -> TTS adapter queue
  -> Avatar adapter
  -> Output-side RelaySCN
  -> RelayRUN final artifact / trace / checkpoint summary
```

The profile prioritizes:

1. Main LLM response generation and `ctx_working_update` / structured summary delta.
2. Small-context RelayCTX Repack.
3. RelayCTX Stream Unpack and sentence/chunk segmentation.
4. Return-side RelayEMO hints for Irodori-TTS and Live2D.
5. TTS queue and avatar adapter output.

## ASR out of scope

ASR is intentionally outside the MVP profile.

Rationale:

- 12GB VRAM should be prioritized for the Main LLM, TTS, and avatar/display path.
- Device-standard speech input can already provide text to RelayLM.
- ASR quality and latency should not block the text-to-character-output MVP.
- Keeping ASR outside the core preserves RelayLM's OpenAI-compatible proxy boundary.

Future ASR adapters may be added, but they should remain optional and should not change the core pipeline contract.

## VRAM budget stance

For a 12GB local AI VTuber target, the recommended initial stance is:

```text
Main LLM:
  - 9B Q4 stable candidate or 12B QAT experimental candidate
  - MTP disabled by default
  - Thinking disabled for low-latency character output
  - context target around 8k-16k via RelayCTX Repack

TTS:
  - Irodori-TTS or a lightweight variant as the primary target
  - sentence/chunk queue instead of full-response blocking

ASR:
  - out of scope for MVP
  - delegated to OS / device / browser speech input when needed

Avatar:
  - adapter-controlled Live2D expression / motion cue handling
```

Peak token throughput should not be prioritized over VRAM headroom, stable streaming, and predictable TTS latency.

## Adapter boundary contract

### Return-side RelayEMO output

Return-side RelayEMO may emit output hints such as:

```json
{
  "tts_style_hint": "gentle",
  "tts_emoji_hint": "😊",
  "avatar_expression_hint": "soft_smile",
  "avatar_motion_hint": "small_nod",
  "caption_hint": "normal",
  "expression_intensity": 0.35
}
```

Return-side RelayEMO must not:

- directly control the TTS engine,
- directly control the avatar runtime,
- mutate the semantic meaning of the Main LLM answer,
- contaminate `ctx_working_update`,
- require a second Main LLM call during streaming.

### TTS adapter

The TTS adapter consumes TTS-safe chunks and optional style hints.

Conceptual contract:

```text
TTSAdapterInput:
  chunk_id: string
  text: string
  tts_policy: speak | skip | caption_only | substitute
  style_hint: string | null
  emoji_hint: string | null
  caption_text: string | null
```

The adapter may use Irodori-TTS, a lightweight variant, or another compatible engine.

RelayLM core should not depend on engine-specific APIs.

### Avatar adapter

The avatar adapter consumes expression and motion hints.

Conceptual contract:

```text
AvatarAdapterInput:
  chunk_id: string
  expression_hint: string | null
  motion_hint: string | null
  intensity: float | null
  timing_hint: before_audio | during_audio | after_audio | none
```

RelayLM core should emit hints only. Runtime-specific Live2D expression names or motion files should be mapped by the adapter.

## RelayCTX Stream Unpack

The initial implementation order should still start with non-streaming minimal RelayCTX Unpack.

After minimal Unpack is stable, this profile extends it into:

```text
minimal RelayCTX Unpack
  -> RelayCTX Stream Unpack
  -> RelayCTX Output Segmenter
  -> TTS adapter queue
```

Stream Unpack responsibilities:

- forward user-visible text chunks as early as possible,
- detect and suppress internal markers,
- collect terminal `ctx_working_update` / structured summary delta candidates,
- block malformed internal update candidates without destroying usable visible text,
- record diagnostics for parse failure, marker leakage, and partial stream failure.

MVP fail-safe rule:

```text
If visible text is available, keep it.
If internal update parsing fails, block only the internal update candidate.
```

## Output Segmenter

RelayCTX Output Segmenter turns visible text into TTS-safe output chunks.

Flush boundaries may include:

- Japanese sentence ending `。`
- question / exclamation ending `？` / `！`
- newline
- configured maximum character length
- configured maximum time without flush

The segmenter should classify chunks before they enter the TTS queue.

Conceptual shape:

```text
SegmentedOutputChunk:
  chunk_id: string
  kind: normal_sentence | quoted_text | parenthetical_note | code_block | inline_code | url | json_yaml | table | command_or_file_path | internal_marker
  text: string
  tts_policy: speak | skip | caption_only | substitute
  caption_text: string | null
  replacement_text: string | null
  diagnostics: dict
```

## TTS-safe chunk rules

### normal_sentence

- TTS policy: `speak`
- Return-side EMO may add style and emoji hints.

### quoted_text

- TTS policy: usually `speak`
- Style hint may indicate quoted or reading voice.
- Long formal quotes may be downgraded to `caption_only` by scene policy.

### parenthetical_note

- TTS policy: usually `speak`
- Style hint should reduce emphasis or pitch when supported.

### code_block

- TTS policy: `caption_only`
- Do not send raw code to TTS.
- Optional substitute text may be used, such as `コードを表示したよ`.

### inline_code

- TTS policy: `speak` only when short and pronounceable.
- Long inline code should become `caption_only`.

### url

- TTS policy: usually `caption_only`
- Full URLs should not be read aloud by default.
- Optional substitute text may read only the domain.

### json_yaml

- TTS policy: `caption_only`
- Structured internal-looking content should not be read aloud.
- Internal markers must be blocked, not captioned.

### table

- TTS policy: `caption_only`
- Optional substitute text may summarize that a table was shown.

### command_or_file_path

- TTS policy: usually `caption_only`
- Short command names or file names may be spoken only when useful and scene-appropriate.

## Runtime and failure behavior

### Chunk parse failure

If segmentation fails, RelayLM should either:

- forward the text as a conservative `normal_sentence` chunk when safe, or
- use `caption_only` when the text appears structured or unsafe for speech.

### TTS adapter failure

TTS failure should not invalidate the Main LLM response.

The fallback route should be:

```text
TTS adapter failed
  -> keep caption / text output
  -> record adapter diagnostics
  -> continue runtime when possible
```

### Partial stream failure

If the backend stream fails after visible chunks have already been emitted:

- preserve emitted chunks,
- block incomplete internal update candidates,
- record partial stream diagnostics,
- allow RelayRUN / Output-side SCN to prepare recovery hints for the next turn.

### Internal update parse failure

Malformed `ctx_working_update`, MEM, SOUL, or SLP candidates must be blocked.

Visible text should still be returned when available.

## Implementation phase mapping

This profile does not change the core implementation order.

It adds VTuber-specific contracts to the existing phases:

```text
Phase 2:
  Add this profile and adapter boundary contract.
  Document ASR out-of-scope and Irodori-TTS primary target.

Phase 3:
  Harden CTX Repack for small-context VTuber profile budgets.
  Keep Main LLM responsible for response + ctx_working_update delta.

Phase 5:
  Implement minimal RelayCTX Unpack first.
  Separate visible text from internal/update candidates.

Phase 5.5:
  Add RelayCTX Stream Unpack and Output Segmenter.
  Add TTS-safe chunk classification.

Phase 6:
  Add failure route handling for chunk parse, TTS adapter, partial stream, and internal update parse failures.

Phase 7+:
  Connect REF, Output-side SCN, and RelayRUN diagnostics to stream/chunk/TTS observations.
```

## Future candidates

The following are future or research candidates, not MVP dependencies:

- LFM2.5-Audio-JP as an ASR/TTS or audio-to-audio adapter.
- Speech-to-speech mode.
- Optional small-model RelayINT probe.
- GPU/CPU hybrid ASR.
- More detailed avatar motion planning.

These candidates should remain adapter-level extensions unless a later design explicitly promotes them into the core pipeline.
