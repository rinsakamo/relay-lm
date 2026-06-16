# RelayEMO MVP Initial Design

## Purpose

RelayEMO provides bounded request/session-local affect estimation and expression state for RelayLM.

It does not claim to know the user's true emotion and does not own scene classification, intent routing, memory, persona mutation, persistence, TTS execution, or avatar execution.

```text
Input-side RelayEMO
  affect estimate + expression pressure

Return-side RelayEMO
  bounded display / TTS / avatar hints after safe visible output exists
```

## Responsibility boundary

RelayEMO may:

- estimate affect from current text with uncertainty,
- maintain a bounded session-local `assistant_emotion_state`,
- emit expression/intensity hints,
- obey RelaySCN safety/formality/expression gates,
- emit low-authority scene evidence hints when relevant.

RelayEMO must not:

- create or update `scene_state`,
- decide task/intent/clarification,
- write RelayMEM or RelaySOUL,
- persist raw affect inference as a user fact,
- alter structured/protected output,
- call TTS/Live2D engines,
- place content-bearing affect artifacts in generic trace records.

## Runtime-private affect artifact

A request-local artifact may contain semantic affect content:

```yaml
relayemo_affect_runtime:
  schema_version: relayemo.affect_runtime.v1
  is_estimate: true
  source: heuristic
  affect_class: light_positive_estimate
  valence: 0.42
  arousal: 0.18
  dominance: 0.05
  intensity: 0.25
  confidence: 0.68
  scene_evidence_hint:
    affect_pressure_present: true
    safety_escalation_candidate: false
```

This artifact is content-bearing. It remains request-local or process/session-local under an explicit protected state policy.

Do not emit a `scene_state_candidate`. RelaySCN alone owns normalized scene state and policy. RelayEMO may provide only bounded evidence hints.

## Content-free EMO projection

Default trace/audit surfaces receive only a typed allowlisted projection:

```yaml
relayemo_projection:
  schema_version: relayemo.projection.v1
  affect_estimate_present: true
  source_class: heuristic
  confidence_band: medium
  intensity_band: low
  expression_state_class: warm
  expression_gate: allowed
  text_adjustment_applied: false
  display_marker_applied: false
  tts_hint_emitted: false
  avatar_hint_emitted: false
  persisted_user_affect: false
  applied_to_soul: false
  applied_to_mem: false
```

Default projections must not contain:

- user text,
- semantic affect labels tied to a person when not needed operationally,
- numeric VAD vectors when they could be identifying/sensitive,
- candidate bodies,
- visible response text,
- display/TTS/caption text,
- session-local state values.

Use bands, booleans, counts, source classes, and stable reason IDs.

## `user_affect_estimate`

Rules:

- always mark as estimate,
- preserve uncertainty/confidence,
- default toward neutral/unknown when confidence is low,
- avoid sensitive-attribute or mental-state diagnosis,
- use only current validated evidence allowed by policy,
- do not persist as a durable user fact,
- do not allow one estimate to trigger persona/relationship updates.

A lightweight heuristic may be the initial active path. Structured LLM probing remains optional, default-off, and dry-run until a separate apply policy exists.

## Structured affect probe

A structured probe may run only when configured with:

- dedicated backend/route or an internal-recursion guard,
- strict input/output size limits,
- timeout and busy-skip policy,
- finite-number validation,
- fail-closed candidate handling.

Conceptual candidate:

```yaml
relayemo_affect_candidate:
  schema_version: relayemo.affect_candidate.v1
  user_affect_estimate_candidate:
    valence: 0.2
    arousal: 0.1
    dominance: 0.0
    intensity: 0.2
    confidence: 0.55
  scene_evidence_hint:
    affect_pressure_present: true
    recovery_escalation_candidate: false
```

Requirements:

- nested objects must be objects,
- required numeric fields must be finite numbers,
- invalid/timeout/parse failure does not stop the main response,
- dry-run candidate does not replace the active heuristic state,
- no candidate content enters generic trace output.

## `assistant_emotion_state`

This is an expression-control state, not a claim about consciousness or a durable persona trait.

Conceptual shape:

```yaml
assistant_emotion_state:
  schema_version: relayemo.assistant_expression_state.v1
  state_class: warm
  intensity: 0.28
  confidence: 0.64
  max_delta_per_turn: 0.20
  decay_per_turn: 0.05
  stability: 0.70
```

Rules:

- update slowly and bound per-turn delta,
- use decay-only behavior when classification is unavailable/low-confidence,
- session-local reuse requires a resolved session ID,
- without session ID, use stateless/fail-safe initialization,
- keep process/session-local by default,
- do not persist into RelayMEM/SOUL,
- RelaySCN policy may suppress or clamp expression.

## Scene evidence hint

RelayEMO may tell RelaySCN only that affect-related evidence exists or that a safety/recovery escalation deserves consideration.

```yaml
scene_evidence_hint:
  affect_pressure_present: true
  formality_mismatch_candidate: false
  safety_escalation_candidate: false
  recovery_escalation_candidate: false
```

RelaySCN independently decides the scene type, safety sensitivity, recovery state, and policy.

## Display marker

Display markers are optional, default-off, and separate from semantic text.

Modes:

```text
diagnostics_only
preview
apply
```

Suggested scene posture:

- casual chat / VTuber roleplay / design talk: potentially allowed,
- implementation work: preview or very light,
- review / formal document / medical or safety / recovery: suppressed,
- unknown or low confidence: suppressed.

Do not replace terminal punctuation.

```yaml
display_marker_hint:
  marker: "✨"
  position: after_terminal_punctuation
  tts_policy: omit
```

The display renderer may append the marker while preserving `。`, `！`, `？`, or other punctuation. TTS text should normally omit purely visual markers.

## Return-side expression hints

Return-side RelayEMO may emit engine-neutral hints only after RelayCTX Unpack/segmentation and RelayREF observation.

```yaml
return_expression_hints:
  style_class: gentle
  expression_intensity: 0.30
  display_marker: null
  tts_style_hint: gentle
  tts_emoji_hint: "😊"
  avatar_expression_hint: soft_smile
  avatar_motion_hint: small_nod
```

External adapters map these classes to engine-specific settings after Output-side RelaySCN / RelayRUN approve the current output.

## Durable voice boundary

Approved `OUTPUT_POLICY.md` plus the Main LLM owns the ordinary durable character voice.

RelayEMO should prefer hints and intensity modulation rather than post-generation persona rewriting. Text changes are optional/default-off and limited to meaning-preserving safe conversational surface adjustments.

## Failure behavior

- Affect-probe failure keeps the safe heuristic/neutral path.
- Return-side EMO failure preserves approved visible text without hints.
- No failure path writes MEM/SOUL or changes scene state directly.
- Only content-free failure/suppression reasons enter generic diagnostics.

## Non-goals

- No durable user-affect persistence.
- No RelaySCN state generation.
- No SOUL/MEM/relationship update.
- No feedback-learning apply.
- No direct Irodori-TTS or Live2D runtime control.
- No meaning-changing post-generation rewrite.
- No content-bearing affect candidate in ordinary trace JSONL.

## Summary

```text
current text + SCN policy
  -> bounded affect estimate
  -> session-local expression state
  -> content-free operational projection

safe visible output
  -> bounded expression hints
  -> SCN/RUN gate
  -> external adapters
```
