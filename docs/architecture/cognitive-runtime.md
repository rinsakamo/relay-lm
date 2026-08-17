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
  continuity_candidates
```

`response` is the user-facing natural-language channel.

`state_candidates` is an internal proposal channel and is never canonical merely because the model emitted it.

`continuity_candidates` is an internal proposal channel for bounded non-durable continuity and is never accepted temporary authority merely because the model emitted it.

Provider-specific structured-output grammar belongs in adapters. Semantic architecture uses `response`, `state_candidates`, and `continuity_candidates` independently of provider wire field names.

No mandatory second semantic LLM call is part of an ordinary turn. Later reflection/crystallization may run out of band and must return through the relevant validation authority rather than creating a competing truth source.

## Continuity Context ordinary-turn path

`docs/architecture/continuity-context.md` owns Continuity semantics. `relaylm.continuity` owns the typed proposal / accepted-item / immutable-container boundary, and `relaylm.continuity_validation` owns deterministic acceptance and lifecycle. Turn/Runtime only coordinates those owners with the Context Compiler and the existing single cognitive generation.

When an explicit process-local `ContinuityRuntime` is configured, ordinary-turn preparation snapshots its current immutable `ContinuityContext` before provider generation and passes that accepted context to the Context Compiler. The compiler remains the owner of current cognitive projection: Turn does not inspect Continuity kinds, reconstruct referent/unresolved/active-task meaning, or decide which accepted items belong in `CognitiveInput`.

Current Context Compiler authority can project already-accepted `referent`, `unresolved`, and `active_task` Continuity while preserving accepted ordering, Event sources, and epistemic role. Those selection/projection semantics are compiler-owned; the runtime only supplies the accepted pre-turn context.

Buffered execution performs exactly one `provider.generate()` call. Streamed execution performs exactly one `stream_generate()` call. In both paths, the provider sees the pre-turn accepted Continuity projection before the completed `CognitiveOutput` reaches the common Turn commit boundary. No continuity-specific semantic provider call is added.

After successful generation, Turn applies deterministic Continuity validation exactly once when a runtime is configured and replaces the runtime's context pointer with the resulting immutable context. This happens even for an empty candidate tuple so revision-based expiry advances deterministically. Streaming deltas may be visible before final structured completion, but neither accepted Continuity nor its revision changes during delta emission.

When no Continuity runtime is configured, ordinary-turn preparation supplies no accepted Continuity Context to the compiler. If the completed output nevertheless contains non-empty continuity proposals, Turn rejects that output before Assistant Event, State, or Continuity commit rather than silently dropping the proposal channel.

The runtime holder requires an explicit immutable `ContinuityContext` and explicit positive lifetime. It does not define default capacity or lifetime policy and does not persist Continuity Context.

Provider-specific structured-output grammar may expose `continuity_candidates` separately. Adapters do not own referent, unresolved, active-task, provenance, acceptance, lifecycle, or Context Compiler projection semantics.
