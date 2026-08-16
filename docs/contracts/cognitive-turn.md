# Cognitive Turn Contract

## CognitiveInput

Minimal semantic shape:

```json
{
  "identity": {"content": "..."},
  "state_classes": {
    "user.preference": "the user's likes, dislikes, and preferences",
    "relationship.state": "current qualities of the relationship"
  },
  "state": [],
  "context": [],
  "input": {
    "event_id": "019c...",
    "actor": "user",
    "content": "..."
  }
}
```

- `identity` is authoritative stable character identity.
- `state` contains selected accepted Canonical State.
- `context` contains RelayLM-prepared cognitive material, not authority-equivalent raw transcript replay.
- `input` is the current governed Event.
- `state_classes` provides bounded semantic definitions and may be rendered through provider/schema metadata without changing semantics.

## CognitiveOutput

```json
{
  "response": "...",
  "state_candidates": []
}
```

`response` is user-visible natural language. `state_candidates` are non-authoritative proposals.

An ordinary turn targets one cognitive generation.
