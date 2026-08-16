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
