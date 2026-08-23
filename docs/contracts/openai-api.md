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

The supported top-level request fields are exactly `model`, `messages`, and `stream`. Other OpenAI Chat Completions controls such as `temperature`, `max_tokens`, `tools`, or `response_format` are not silently accepted as no-ops: unsupported top-level fields fail request validation before generation. Provider/model/cognition controls are carried only through RelayLM's explicit owner-defined runtime surfaces when supported.

When supplied, `stream` must be an actual JSON boolean. String or numeric truthy/falsy alternatives are request-validation errors rather than being coerced into buffered or streaming execution. Omitting `stream` preserves the current buffered default (`false`).

## Request authority

RelayLM selects only the last non-empty `user` message as the current governed input.

Earlier client-supplied `system`, `assistant`, and `user` messages are not replayed into Cognitive Context and are not appended into the Event Journal merely because the client sent them. Character continuity comes from `SOUL.md`, Canonical State, and RelayLM-governed Context.

This prevents unsupported prior assistant statements or arbitrary client system prompts from overriding character Identity or becoming self-reinforcing memory.

## Buffered response

With `stream=false`, the endpoint returns an OpenAI-style `chat.completion` containing the RelayLM semantic response after the complete structured cognitive result has been validated and committed through the ordinary turn path.

## Streaming response

With `stream=true`, the current OpenAI-compatible provider path returns `text/event-stream` using OpenAI-style `chat.completion.chunk` frames.

RelayLM may expose safely decoded characters from the provider wire `utterance` before the complete structured provider object has arrived. This early visible text is delivery only: `state_candidates` remain non-authoritative, and RelayLM creates the Assistant Event and applies State mutation only after the provider stream completes as a valid structured result and the existing Validator accepts the candidates.

A successful stream ends with a final chunk carrying `finish_reason: "stop"` followed by `data: [DONE]`.

If the structured provider stream truncates or becomes invalid after some safe utterance text was already emitted, that visible prefix is not semantically regenerated. The current User Event remains persisted, but RelayLM creates no Assistant Event and performs no State mutation for the failed turn. The incomplete stream does not emit the normal successful `stop` / `[DONE]` terminator.

A configured provider that does not implement RelayLM's streaming provider contract rejects `stream=true` rather than silently falling back to a second generation or a different semantic path.

## Concurrency

The one-character runtime serializes turns at the API boundary to prevent overlapping requests from racing Event/State persistence. Streaming retains the same turn lock through provider completion and final commit. Multi-character routing and broader scheduling remain outside the current boundary.
