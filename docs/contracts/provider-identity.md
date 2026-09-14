# OpenAI-compatible provider capability and configuration identity

Status: #1456 P4 stable provider-owned identity surface plus #1545 R3A backend vocabulary and #2898 llama.cpp release carriage for RelayLM v1.

This contract exposes stable, content-free provider identity so Actual-model Evaluation (#1386) and Release Runtime / Configuration (#1446) can consume provider capabilities and applied request configuration without private adapter inspection.

It does not redefine evaluation identity methodology, release configuration precedence, provider wire semantics, Continuity, Cognitive Budget, or calibration defaults.

## Format and adapter identity

The provider-owned identity format is version `1`.

The canonical adapter identity is:

```text
openai_compatible
```

The adapter identity names the API protocol family. It does **not** identify which backend implementation serves that protocol.

The current strict structured-output schema name is:

```text
relaylm_cognitive_output
```

These are stable machine-facing identifiers. They are not model aliases or provider deployment names.

## Backend implementation identity

#1545 separates the OpenAI-compatible adapter from the backend implementation/dialect that realizes backend-specific controls.

The provider-owned canonical backend IDs currently are:

```text
generic
vllm
lm_studio
llama_cpp
```

Their human-facing display names are:

```text
generic    -> Generic OpenAI-compatible
vllm       -> vLLM
lm_studio  -> LM Studio
llama_cpp  -> llama.cpp
```

`openai_compatible` is deliberately **not** a backend ID; it remains the adapter/protocol identity above.

`generic` represents the existing unspecialized OpenAI-compatible path. `vllm`, `lm_studio`, and `llama_cpp` identify backend-specific dialect families without claiming that every backend-specific capability is already implemented or applicable to every configured model/runtime.

`llama_cpp` is a first-class external-process backend. RelayLM speaks the
OpenAI-compatible Chat Completions and input-token surfaces of an externally
managed `llama-server`; RelayLM does not bundle, launch, supervise, or replace
that process. Its canonical display name is `llama.cpp` and its bounded input
aliases are `llama_cpp`, `llama-cpp`, and `llama.cpp`.

The selected spelling does not attest a capability. A serializable,
condition-specific llama.cpp attestation must bind the exact runtime/model
identity, streaming, native structured output, reasoning-OFF, decoding,
context-shift, cache, and exact-counter facts before assembly can use them.
Arbitrary BYOM GGUF artifacts are therefore not automatically qualified.

Machine identity and display text are separate. `resolve_openai_compatible_backend(...)` accepts only an explicit bounded alias set, trims surrounding whitespace, and case-folds input. It never fuzzy-matches or auto-detects a backend. For example, `vLLM` resolves to canonical machine ID `vllm`, while unknown spellings and undeclared backends fail closed.

The canonical registry lives in `src/relaylm/providers/openai_compatible_backend.py`. Downstream configuration/evidence must persist the canonical ID rather than the user-facing spelling. #1552 now carries that provider-owned value through `provider.backend`; runtime configuration does not redefine backend meaning.

## vLLM backend identity attestation

`src/relaylm/providers/vllm_backend.py` defines a provider-owned, content-free attestation for the `vllm` backend.

The attestation consumes responses from two vLLM API surfaces:

```text
/version
/v1/models
```

It binds:

```text
backend = vllm
vLLM version
configured request_model
exact matching served model id
reported model root, if present
reported max_model_len, if present
attestation source endpoints
```

`/v1/models` must contain exactly one model card whose public `id` equals the configured RelayLM request model. Missing or ambiguous matches fail closed. The matching card must identify itself as a model. Optional `root` and `max_model_len` metadata are validated when present.

`model_root` and `max_model_len` are **reported serving metadata**, not immutable model-artifact identity. #1386 remains responsible for exact model/tokenizer/artifact evidence identity where required.

The vLLM attestation deliberately does not infer reasoning capability, reasoning mode, token-budget applicability, structured-output support, or decoding capability merely because the backend is vLLM or because a model name appears in `/v1/models`. Those facts require their own provider-owned capability/wire proof.

## llama.cpp release capability attestation

`src/relaylm/providers/llama_cpp_backend.py` is the production-owned
capability and counter boundary. It is intentionally independent from
`actual_model_*` evaluation hosts. The configured attestation binds:

```text
backend = llama_cpp
request model and external runtime/model identity
reasoning_effort=none support
native strict structured-output support
streaming support
explicit decoding controls
cache policy = disabled
context shift = disabled
exact /v1/chat/completions/input_tokens counter and framing identity
```

The Core 1.0 cache baseline is conservative: every ordinary buffered Pass 1,
streaming Pass 1, and Pass 2 request carries `cache_prompt: false`. Cache reuse
is not a release optimization or a quality claim. The pinned upstream source
contract for the qualified carriage is llama.cpp revision
`e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`, build `10874`; a different
revision/model/template condition requires a new attestation.

This module parses supplied API responses and creates a typed identity record. Repository CI does not pretend to contact the operator's live vLLM server; live response acquisition belongs to the later host/preflight integration that can actually reach the configured deployment.

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

The current P4 object predates the separate backend vocabulary and therefore does not yet claim an applied backend implementation identity. The typed vLLM attestation is a separate provider-owned fact until a later #1545/R4 consumer-convergence transaction wires live backend attestation into effective provider/evidence identity truthfully.

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

For #1446, the identity is an owner-defined provider surface that runtime diagnostics or assembly may consume. Provider-owned backend IDs supply the canonical values; #1446 owns how runtime configuration selects and carries one of those values.

`VLLMBackendAttestation.to_mapping()` is a separate content-free observed-backend record suitable for later host/preflight/evidence integration. A configured `backend: vllm` value by itself is requested identity; the attestation represents observed API identity.

## Privacy and authority invariants

- no API key or secret reference value appears in identity or diagnostics;
- no secret is hashed to manufacture identity;
- no semantic payload is included;
- adapter identity and backend identity remain distinct concepts;
- configured backend selection and observed backend attestation remain distinguishable;
- human display spelling never becomes canonical machine identity;
- unknown backend identity is never fuzzy-matched into support;
- vLLM family identity never implies model-specific reasoning capability;
- llama.cpp backend identity never implies model, GGUF, streaming, reasoning, structured-output, cache, or token-counter capability;
- llama.cpp runtime/model identity is condition-specific and is not inferred from a model family or filename;
- capability tokens describe declared adapter/provider support, not successful model behavior;
- seed-field support is not a deterministic-model guarantee;
- decoding configuration describes exactly carried explicit request fields, not evaluator metadata;
- provider identity remains transport/configuration authority only and does not become State, Continuity, Retrieval, Context Compiler, Cognitive Budget, evaluation, or calibration authority.
