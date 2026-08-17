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

## Continuity Context return path

`docs/architecture/continuity-context.md` owns the Continuity semantics tracked by #1371.

K1 implements the typed proposal / accepted-item / immutable-container boundary in `relaylm.continuity`. K2 implements deterministic continuity acceptance/lifecycle in `relaylm.continuity_validation`. K3 exposes `CognitiveOutput.continuity_candidates` and wires the provider-independent ordinary-turn return path through the same single buffered or streamed cognitive generation.

Buffered execution performs exactly one `provider.generate()` call. Streamed execution performs exactly one `stream_generate()` call. In both paths, the completed `CognitiveOutput` reaches the same Turn commit boundary. No continuity-specific semantic provider call is added.

When an explicit process-local `ContinuityRuntime` is configured, Turn applies K2 exactly once after successful generation and advances the Continuity Context revision even for an empty candidate tuple. Streaming deltas are visible before final structured completion, but the Continuity runtime is not updated until generation has completed and deterministic validation has run.

When continuity proposals are present without an explicit runtime, Turn rejects the output before Assistant Event, State, or Continuity commit rather than silently dropping the proposal channel.

The runtime holder requires an explicit immutable `ContinuityContext` and explicit positive lifetime. It does not define default capacity or lifetime policy and does not persist Continuity Context.

Provider-specific structured-output grammar may expose `continuity_candidates` separately. Adapters do not own referent, unresolved, active-task, provenance, acceptance, or lifecycle semantics.

With K3 present on current `v1`, Context Compiler C2 is unblocked as a separate #1267 transaction and must operate on already-accepted `ContinuityItem` values. C3 remains ordered after C2.
