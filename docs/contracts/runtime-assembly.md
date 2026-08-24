# Release Runtime Assembly Contract

Status: current RelayLM v1 release assembly contract. Owning Issue: #1446.

Runtime assembly turns one validated `ResolvedRuntimeConfig` into the owner-defined objects used by the ordinary installed API path. It does not choose Character meaning, provider wire semantics, or #1388 calibrated numbers.

## Input and output

```text
ResolvedRuntimeConfig
  RuntimeConfig
  RuntimeSecretInputs
        |
        v
RuntimeAssembly
  CharacterDirectory
  provider
  cognition_mode
  CognitionExecutionRuntime | None
  Pass 1 CognitionPassRequest | None
  Pass 2 CognitionPassRequest | None
  MemoryRetrievalBudget | None
  EventRetrievalBudget | None
  ContinuityRuntime | None
  CognitiveBudgetRuntimeConfig | None
```

`RuntimeAssembly.app_kwargs()` exposes exactly the values accepted by `server.create_app`; it does not reinterpret them.

## Cognition topology

Assembly follows #1533 rather than selecting topology itself.

### `two_pass`

The Core 1.0 release/reference path constructs:

```text
OpenAICompatibleTwoPassProvider
+ one process-local CognitionExecutionRuntime
+ independently resolved Pass 1 / Pass 2 requests
```

The same loaded provider/model is reused sequentially. No second simultaneously resident online model is introduced.

The OpenAI-compatible API then dispatches buffered and streaming turns to the existing response-first two-pass Turn owner. Pass 1 may complete visibly while Pass 2 continues under the existing stale-result, failure, and pending-extraction lifecycle.

### `single_pass`

Explicit `single_pass` constructs the existing `OpenAICompatibleProvider` and preserves the historical `run_user_turn` / `run_user_turn_streaming` compatibility path.

### `auto` and `shadow_two_pass`

`auto` is unresolved profile policy until #1388 publishes calibrated authority. `shadow_two_pass` is evidence-only. Ordinary release assembly rejects both rather than guessing a serving topology.

## Pass controls

Assembly carries already-resolved `CognitionPassRequest` values unchanged. Empty requests mean the controls are omitted; assembly does not invent reasoning, temperature, top-p, output-token, or budget defaults.

Capability truth and exact backend serialization remain provider-owned. Requested values are not evidence that values were applied.

## Provider/backend boundary

Runtime configuration carries:

```text
provider.adapter = openai_compatible
provider.backend = generic | vllm | lm_studio
```

Current specialized capability:

- `generic` — ordinary OpenAI-compatible transport without claiming a backend-specific dialect;
- `vllm` — assembly-capable only with the explicit provider-owned reasoning capability attestation required by the current vLLM realizer;
- `lm_studio` — still fails `capability_unavailable` in this contract until the separate LM Studio runtime-assembly transaction connects the existing provider capability surface.

A backend-specific selection never silently falls through to `generic`.

Raw API-key material comes only from `RuntimeSecretInputs` and is not copied into effective diagnostics or assembly representation.

## Retrieval and Continuity

Explicit retrieval and Continuity settings map directly to their existing owner types. Assembly does not rank content, reinterpret MEMORY/Event evidence, or change Continuity acceptance/lifecycle semantics.

A configured `ContinuityRuntime` is a fresh process-local holder initialized from explicit capacity/lifetime inputs only.

## Cognitive Budget boundary

The existing `runtime.cognitive_budget` maps to the existing #1387 single-pass `CognitiveBudgetRuntimeConfig` through an explicit serialized-input token-counter capability.

Assembly does not provide a tokenizer heuristic or numeric default. Missing, incompatible, or failed counter capabilities are `capability_unavailable`.

Until #1388 publishes per-pass budget authority:

```text
two_pass + runtime.cognitive_budget -> invalid_combination
```

Assembly does not guess that one single-pass total should be copied into both passes.

For explicit `single_pass`, the existing direct-retrieval overlap rule remains:

```text
cognitive_budget + memory_retrieval -> invalid_combination
cognitive_budget + event_retrieval  -> invalid_combination
```

## Ordinary API wiring

The supported installed path is:

```text
runtime config
  -> resolve
  -> preflight
  -> assemble_runtime
  -> server.create_app(**assembly.app_kwargs())
  -> /v1/chat/completions
       buffered | streaming
       -> selected cognition topology
```

For the default Core 1.0 product path, the selected topology is `two_pass`.

Direct Python callers of `create_app` may still explicitly/use its compatibility single-pass default; that helper compatibility does not redefine the installed `relaylm serve` product path.

## Error boundary

Assembly uses the existing release-facing error taxonomy. Typical failures include:

- `invalid_combination` — unresolved/evidence-only cognition mode or owner-control overlap;
- `capability_unavailable` — unavailable selected backend realizer or token-count capability;
- `provider_invalid` — configured provider cannot be constructed safely.

Messages contain configuration/capability metadata only, not Character semantic content or secrets.

## Invariants

Assembly preserves:

- #1533 cognition ownership;
- #1388 numeric/profile ownership;
- provider capability/wire ownership;
- no backend-specific silent generic fallback;
- buffered/streaming two-pass policy equivalence;
- response-first Pass 2 failure semantics;
- Retrieval/Continuity/State authority;
- secret separation.

> Assembly connects owners. It does not become a new policy engine.