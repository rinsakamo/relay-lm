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
  "context": [
    {
      "content": "...",
      "sources": ["event-id"],
      "actor": "user"
    }
  ],
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

## ContextItem provenance

A Context item carries:

```text
content
sources[]
actor? = user | assistant | other future source role
```

For current Working Context, `sources` identifies the RelayLM-owned source Event and `actor` preserves who authored that Event.

The actor/source metadata is semantically important:

- user-authored Context can support what the user actually said, subject to temporal and semantic scope;
- assistant-authored Context may support dialogue continuity, reference resolution, and unfinished conversational structure;
- assistant-authored Context does not independently establish user facts, preferences, goals, experiences, or external truth;
- inclusion in Context never upgrades the authority of the underlying source.

Context compilation is read/select/project only. `ContextItem` is not a memory mutation or State acceptance mechanism.

## Working Context

The current runtime may include bounded RelayLM-owned recent dialogue in `context`.

This Working Context is intentionally different from durable memory:

```text
Event / State / MEMORY
    durable semantic sources

Working Context
    temporary cognitive residency for conversational continuity
```

Material can leave Working Context under budget pressure while remaining durably available in its source layer. Later retrieval may re-admit it.

The current implementation preserves normal prior `user → assistant` exchanges atomically so budget pressure cannot retain an assistant assertion while dropping the user Event that gave the exchange its conversational basis.

## Ordinary turn ordering

The current ordinary-turn runtime uses this semantic order:

```text
load config / Identity / Canonical State
        ↓
persist Current User Event
        ↓
compile CognitiveInput
        ↓
exactly one provider generation
        ↓
accept complete valid CognitiveOutput
        ↓
persist Assistant Event from response
        ↓
validate StateCandidate[]
        ↓
persist Canonical State only if validation changed it
```

Persisting the User Event before provider execution is intentional: the Event Journal records that the user input occurred even if cognition later fails.

Buffered and streamed delivery share this semantic ordering. A streaming adapter may expose safely decoded response characters while the single provider generation is still producing its structured wire object, but this early display is not a semantic `CognitiveOutput` acceptance point. Assistant Event creation and StateCandidate validation wait for the complete valid cognitive result.

## CognitiveOutput

```json
{
  "response": "...",
  "state_candidates": []
}
```

`response` is user-visible natural language. `state_candidates` are non-authoritative proposals.

The return path is deliberately symmetric with the input path:

```text
CognitiveOutput
  ├─ response
  │    ↓
  │  Assistant Event
  │    ↓
  │  possible future Working Context
  │
  └─ StateCandidate[]
       ↓
     Validator
       ↓
     Canonical State
```

An assistant response therefore remains useful for future conversational continuity without becoming self-certified factual authority.

Streaming does not create a second semantic output form. Provider wire `utterance` deltas are delivery fragments only; the final complete structured provider result is normalized into the same `CognitiveOutput(response, state_candidates)` used by buffered turns.

## Failure semantics

If the cognitive provider fails before producing a valid `CognitiveOutput`:

```text
Current User Event    persisted
Assistant Event       not created
Canonical State       unchanged by that failed turn
```

The persisted unmatched User Event may later participate in bounded Working Context, because it is real user-origin conversational evidence even though the attempted assistant response failed.

For a streamed turn, the same failure rule applies even if a safe prefix of the provider `utterance` was already delivered to the client. A truncated or malformed structured stream does not retroactively turn that visible prefix into an accepted Assistant Event, does not make incomplete candidates authoritative, and does not trigger semantic regeneration. Successful Assistant/State persistence occurs only after complete structured provider output.

If a valid response is produced but one or more StateCandidates are rejected, the valid response still becomes an Assistant Event while rejected candidates do not mutate Canonical State. Response validity and State acceptance are deliberately separate channels.

Adapter-level malformed provider output is fail-closed before a semantic `CognitiveOutput` is accepted.

An ordinary turn targets exactly one cognitive generation. Working Context selection, deterministic validation, persistence, Context compilation, and streamed delivery do not add a second ordinary cognitive LLM call.
