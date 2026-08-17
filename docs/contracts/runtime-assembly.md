# Release Runtime Assembly Contract

Status: RCFG3 implementation contract for RelayLM v1. Owning Issue: #1446.

RCFG3 consumes the validated, non-secret RCFG2 result and constructs only current owner-defined runtime objects. It does not choose cognitive semantics, calibrated numbers, provider wire behavior, or Character authority.

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

`character.directory` becomes a `CharacterDirectory` root. RCFG3 does not read SOUL, State, Event, MEMORY, or other Character semantic payload while assembling the object. Character readability/semantic validation belongs to startup preflight/doctor work in RCFG4.

The currently supported `openai_compatible` provider configuration becomes `OpenAICompatibleProvider(base_url, model, api_key)`. Raw API-key material comes only from RCFG2 `RuntimeSecretInputs`; it is not copied into `RuntimeConfig`, effective-config diagnostics, or `RuntimeAssembly` representation.

Provider wire/schema/decoding semantics remain owned by the provider lane and are unchanged by this assembly contract.

## 3. Retrieval controls

Explicit file controls map one-to-one into existing Turn owner types:

```text
runtime.memory_retrieval
  -> MemoryRetrievalBudget(max_chunks, max_chars)

runtime.event_retrieval
  -> EventRetrievalBudget(max_events, max_chars)
```

RCFG3 does not rank, retrieve, filter, score, or reinterpret MEMORY/Event content.

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

RCFG3 introduces no context-window, reserve, envelope, floor, degradation-step, or profile numeric default.

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

RCFG3 does not provide a generic tokenizer heuristic. Concrete provider/model token-counter registrations remain explicit release/operator capabilities.

## 6. Invalid overlap

Current Turn semantics reject simultaneous direct MEMORY/Event budgets and `CognitiveBudgetRuntimeConfig`, because Cognitive Budget already assigns retrieval envelopes.

RCFG3 therefore fails the same invalid combination during assembly, before serving or generation:

```text
cognitive_budget + memory_retrieval -> invalid_combination
cognitive_budget + event_retrieval  -> invalid_combination
```

This is fail-fast carriage of an existing Turn owner invariant, not a new budget semantic rule.

## 7. Ordinary API wiring

`server.create_app` and `api.openai.create_openai_router` accept the assembled optional controls and pass them unchanged into both ordinary Turn functions:

```text
buffered  -> run_user_turn(...)
streaming -> run_user_turn_streaming(...)
```

The same configured MEMORY/Event/Continuity/Cognitive Budget objects are passed on both paths. RCFG3 does not add a second LLM call or a separate streaming policy.

The legacy `create_app_from_env()` startup helper is intentionally not converted into the new loader/assembly CLI path in RCFG3. RCFG4 will make `serve`/`doctor` consume RCFG2 + RCFG3 through the supported operator entrypoint.

## 8. Error boundary

RCFG3 uses the existing RCFG1 release-facing taxonomy for assembly failures, including:

- `invalid_combination` for overlapping owner controls;
- `capability_unavailable` for unavailable/incompatible token-count capability;
- `provider_invalid` when the validated provider configuration cannot construct the current adapter.

Errors remain configuration/capability metadata only and must not include API-key values or Character semantic payload.

## 9. Preserved invariants

RCFG3 preserves:

- exactly one ordinary semantic generation;
- buffered/streaming semantic-control equivalence;
- Retrieval semantic ownership;
- Continuity lifecycle ownership;
- #1387 deterministic degradation and fail-before-generation behavior;
- Character semantic authority separation;
- secret separation from portable Character data and generic diagnostics.

## 10. Remaining work

RCFG3 does not implement:

- `relaylm serve` / `relaylm doctor` CLI parsing and operator output (RCFG4);
- Character/package/provider reachability preflight (RCFG4);
- canonical calibrated profile/default consumption (#1388 -> RCFG5);
- installed-artifact operator smoke (RCFG6);
- provider wire changes (#1456 lane);
- UI/presence work.
