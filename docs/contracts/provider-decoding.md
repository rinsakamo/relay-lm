# OpenAI-compatible provider decoding contract

Status: #1456 P3 provider-owned explicit decoding carriage plus #1977 hard output-limit carriage for RelayLM v1.

This contract defines only the OpenAI-compatible cognitive provider request controls that RelayLM can explicitly carry. It does not choose model-quality settings, calibration defaults, release-configuration precedence, or Actual-model Evaluation methodology.

## Purpose

Actual-model evidence must be able to distinguish a decoding value that was actually placed on the provider request from a value that was merely written into evaluation metadata.

The canonical provider therefore exposes typed explicit request configuration and requires an explicit provider/model support declaration before a requested decoding control can be used.

For Cognitive Budget safety, an output reservation is useful only when the corresponding generation can also be hard-bounded. The provider boundary therefore carries the existing provider-neutral `max_output_tokens` cognition control as an actual Chat Completions request limit when that capability is explicitly declared.

## Explicit controls

The provider-owned decoding configuration carries these controls:

- `temperature` — explicit finite numeric value;
- `top_p` — explicit finite numeric value;
- `seed` — explicit integer value;
- `max_output_tokens` — explicit positive integer generation limit, realized on the current canonical Chat Completions wire as `max_tokens`.

These are carriage fields, not RelayLM defaults.

The `max_output_tokens` semantic name is intentionally distinct from its current wire spelling. Current supported vLLM and LM Studio Chat Completions contracts accept `max_tokens`; RelayLM still requires an explicit capability declaration and does not assume that every generic OpenAI-compatible endpoint accepts it.

No numeric value is supplied by RelayLM when the caller omits it:

```text
absent temperature       -> no `temperature` request field
absent top_p             -> no `top_p` request field
absent seed              -> no `seed` request field
absent max_output_tokens -> no `max_tokens` request field
```

The adapter rejects non-numeric/non-finite sampling values and non-positive/untyped output limits locally. Any narrower model/provider range remains an upstream capability/validation concern.

## Typed request configuration

`OpenAICompatibleDecodingConfig` is the provider-owned typed input. Its `to_mapping()` result contains exactly the controls that will be sent upstream and is therefore suitable as content-free request-configuration evidence.

`OpenAICompatibleProvider.effective_decoding_configuration` returns that same exact mapping after capability validation. It contains no API key, prompt text, State, Continuity, MEMORY, Event, or user content.

The mapping is request authority only because buffered and streaming generation call the same provider request serialization boundary with validated configuration.

When a fully resolved `CognitionPassRequest` is supplied, its `temperature`, `top_p`, and `max_output_tokens` values become that pass's effective provider decoding controls; provider-level `seed` remains the reproducibility control already carried across passes. Unsupported explicit pass controls fail before network use.

## Capability declaration and fail-closed behavior

`OpenAICompatibleDecodingCapabilities` declares which decoding controls the selected upstream provider/model supports.

Every explicitly requested control must be present in that declaration. Otherwise provider construction or per-pass capability resolution fails before any network request.

An empty or omitted decoding configuration needs no decoding capability declaration and preserves existing provider behavior.

This is deliberately conservative: RelayLM does not silently send a control merely because another OpenAI-compatible implementation commonly accepts the same field name.

The capability boundary prevents a requested output limit from being recorded as applied when it was not actually carried upstream.

## Reasoning boundary

Reasoning controls are outside this decoding contract. Current provider reasoning capability, backend-specific attestation, exact realization, and request carriage are defined by `docs/contracts/provider-reasoning.md`.

`OpenAICompatibleDecodingConfig` therefore remains limited to decoding/output controls; the absence of reasoning fields from that type neither implies reasoning support nor reasoning unavailability for the canonical provider request path.

## Machine-readable cognition capability facts

`OpenAICompatibleCognitionCapabilityFacts` exposes the current adapter facts needed by the COGP consumer boundary without changing the stable P4 provider identity or its historical serialization.

This decoding contract owns only the decoding-control projection in that facts view. The provider decoding controls with exact current COGP per-pass semantic matches are `temperature`, `top_p`, and `max_output_tokens` when they are declared supported by `OpenAICompatibleDecodingCapabilities`.

`seed` remains provider-level reproducibility configuration and is deliberately not promoted into the current per-pass COGP vocabulary.

Reasoning-related fields in `OpenAICompatibleCognitionCapabilityFacts` are governed by `docs/contracts/provider-reasoning.md`, not by this decoding contract.

This facts view is intentionally separate from `OpenAICompatibleProviderIdentity.to_mapping()`. Adding the consumer-facing bridge therefore does not retroactively change historical provider identity or actual-model run identity. Consumers may bind the facts separately when their own evidence contract requires capability-resolution provenance.

The provider owner supplies these facts; COGP remains responsible for mapping them into its normalized `CognitionExecutionCapabilities` consumer view and for classifying a requested option as applied, omitted, or unsupported.

## Buffered / streaming parity

The same validated decoding mapping is added to buffered and streaming Chat Completions request bodies. Streaming does not alter decoding configuration and does not introduce a second semantic generation.

The two-pass provider uses the same resolved per-pass decoding configuration for buffered Pass 1, streaming Pass 1, and buffered Pass 2, so distinct explicit output limits remain distinct request facts.

## Cognitive Budget relationship

This provider contract does not choose `reserved_output_tokens`; #1387 owns Cognitive Budget arithmetic and #1388 owns calibrated recommendation policy.

For a budgeted pass, downstream runtime assembly may rely on the following safety relationship only after it has resolved both values:

```text
reserved_output_tokens >= applied provider hard output limit
```

The provider side of that comparison is the actual applied `max_tokens` request value produced here, not a value merely requested in metadata. Exact runtime validation/carriage remains #1446 ownership.

## Serialized-input accounting

`OpenAICompatibleSerializedInputCounter` accepts the same optional `OpenAICompatibleDecodingConfig` so its provider/model-specific counting callback can observe the same serialized request shape as generation, excluding only the transport `stream` flag as before.

This does not change Cognitive Budget semantics or claim that a decoding field consumes input tokens. The supplied provider/model-specific counter remains responsible for its own accounting behavior.

## Consumer boundary

Actual-model Evaluation (#1386) may use the provider's applied decoding mapping as evidence authority, but this contract does not change scoring, scenarios, cohorts, or evidence methodology.

Release Runtime / Configuration (#1446) may carry these provider-owned typed inputs, but this provider contract does not add YAML fields, environment variables, CLI options, discovery, precedence, or loader/assembly rules.

Calibration (#1388) remains the sole owner of any canonical numeric output allowance or recommendation.

## Invariants

- no hidden or invented numeric defaults;
- omitted means omitted;
- unsupported requested controls fail before network use;
- `max_output_tokens` is a positive provider-neutral control and current wire `max_tokens` is inspectable request authority;
- buffered and streaming requests carry identical explicit decoding semantics;
- distinct Pass 1 / Pass 2 output limits remain distinct;
- effective decoding evidence contains no secrets or semantic payload;
- cognition execution topology remains owned by `cognitive_turn`, not this decoding contract;
- reasoning capability and carriage remain owned by `docs/contracts/provider-reasoning.md`, not this decoding contract;
- provider-owned cognition capability facts do not alter historical P4 provider identity;
- provider decoding carriage does not become State, Continuity, Retrieval, Context Compiler, Cognitive Budget, evaluation, or calibration authority.
