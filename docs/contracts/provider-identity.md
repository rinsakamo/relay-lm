# OpenAI-compatible provider capability and configuration identity

Status: #1456 P4 stable provider-owned identity surface for RelayLM v1.

This contract exposes a stable, content-free description of the canonical OpenAI-compatible cognitive adapter so Actual-model Evaluation (#1386) and Release Runtime / Configuration (#1446) can consume provider capabilities and applied request configuration without private adapter inspection.

It does not redefine evaluation identity methodology, release configuration precedence, provider wire semantics, Continuity, Cognitive Budget, or calibration defaults.

## Format and adapter identity

The provider-owned identity format is version `1`.

The canonical adapter identity is:

```text
openai_compatible
```

The current strict structured-output schema name is:

```text
relaylm_cognitive_output
```

These are stable machine-facing identifiers. They are not model aliases or provider deployment names.

## Structured semantic channels

The canonical adapter currently transports these semantic channels from one provider generation:

```text
response
state_candidates
continuity_candidates
```

The capability surface exposes those exact semantic names. In particular, it deliberately reuses the existing #1386 scenario capability tokens `state_candidates` and `continuity_candidates` rather than introducing a provider-specific translation vocabulary.

## Delivery capabilities

The canonical adapter exposes:

```text
buffered
streaming
```

Both delivery forms produce the same completed semantic `CognitiveOutput` contract. `streaming` means the provider implements the current safe structured-response streaming path; it does not relax final candidate validation or authorize partial semantic output.

The flattened `provider_capabilities` / `capability_tokens` surface contains the structured semantic channel names plus supported delivery tokens and declared decoding-control names. This makes the current #1386 preflight vocabulary directly consumable:

```text
state_candidates
continuity_candidates
streaming
```

No evaluation-only capability aliasing is required.

## Decoding-control capability versus applied configuration

Declared decoding support and applied request configuration remain separate:

- `supported_decoding_controls` lists the explicit provider/model controls declared available through the P3 support boundary;
- `decoding_configuration` contains only the exact explicit controls actually carried on provider requests;
- `seed_control_supported` is true only when the selected provider/model declares support for the `seed` request field.

`seed_control_supported` means **request-field support only**. It is not a claim that an upstream implementation is perfectly deterministic, bit-reproducible, or reproducible across model/server/runtime changes.

The initial provider-owned decoding-control vocabulary remains:

```text
temperature
top_p
seed
```

No numeric defaults or model-specific tuning values are created by this identity surface.

## Request configuration identity

`OpenAICompatibleProviderIdentity` includes:

- identity format version;
- canonical adapter identity;
- configured provider request model identifier;
- canonical structured-output schema name;
- exact effective decoding configuration;
- structured semantic, delivery, and decoding-control capabilities.

Changing the request model or effective decoding configuration changes this identity value. Changing a secret does not.

The identity intentionally does **not** include `api_key`, Authorization material, semantic payload, prompt text, State, Continuity, MEMORY, Events, or user content.

It also does not treat the connection endpoint (`base_url`) as part of this provider-owned request/config identity. Deployment/provider-instance identity remains a separate consumer concern: #1386 already carries a distinct `provider_identity`, while #1446 owns the machine/runtime configuration that selects `base_url`. This separation prevents connection strings from becoming implicit evidence identity or leaking embedded credentials through diagnostics. P4 does not hash excluded values and never treats an API key hash as identity.

## Consumer shape

`describe_openai_compatible_provider(provider)` returns an immutable `OpenAICompatibleProviderIdentity` from the canonical provider's already-validated public configuration surface. It performs no network request and reads no semantic content.

For #1386, consumers may directly use:

```text
identity.adapter_identity
identity.provider_capabilities
identity.effective_decoding_configuration
```

alongside #1386-owned provider/model/evidence identity fields. P4 does not mutate `ActualModelRunManifest` or decide how evidence artifacts are assembled.

For #1446, the identity is an owner-defined provider surface that later runtime diagnostics or assembly may consume. P4 does not add YAML keys, environment variables, CLI flags, config discovery, precedence, or loader semantics.

## Privacy and authority invariants

- no API key or secret reference value appears in identity or diagnostics;
- no secret is hashed to manufacture identity;
- no semantic payload is included;
- capability tokens describe declared adapter/provider support, not successful model behavior;
- seed-field support is not a deterministic-model guarantee;
- decoding configuration describes exactly carried explicit request fields, not evaluator metadata;
- provider identity remains transport/configuration authority only and does not become State, Continuity, Retrieval, Context Compiler, Cognitive Budget, evaluation, or calibration authority.
