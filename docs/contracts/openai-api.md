# OpenAI-Compatible API Boundary

RelayLM exposes an OpenAI-compatible client boundary without treating client-supplied history as Cognitive Package authority.

## Direction

```text
client / AITuber UI
        |
        v
POST /v1/chat/completions
  model = Cognitive Profile name
        |
        v
configured Cognitive Profile
  -> Cognitive Package root
  -> effective physical provider/model
        |
        v
RelayLM turn
```

The client-facing `model` field is the public Cognitive Profile selector. It does not directly name or override the physical inference model. RelayLM resolves the supplied value against the configured Profile registry before semantic turn preparation; an unknown Profile returns a public 404 and no Event/State mutation is started.

`GET /v1/models` projects the configured public Cognitive Profile IDs. It does not expose physical provider model IDs as RelayLM public model identities.

Multiple Cognitive Profiles may map to the same physical provider/model, and a Profile may use an explicitly supported physical-model override from runtime configuration. Provider endpoints, backend controls, and secrets remain operator/runtime configuration rather than client authority or Cognitive Package data.

The supported top-level Chat Completions request fields are exactly `model`, `messages`, and `stream`. Other OpenAI Chat Completions controls such as `temperature`, `max_tokens`, `tools`, or `response_format` are not silently accepted as no-ops: unsupported top-level fields fail request validation before generation. Physical provider/model and cognition controls are carried only through RelayLM's explicit owner-defined runtime surfaces when supported.

When supplied, `stream` must be an actual JSON boolean. String or numeric truthy/falsy alternatives are request-validation errors rather than being coerced into buffered or streaming execution. Omitting `stream` preserves the current buffered default (`false`).

## Profile resolution and authority isolation

Buffered and streaming requests resolve `model` through the same Cognitive Profile registry before turn preparation. The resolved Profile supplies the Cognitive Package root, effective provider/model, and Profile-scoped runtime holders used by the turn.

Profile names are validated and unique in runtime configuration. Separate Profile roots preserve separate State, Event, and MEMORY persistence authority; selecting one Profile must not read or mutate another Profile's root merely because both share a physical inference model.

The response and stream `model` identity is the resolved public Cognitive Profile name. It is not rewritten to the physical provider model ID.

## Request authority

RelayLM selects only the last non-empty `user` message as the current governed input.

Earlier client-supplied `system`, `assistant`, and `user` messages are not replayed into Cognitive Context and are not appended into the Event Journal merely because the client sent them. Cognitive continuity comes from the selected Cognitive Package's governed semantic data and RelayLM-owned runtime context.

This prevents unsupported prior assistant statements or arbitrary client system prompts from overriding package Identity/instructions or becoming self-reinforcing memory. The request `model` chooses a configured Profile but does not itself become semantic package content.

## Buffered response

With `stream=false`, the endpoint returns an OpenAI-style `chat.completion` containing the RelayLM semantic response after the complete structured cognitive result has been validated and committed through the ordinary turn path for the resolved Profile.

## Streaming response

With `stream=true`, the current OpenAI-compatible provider path returns `text/event-stream` using OpenAI-style `chat.completion.chunk` frames for the same resolved Profile.

RelayLM starts the governed streaming turn far enough to determine its first observable outcome before committing the successful HTTP streaming response. If the resolved cognitive provider fails with `ProviderProtocolError` before any SSE frame is emitted, the endpoint returns the same HTTP 502 public error boundary as buffered cognition. If the selected Cognitive Package cannot be loaded or validated before any SSE frame is emitted, the endpoint returns the same HTTP 500 public `cognitive package is invalid` boundary as buffered cognition. A pre-emission failure is therefore not represented as an empty HTTP 200 stream.

RelayLM may expose safely decoded characters from the provider wire `utterance` before the complete structured provider object has arrived. This early visible text is delivery only: `state_candidates` remain non-authoritative, and RelayLM creates the Assistant Event and applies State mutation only after the provider stream completes as a valid structured result and the existing Validator accepts the candidates.

A successful stream ends with a final chunk carrying `finish_reason: "stop"` followed by `data: [DONE]`.

Once RelayLM has emitted the first normal SSE frame, the HTTP response status is already committed. If the structured provider stream then truncates or becomes invalid, that visible prefix is not semantically regenerated and RelayLM does not attempt a retroactive status rewrite or emit a new in-band error protocol. The current User Event remains persisted in the selected Profile root, but RelayLM creates no Assistant Event and performs no State mutation for the failed turn. The incomplete stream does not emit the normal successful `stop` / `[DONE]` terminator.

A resolved provider implements RelayLM's streaming provider contract only when its required streaming entrypoint is callable. A missing, null, or non-callable entrypoint rejects `stream=true` at the public boundary before turn preparation, so unsupported streaming cannot append a User Event or silently fall back to a second generation or a different semantic path.

## Concurrency

Core 1.0 may serialize turns globally at the API boundary; concurrent multi-Profile scheduling is not required. The required property is deterministic one-request -> one-Profile realization and Profile-root authority isolation. Streaming retains the same turn lock through provider completion and final commit.

Group-chat selection, automatic semantic routing between Profiles, and broader multi-agent scheduling remain outside this boundary.
