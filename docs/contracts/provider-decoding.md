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

## Reasoning / thinking capability boundary

The current canonical OpenAI-compatible cognitive adapter is a Chat Completions adapter. Its typed request-control contract contains `temperature`, `top_p`, and `seed` only. It does **not** currently expose or serialize a per-request reasoning/thinking mode, reasoning effort, or bounded reasoning budget.

Therefore reasoning is not an implied capability of this adapter merely because a particular upstream product, model, or another endpoint can expose reasoning controls. Support available through a different protocol or endpoint does not flow into the canonical Chat Completions adapter without a provider-owner contract change that adds exact typed carriage, capability declaration, request serialization, identity, and tests.

For consumers such as cognition execution policy and Actual-model Evaluation, the current provider facts are therefore:

```text
per-request reasoning modes      = unsupported
bounded reasoning budget         = unsupported
per-request reasoning override   = unavailable
```

A caller must not label a condition `reasoning off`, `reasoning on`, or `bounded reasoning` merely because that condition was requested in higher-level policy. If the provider cannot carry and attest the request, the requested option remains unsupported and must fail closed or be recorded as unsupported before generation according to the consuming contract.

A model-wide or host-wide reasoning default may be separately observed or attested by an evidence owner when reproducibility requires it. Such an attestation describes the execution environment; it is not a distinct per-pass provider override and must not be represented as though Pass 1 and Pass 2 received different request controls.

Reasoning state must not be inferred from output style, hidden model behavior, or the presence/absence of visible reasoning text.

This boundary is intentionally capability-conservative. Future reasoning carriage, if product requirements justify it, must be added as an explicit provider-owned extension rather than as evaluation-only metadata or an untyped passthrough field.

## Machine-readable cognition capability facts

`OpenAICompatibleCognitionCapabilityFacts` exposes the current adapter facts needed by the COGP consumer boundary without changing the stable P4 provider identity or its historical serialization.

The facts are content-free and separate from provider request configuration. For the current canonical adapter they report:

```text
structured_output          = true
streaming                  = true
reasoning_modes            = []
bounded_reasoning_budget   = false
```

The view also exposes the provider decoding controls that have an exact current COGP per-pass semantic match. At present those are `temperature` and `top_p` when they are declared supported by `OpenAICompatibleDecodingCapabilities`.

`seed` remains provider-level reproducibility configuration and is deliberately not promoted into the current per-pass COGP vocabulary. `max_output_tokens` is not currently carried by this adapter and is therefore not reported as a supported per-pass control.

The base OpenAI-compatible provider and the existing two-pass extension report the same provider-owned capability facts because the two-pass extension changes semantic orchestration methods, not the underlying Chat Completions request capability.

This facts view is intentionally separate from `OpenAICompatibleProviderIdentity.to_mapping()`. Adding the consumer-facing bridge therefore does not retroactively change historical provider identity or actual-model run identity. Consumers may bind the facts separately when their own evidence contract requires capability-resolution provenance.

The provider owner supplies these facts; COGP remains responsible for mapping them into its normalized `CognitionExecutionCapabilities` consumer view and for classifying a requested option as applied, omitted, or unsupported.

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
- reasoning/thinking is unsupported unless the canonical adapter explicitly carries and attests it;
- provider-owned cognition capability facts do not alter historical P4 provider identity;
- provider decoding carriage does not become State, Continuity, Retrieval, Context Compiler, Cognitive Budget, evaluation, or calibration authority.
