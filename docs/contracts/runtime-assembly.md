# Release Runtime Assembly Contract

Status: RCFG3 implementation contract plus provider-backend selection fail-closed follow-up for RelayLM v1. Owning Issue: #1446.

Runtime assembly consumes the validated, non-secret runtime configuration result and constructs only current owner-defined runtime objects. It does not choose cognitive semantics, calibrated numbers, provider wire behavior, backend capability meaning, or Character authority.

## 1. Input and output boundary

Input:

```text
ResolvedRuntimeConfig
  RuntimeConfig
  RuntimeSecretInputs
  source provenance
```

Output:

```text
RuntimeAssembly
  CharacterDirectory
  OpenAICompatibleProvider
  MemoryRetrievalBudget | None
  EventRetrievalBudget | None
  ContinuityRuntime | None
  CognitiveBudgetRuntimeConfig | None
```

Canonical implementation surface: `src/relaylm/runtime_assembly.py`.

`RuntimeAssembly.app_kwargs()` exposes the exact owner objects accepted by `server.create_app`; it performs no semantic transformation.

## 2. Character and provider assembly

`character.directory` becomes a `CharacterDirectory` root. Assembly does not read SOUL, State, Event, MEMORY, or other Character semantic payload while assembling the object. Character readability/semantic validation belongs to startup preflight/doctor.

Provider selection has two distinct identities:

```text
provider.adapter = openai_compatible
provider.backend = generic | vllm | lm_studio
```

The adapter identifies the API protocol family. The backend identifies the implementation/dialect selected from provider-owned `OpenAICompatibleBackendId` authority.

Current assembly capability is intentionally narrower than the selection vocabulary:

```text
backend = generic
  -> existing OpenAICompatibleProvider(base_url, model, api_key)

backend = vllm
  -> requires an explicit provider-owned VLLMReasoningCapabilityAttestation
     bound to the configured request model and frozen actual-model target
  -> OpenAICompatibleProvider with the backend-specific vLLM realizer enabled

backend = lm_studio
  -> capability_unavailable at provider.backend
  -> fail before provider construction/generation
```

The `generic` backend preserves the historical unspecialized OpenAI-compatible path. A selected backend-specific ID must never silently fall through to `generic`; doing so would falsely report a backend-specific selection without applying its dialect. vLLM assembly fails closed when the explicit attestation is absent, malformed, or bound to a different configured request model.

Runtime assembly consumes the provider-owned capability; it does not discover the backend, invent wire mappings, or choose a reasoning mode/budget.

Raw API-key material comes only from `RuntimeSecretInputs`; it is not copied into `RuntimeConfig`, effective-config diagnostics, or `RuntimeAssembly` representation.

Provider wire/schema/decoding/reasoning semantics remain owned by the provider lane.

## 3. Retrieval controls

Explicit file controls map one-to-one into existing Turn owner types:

```text
runtime.memory_retrieval
  -> MemoryRetrievalBudget(max_chunks, max_chars)

runtime.event_retrieval
  -> EventRetrievalBudget(max_events, max_chars)
```

Assembly does not rank, retrieve, filter, score, or reinterpret MEMORY/Event content.

## 4. Continuity runtime

Explicit Continuity settings map to:

```text
ContinuityContext(max_items=configured max_items)
  revision = 0
  items = ()

ContinuityRuntime(
  context=<fresh process-local context>,
  lifetime_revisions=configured lifetime_revisions,
)
```

This is process-local runtime initialization only. It does not redefine candidate acceptance, expiry, resolution, persistence, or lifecycle semantics owned by #1371.

No Continuity capacity/lifetime default is created here.

## 5. Cognitive Budget and token-counter capabilities

An explicit `runtime.cognitive_budget` maps directly to existing #1387 owner types:

```text
ExplicitCognitiveBudgetConfig
  total  ---------------------> CognitiveBudgetRuntimeConfig.total
  policy ---------------------> CognitiveBudgetRuntimeConfig.policy
  token_counter capability ---> registered SerializedCognitiveInputTokenCounter
```

Assembly introduces no context-window, reserve, envelope, floor, degradation-step, or profile numeric default.

A configured token counter is resolved only through an explicit capability registry. A registry entry records:

- capability identifier;
- declared existing `TokenCountMode` (`exact` or `conservative_estimate`);
- factory receiving non-secret `ProviderRuntimeConfig` and returning the existing `SerializedCognitiveInputTokenCounter` protocol.

Assembly fails with `capability_unavailable` when:

- the configured capability is not registered;
- the configured mode differs from the registered capability mode;
- the capability factory fails;
- the factory returns an object that does not implement the existing serialized-input counter protocol.

Factory-internal exceptions are not copied into release-facing assembly error text.

Assembly does not provide a generic tokenizer heuristic. Concrete provider/model token-counter registrations remain explicit release/operator capabilities.

## 6. Invalid overlap

Current Turn semantics reject simultaneous direct MEMORY/Event budgets and `CognitiveBudgetRuntimeConfig`, because Cognitive Budget already assigns retrieval envelopes.

Assembly therefore fails the same invalid combination before serving or generation:

```text
cognitive_budget + memory_retrieval -> invalid_combination
cognitive_budget + event_retrieval  -> invalid_combination
```

This is fail-fast carriage of an existing Turn owner invariant, not a new budget semantic rule.

## 7. Ordinary API wiring

`server.create_app` and `api.openai.create_openai_router` accept the assembled optional controls and pass them unchanged into ordinary Turn functions.

The same configured MEMORY/Event/Continuity/Cognitive Budget objects are passed through both buffered and streaming paths. Assembly does not choose provider backend semantics based on semantic payload.

## 8. Error boundary

Assembly uses the existing release-facing taxonomy, including:

- `invalid_combination` for overlapping owner controls;
- `capability_unavailable` for an explicitly selected backend dialect whose runtime realizer is unavailable;
- `capability_unavailable` for unavailable/incompatible token-count capability;
- `provider_invalid` when validated generic provider configuration cannot construct the current adapter.

Errors remain configuration/capability metadata only and must not include API-key values or Character semantic payload.

## 9. Preserved invariants

Assembly preserves:

- adapter/protocol identity separate from backend implementation identity;
- no backend-specific selection silently falls back to generic behavior;
- backend-specific unavailability fails before generation;
- buffered/streaming semantic-control equivalence;
- Retrieval semantic ownership;
- Continuity lifecycle ownership;
- #1387 deterministic degradation and fail-before-generation behavior;
- Character semantic authority separation;
- secret separation from portable Character data and generic diagnostics.

## 10. Remaining dependency

Backend-specific runtime assembly depends on provider-owned backend realizers. The vLLM path now requires the explicit #1545 attestation and realizer; other backend-specific dialects remain unavailable until their own provider-owned capability and wire contracts exist.

This contract does not add vLLM reasoning wire, LM Studio reasoning wire, automatic backend detection, calibrated cognition defaults, or GUI behavior.
