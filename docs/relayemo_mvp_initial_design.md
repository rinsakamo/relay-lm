# RelayEMO MVP Initial Design

## Purpose

This document distinguishes the **current implemented RelayEMO MVP artifact** from the **target component boundary**.

The current runtime still contains legacy scene and trace fields. The target sections describe the migration direction and must not be read as already-implemented behavior.

## Current implemented behavior

The current runtime helper is `relaylm/relayemo.py`.

### Current heuristic path

The runtime currently:

- extracts the latest user text,
- estimates VAD-like affect values,
- infers a scene type inside RelayEMO,
- updates a process/session-local assistant state,
- optionally builds a structured LLM affect-probe candidate,
- emits one combined runtime artifact.

### Current runtime artifact

The current artifact includes fields equivalent to:

```yaml
relayemo_artifact:
  user_affect_estimate:
    valence: 0.4
    arousal: 0.6
    dominance: 0.2
    intensity: 0.7
    confidence: 0.55
    mode: light_positive_estimate
    evidence_level: light_text_heuristic
    is_estimate: true
  affect_probe_mode: heuristic
  heuristic_user_affect_estimate: "..."
  llm_user_affect_estimate_candidate: null
  llm_scene_state_candidate: null
  llm_affect_probe_meta: "..."
  llm_candidate_applied: false
  assistant_emotion_state: "..."
  scene_state:
    scene_type: casual_chat
  text_marker_preview:
    gate_open: false
    marker: ""
    marker_count: 0
    placement: postfix_replace_punctuation
    applied_to_text: false
    suppression_reason: relayemo_disabled_or_scene_gate
  text_marker_apply:
    applied_to_text: false
    applied_to_soul: false
    applied_to_mem: false
    applied_to_tts: false
    persisted_user_affect: false
  user_affect_estimate_is_estimate: true
```

This is the current compatibility shape. It is broader than the target ownership and projection model.

### Current structured affect probe

The current probe prompt/parser expects:

```text
user_affect_estimate_candidate
scene_state_candidate
classifier_meta
```

The parser validates a `scene_type` and scene confidence in addition to affect fields. Synthetic dry-run output also includes `scene_state_candidate`.

### Current session state

The current implementation keeps assistant state in an in-process TTL-bounded dictionary keyed by session key when available.

This is runtime-local state and is not RelayMEM or RelaySOUL persistence.

## Target responsibility boundary

RelayEMO should provide bounded request/session-local affect estimation and expression state.

```text
Input-side RelayEMO
  affect estimate + expression pressure

Return-side RelayEMO
  bounded display / TTS / avatar hints after safe visible output exists
```

Target RelayEMO does not own:

- normalized scene classification or `scene_state`,
- task/intent/clarification decisions,
- RelayMEM or RelaySOUL writes,
- durable user-affect facts,
- TTS or avatar execution,
- meaning-changing output rewrite.

## Target migration from current artifact

The current compatibility fields should be migrated as follows:

```text
infer_scene_type / scene_state
  -> RelaySCN input-side classification

llm_scene_state_candidate
  -> bounded scene_evidence_hint only

full VAD and assistant state in generic trace
  -> runtime-private artifact
  -> typed content-free EMO projection for trace/audit

postfix_replace_punctuation
  -> preserve terminal punctuation
  -> separate display_marker_hint with TTS omission policy
```

This migration requires implementation and smoke-test changes; this docs-only PR does not perform it.

## Target runtime-private affect artifact

A future request-local artifact may contain semantic affect content:

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

This artifact is content-bearing and remains request-local or process/session-local under an explicit protected state policy.

RelayEMO may provide only low-authority scene evidence hints. RelaySCN alone creates normalized scene state and policy.

## Target content-free EMO projection

Default trace/audit should receive a typed allowlisted projection:

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

The target projection must not contain:

- user text,
- numeric VAD vectors,
- semantic affect candidate bodies,
- scene candidate bodies,
- visible response text,
- display/TTS/caption text,
- session-local assistant-state values.

Use bands, booleans, counts, source classes, and stable reason IDs.

## Affect-estimate rules

Both current and target behavior should preserve these invariants:

- always mark the result as an estimate,
- preserve uncertainty/confidence,
- default toward neutral/unknown when confidence is low,
- avoid sensitive-attribute or mental-state diagnosis,
- use only validated evidence allowed by policy,
- do not persist as a durable user fact,
- do not allow one estimate to trigger persona/relationship updates.

## Target structured affect probe

A future probe should return affect candidates and bounded scene evidence rather than normalized scene state:

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

Required target behavior:

- dedicated backend/route or recursion guard,
- strict input/output limits,
- timeout and busy-skip policy,
- finite-number validation,
- invalid candidate does not stop the main response,
- dry-run candidate does not replace the active state,
- candidate content does not enter generic trace output.

## Assistant expression state

The assistant state is expression control, not a claim about consciousness or a durable persona trait.

```yaml
assistant_expression_state:
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
- use decay-only behavior for low-confidence input,
- session-local reuse requires a resolved session ID,
- without session ID, use stateless/fail-safe initialization,
- keep process/session-local by default,
- do not persist into RelayMEM/SOUL,
- allow RelaySCN to suppress or clamp expression.

## Display marker target

Display markers are optional, default-off, and separate from semantic text.

```yaml
display_marker_hint:
  marker: "✨"
  position: after_terminal_punctuation
  tts_policy: omit
```

Target behavior preserves `。`, `！`, `？`, and other punctuation. TTS text normally omits purely visual markers.

The current `postfix_replace_punctuation` compatibility field remains an implementation gap until the marker path is migrated.

## Return-side expression hints

Return-side RelayEMO may emit engine-neutral hints only after RelayCTX Unpack/segmentation and RelayREF observation:

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

External adapters map these classes after the current-response safety gate and RelayRUN emission decision.

## Durable voice boundary

Approved `OUTPUT_POLICY.md` plus the Main LLM owns ordinary durable character voice.

RelayEMO should prefer hints and intensity modulation. Text changes remain optional/default-off and limited to meaning-preserving safe conversational surface adjustments.

## Required implementation follow-up

A future implementation PR should:

1. remove scene classification ownership from `relaylm/relayemo.py`,
2. replace `scene_state_candidate` with typed `scene_evidence_hint`,
3. create a typed content-free EMO projection,
4. prevent the full current artifact from entering generic trace surfaces,
5. migrate marker placement away from punctuation replacement,
6. update examples and RelayEMO smoke tests.

## Failure behavior

- affect-probe failure keeps the safe heuristic/neutral path,
- Return-side EMO failure preserves approved visible text without hints,
- no failure path writes MEM/SOUL,
- only content-free failure/suppression reasons should enter generic diagnostics after projection migration.

## Non-goals

- no claim that target v1 artifacts are currently implemented,
- no durable user-affect persistence,
- no final RelaySCN state ownership,
- no SOUL/MEM/relationship update,
- no direct TTS/Live2D control,
- no meaning-changing rewrite,
- no content-bearing affect candidate in the target generic trace.
