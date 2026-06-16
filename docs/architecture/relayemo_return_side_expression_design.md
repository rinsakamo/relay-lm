# RelayEMO Return-side Expression Design

## Purpose

Return-side RelayEMO applies bounded transient expression after RelayCTX has separated visible output from internal candidates and after RelayREF has produced output observations.

It does not create the character's durable voice. Durable character wording, tone, response shape, and memory-disclosure behavior are primarily conditioned by approved `OUTPUT_POLICY.md` and rendered by the Main LLM.

```text
approved OUTPUT_POLICY + Main LLM
  durable character voice and semantic answer

Return-side RelayEMO
  transient affect expression and engine-neutral hints
```

## Canonical position

```text
Main LLM
  -> RelayCTX Unpack / Stream Unpack
  -> Output Segmenter
  -> RelayREF
  -> Return-side RelayEMO
  -> Output-side RelaySCN current-response gate / next-turn observation
  -> RelayRUN approved output
  -> external TTS / Avatar adapters / captions
```

Return-side RelayEMO must not send output directly to a TTS engine or avatar runtime before Output-side RelaySCN and RelayRUN approve the current response.

## Inputs

Return-side RelayEMO may consume:

- validated visible output segments,
- protected-segment classification,
- approved durable `OUTPUT_POLICY.md`,
- RelaySCN expression/formality/safety policy,
- request/session-local `assistant_emotion_state`,
- RelayREF content-free observations,
- TTS/avatar profile capabilities.

It must not consume raw internal candidate bodies as style input.

## Ownership boundary

### Main LLM and durable output policy

Own:

- semantic answer,
- persona-consistent wording,
- durable character voice,
- ordinary tone and response shape,
- clarification wording,
- factual/code/structured content.

### RelayCTX Output Segmenter

Owns:

- visible chunk boundaries,
- protected-segment classification,
- `speak` / `skip` / `caption_only` / `substitute` policy,
- internal-marker blocking,
- separation of display text, TTS text, and optional substitute text.

### RelayREF

Owns post-generation observations such as empty/invalid output, marker leakage, and likely scene/policy mismatch. It does not rewrite output.

### Return-side RelayEMO

May:

- select bounded expression intensity,
- emit visual marker hints,
- emit TTS prosody/style hints,
- emit avatar expression/motion hints,
- apply narrowly-scoped surface adjustments to safe conversational segments when explicitly allowed.

Must not:

- alter facts, reasoning, instructions, code, commands, quoted text, structured data, or safety meaning,
- reconstruct the whole answer in a different persona voice,
- override Output Segmenter TTS safety policy,
- override RelaySCN formality/safety/recovery suppression,
- modify internal candidates,
- persist affect or relationship state,
- control TTS/Live2D engines directly.

Meaning-changing repair is handled through REF / SCN / RUN policy, not hidden inside EMO.

## Safe segment classes

Only validated conversational segments are eligible for text-surface adjustment by default.

Protected classes include:

- quoted text,
- inline/fenced code,
- commands and file paths,
- JSON/YAML and tables,
- URLs,
- formal-document passages,
- medical/safety passages,
- strict implementation/review output,
- internal markers or candidate envelopes.

For protected segments, RelayEMO may still emit an external delivery hint only when the segmenter's policy permits it.

## Durable voice versus transient expression

Examples of durable `OUTPUT_POLICY.md` concerns:

- usually warm but technically precise,
- concise acknowledgement before analysis,
- characteristic first-person/ending style,
- typical verbosity and structure,
- memory-disclosure restraint.

Examples of transient RelayEMO concerns:

- slightly softer delivery for a worried user,
- reduced intensity in formal/recovery scenes,
- short visual marker on an informal positive response,
- TTS prosody hint such as gentle/playful/low-energy,
- avatar smile/nod hint.

Return-side RelayEMO should prefer hints over text mutation.

## Expression state

Use terms such as:

```text
expression_state
expression_intensity
affect_intensity
style_intensity
```

