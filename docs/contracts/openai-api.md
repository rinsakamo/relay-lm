# OpenAI-Compatible API Boundary

RelayLM exposes an OpenAI-compatible client boundary without treating client-supplied history as character authority.

## Direction

```text
client / AITuber UI
        |
        v
POST /v1/chat/completions
        |
        v
RelayLM turn
        |
        v
configured cognitive provider
```

The client-facing `model` field is a compatibility field. It does not select or override RelayLM's configured cognitive provider/model.

## MVP request authority

For M3, RelayLM selects only the last non-empty `user` message as the current governed input.

Earlier client-supplied `system`, `assistant`, and `user` messages are not replayed into Cognitive Context and are not appended into the Event Journal merely because the client sent them. Character continuity comes from `SOUL.md`, Canonical State, and RelayLM-governed Context.

This prevents unsupported prior assistant statements or arbitrary client system prompts from overriding character Identity or becoming self-reinforcing memory.

## MVP response

The endpoint returns a non-streaming OpenAI-style `chat.completion` containing the RelayLM semantic response.

`stream=true` is rejected explicitly in M3. Safe structured-response streaming is owned by #1269 so that delivery framing cannot leak into semantic cognition/state contracts.

## Concurrency

The one-character MVP serializes turns at the API boundary to prevent overlapping requests from racing Event/State persistence. Multi-character routing and broader scheduling are outside M3.
