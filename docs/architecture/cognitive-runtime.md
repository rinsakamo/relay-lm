# Cognitive Runtime

An ordinary RelayLM turn uses one semantic language-model generation.

```text
CognitiveInput
      |
      v
replaceable LM
      |
      v
CognitiveOutput
  response
  state_candidates
```

`response` is the user-facing natural-language channel.

`state_candidates` is an internal proposal channel and is never canonical merely because the model emitted it.

Provider-specific structured-output grammar belongs in adapters. Semantic architecture uses `response` regardless of provider wire field names.

No mandatory second semantic LLM call is part of an ordinary turn. Later reflection/crystallization may run out of band and must return through the same validation authority rather than creating a competing memory truth.

## Accepted Continuity Context extension

`docs/architecture/continuity-context.md` freezes an additional proposal channel, `continuity_candidates`, for implementation under #1371.

K1 implements the typed proposal / accepted-item / immutable-container boundary in `relaylm.continuity`. K2 implements deterministic continuity acceptance/lifecycle in `relaylm.continuity_validation`. The current `CognitiveOutput` still does **not** expose `continuity_candidates`; ordinary buffered/streamed return-path wiring remains K3.

The accepted target shape is:

```text
CognitiveOutput
  response
  state_candidates
  continuity_candidates
```

`continuity_candidates` must be produced by the same ordinary semantic generation rather than a mandatory second model call. Like `state_candidates`, they are proposals only. Deterministic continuity validation must accept a candidate before it can become a `ContinuityItem` in Continuity Context.

Provider-specific structured-output grammar may carry the field when K3 lands, but provider adapters do not own referent, unresolved, active-task, acceptance, or lifecycle semantics.