Do not call this EMO `temperature`, because it is distinct from OpenAI sampling `temperature`.

Conceptual state:

```yaml
expression_state:
  class: warm
  intensity: 0.30
  confidence_band: medium
  text_adjustment_allowed: false
  visual_marker_allowed: true
  tts_hint_allowed: true
  avatar_hint_allowed: true
```

## Text adjustment

Text adjustment is optional, default-off, and narrower than general style rewriting.

Allowed examples when all gates pass:

- preserving punctuation while appending a bounded display marker,
- selecting among pre-approved equivalent short interjections,
- minor punctuation/emphasis adjustment that does not change meaning.

Disallowed:

- systematic suffix replacement across every sentence,
- converting formal/technical prose into colloquial character speech after generation,
- changing certainty, negation, urgency, instruction steps, or quoted wording,
- changing TTS text without a separately defined display/TTS split.

Durable suffix or character phrase behavior should be expressed in `OUTPUT_POLICY.md` and generated by the Main LLM. RelayEMO may only modulate its transient intensity.

## Marker boundary

Visual markers should be separate from semantic text when possible.

```yaml
expression_output:
  display_marker: "✨"
  marker_position: after_terminal_punctuation
  tts_marker_policy: omit
```

Do not replace terminal punctuation with an emoji/marker. Preserve punctuation for captions, text integrity, and TTS segmentation.

## TTS hint projection

Return-side RelayEMO emits engine-neutral hints:

```yaml
tts_expression_hint:
  style_class: gentle
  intensity: 0.35
  emoji_hint: "😊"
  timing_hint: chunk
```

This is not an Irodori-TTS adapter and contains no engine call. The external TTS adapter maps supported fields to the configured engine.

## Avatar hint projection

```yaml
avatar_expression_hint:
  expression_class: soft_smile
  motion_class: small_nod
  intensity: 0.35
  timing_hint: during_audio
```

This is not a Live2D adapter. Runtime-specific expression/motion names are mapped externally.

## Recovery and deferred-state boundary

RelayREF and RelaySLP do not directly create sleep/reflect/resume expressions or user-visible text.

```text
REF observation / SLP outcome
  -> Output-side RelaySCN or next-turn RelaySCN policy
  -> RelayRUN recovery/waiting-user route
  -> normal visible-output generation
  -> Return-side RelayEMO bounded hints
```

Formal component contracts should use:

- deferred RelaySLP,
- recovery,
- waiting-user,
- reanchor,
- normal-turn continuation.

Product-facing metaphors may be rendered only after the semantic recovery route has been approved.

## Runtime-private artifact versus content-free projection

### Runtime-private expression artifact

May contain request-local expression labels, segment-level hints, display markers, and adapter hint values.

### Default diagnostic projection

May contain only:

- expression state/intensity bands,
- segment counts,
- marker/text/TTS/avatar hint applied booleans,
- suppressed reason IDs,
- protected-segment counts,
- output gate status.

It must not contain visible response text, rewritten segment text, user affect labels/text, TTS caption bodies, or avatar implementation names when those are sensitive configuration values.

## Scene suppression

Text adjustment and expressive hints should be reduced or suppressed for:

- formal documents,
- review and strict implementation work,
- medical/safety content,
- recovery/waiting-user states,
- exact commands/instructions,
- structured data,
- low-confidence affect estimates,
- current-response block states.

## Failure behavior

- EMO failure does not invalidate an otherwise approved semantic response.
- On failure, preserve approved visible/caption text without expression hints.
- Never fall back to changing protected text.
- Record only a content-free failed/suppressed projection.

## Summary

```text
Main LLM + OUTPUT_POLICY
  -> durable persona-consistent answer

RelayCTX / REF
  -> safe visible segments and observations

Return-side RelayEMO
  -> bounded transient expression hints

SCN / RUN
  -> approve current output

external adapters
  -> TTS / Avatar execution
```
