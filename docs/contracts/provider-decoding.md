# OpenAI-compatible provider decoding contract

Status: #1456 P3 provider-owned explicit decoding carriage for RelayLM v1.

This contract defines only the OpenAI-compatible cognitive provider request controls that RelayLM can explicitly carry. It does not choose model-quality settings, calibration defaults, release-configuration precedence, or Actual-model Evaluation methodology.

## Purpose

Actual-model evidence must be able to distinguish a decoding value that was actually placed on the provider request from a value that was merely written into evaluation metadata.

The canonical provider therefore exposes typed explicit request configuration and requires an explicit provider/model support declaration before a requested decoding control can be used.

## Initial explicit controls

P3 carries exactly these OpenAI-compatible request fields:

- `temperature` — explicit finite numeric value;
- `top_p` — explicit finite numeric value;
- `seed` — explicit integer value.

These are carriage fields, not RelayLM defaults.

No numeric value is supplied by RelayLM when the caller omits it:

```text
absent temperature -> no `temperature` request field
absent top_p       -> no `top_p` request field
absent seed        -> no `seed` request field
```

P3 intentionally does not invent provider/model-specific numeric ranges. The adapter rejects non-numeric or non-finite values locally, while any narrower model/provider range remains an upstream capability/validation concern.

## Typed request configuration

`OpenAICompatibleDecodingConfig` is the provider-owned typed input. Its `to_mapping()` result contains exactly the controls that will be sent upstream and is therefore suitable as content-free request-configuration evidence.

`OpenAICompatibleProvider.effective_decoding_configuration` returns that same exact mapping after capability validation. It contains no API key, prompt text, State, Continuity, MEMORY, Event, or user content.

The mapping is request authority only because both buffered and streaming generation call the same provider request serializer with the validated configuration.

## Capability declaration and fail-closed behavior

`OpenAICompatibleDecodingCapabilities` declares which of the initial controls the selected upstream provider/model supports.

Every explicitly requested control must be present in that declaration. Otherwise provider construction raises `ProviderCapabilityError` before any network request.

An empty or omitted decoding configuration needs no decoding capability declaration and preserves existing provider behavior.

This is deliberately conservative: RelayLM does not silently send a control merely because another OpenAI-compatible implementation commonly accepts the same field name.

P3 does not yet define the broader stable provider capability/config identity required by #1456 P4. It only creates the typed support boundary necessary to prevent unsupported requested decoding values from being recorded as though they were applied.

## Buffered / streaming parity

The same validated decoding mapping is added to both buffered and streaming Chat Completions request bodies. Streaming does not alter decoding configuration and does not introduce a second semantic generation.

The structured semantic output contract remains independent of these controls:

```text
one request
  + explicit decoding fields
  + strict structured output
        |
        v
CognitiveOutput
```

## Serialized-input accounting

`OpenAICompatibleSerializedInputCounter` accepts the same optional `OpenAICompatibleDecodingConfig` so its provider/model-specific counting callback can observe the same serialized request shape as generation, excluding only the transport `stream` flag as before.

This does not change Cognitive Budget semantics or claim that a decoding field consumes input tokens. The supplied provider/model-specific counter remains responsible for its own accounting behavior.

## Consumer boundary

Actual-model Evaluation (#1386) may use the provider's applied decoding mapping as evidence authority, but P3 does not change `ActualModelRunManifest`, scoring, scenarios, cohorts, or evidence methodology.

Release Runtime / Configuration (#1446) may later carry these provider-owned typed inputs, but P3 does not add YAML fields, environment variables, CLI options, discovery, precedence, or loader/assembly rules.

Calibration (#1388) remains the sole owner of any future canonical numeric decoding choice if such a choice is ever established.

## Invariants

- no hidden or invented numeric defaults;
- omitted means omitted;
- unsupported requested controls fail before network use;
- buffered and streaming requests carry identical explicit decoding controls;
- effective decoding evidence contains no secrets or semantic payload;
- exactly one ordinary semantic model generation remains authoritative;
- provider decoding carriage does not become State, Continuity, Retrieval, Context Compiler, Cognitive Budget, evaluation, or calibration authority.
