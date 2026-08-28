# Release Runtime Assembly Contract

Status: current RelayLM v1 release assembly contract. Owning Issue: #1446.

Runtime assembly turns one validated `ResolvedRuntimeConfig` into the owner-defined objects used by the ordinary installed API path. It does not choose Cognitive Package meaning, public Profile identity, provider wire semantics, or #1388 calibrated numbers.

## Input and output

```text
ResolvedRuntimeConfig
  RuntimeConfig
    profiles[]
    provider
    runtime policy
  RuntimeSecretInputs
        |
        v
RuntimeAssembly
  CognitiveProfileRegistry
    CognitiveProfileRuntime per configured Profile
      name
      CognitivePackageDirectory
      provider
      physical_model
      ContinuityRuntime | None
      CognitionExecutionRuntime | None
  cognition_mode
  Pass 1 CognitionPassRequest | None
  Pass 2 CognitionPassRequest | None
  MemoryRetrievalBudget | None
  EventRetrievalBudget | None
  CognitiveBudgetRuntimeConfig | None
```

`RuntimeAssembly.app_kwargs()` exposes exactly the values accepted by `server.create_app`; it does not reinterpret them.

## Cognitive Profile assembly

Assembly constructs one `CognitiveProfileRuntime` for each validated `profiles[]` entry.

For each Profile:

```text
public name
  -> one CognitivePackageDirectory(root)
  -> one effective physical model
  -> one provider instance
  -> Profile-local ContinuityRuntime when configured
  -> Profile-local CognitionExecutionRuntime in two-pass mode
```

The effective physical model is `profiles[].provider.model` when explicitly configured and otherwise the global `provider.model`. The public Profile name never becomes the physical provider model by implication.

Multiple Profiles may share the same physical provider/model while retaining separate Cognitive Package roots and therefore separate State/Event/MEMORY authority. Assembly does not merge Profile roots or reuse semantic persistence across Profiles.

Machine configuration and secrets remain outside the Cognitive Package. Profile-local overrides are limited to runtime leaves explicitly supported by the configuration contract.

## Cognition topology

Assembly follows #1533 rather than selecting topology itself.

### `two_pass`

The Core 1.0 release/reference path constructs, for each configured Profile:

```text
OpenAICompatibleTwoPassProvider
+ Profile-local CognitionExecutionRuntime
+ independently resolved Pass 1 / Pass 2 requests
```

A request still realizes one Cognitive Profile and one sequential two-pass turn. No second simultaneously resident online model or multi-agent scheduler is introduced by Profile routing.

The OpenAI-compatible API resolves the request `model` to one Profile before dispatching buffered or streaming execution to the existing response-first two-pass Turn owner. Pass 1 may complete visibly while Pass 2 continues under the existing stale-result, failure, and pending-extraction lifecycle.

### `single_pass`

Explicit `single_pass` constructs one `OpenAICompatibleProvider` per Profile and preserves the existing `run_user_turn` / `run_user_turn_streaming` compatibility path after Profile resolution.

### `auto` and `shadow_two_pass`

`auto` is unresolved calibration policy until #1388 publishes calibrated authority. `shadow_two_pass` is evidence-only. Ordinary release assembly rejects both rather than guessing a serving topology.

## Pass controls

Assembly carries already-resolved `CognitionPassRequest` values unchanged. Empty requests mean the controls are omitted; assembly does not invent reasoning, temperature, top-p, output-token, or budget defaults.

Pass requests are common runtime policy carried into whichever Profile is selected. Capability truth and exact backend serialization remain provider-owned. Requested values are not evidence that values were applied.

## Provider/backend boundary

Runtime configuration carries:

```text
provider.adapter = openai_compatible
provider.backend = generic | vllm | lm_studio
```

Current assembly behavior:

- `generic` — ordinary OpenAI-compatible transport without claiming a backend-specific dialect;
- `vllm` — assembly-capable only with the explicit provider-owned reasoning capability attestation required by the current vLLM realizer;
- `lm_studio` — ordinary OpenAI-compatible buffered/two-pass transport is assembly-capable when LM Studio-specific reasoning controls are omitted. The resolved backend identity remains `lm_studio`; assembly does not rewrite it to `generic`.

LM Studio capability metadata and exact Chat Completions reasoning realization are separate concerns. #1545 owns LM Studio capability attestation, while exact LM Studio Chat Completions reasoning wire remains separately qualified. An unsupported explicit Pass 1/Pass 2 reasoning control fails `capability_unavailable` before serving rather than being silently omitted or guessed onto a vendor field.

Reusing the common OpenAI-compatible transport for requests that require no backend-specific wire is not a backend-identity fallback. A backend-specific selection is preserved in resolved configuration and diagnostics, and any requested specialized capability still requires its provider-owned realizer.

Raw API-key material comes only from `RuntimeSecretInputs` and is not copied into effective diagnostics, Profile objects intended for diagnostics, or assembly representation.

## Retrieval and Continuity

Explicit retrieval settings map directly to their existing owner types. Assembly does not rank content, reinterpret MEMORY/Event evidence, or change retrieval semantics.

A configured `ContinuityRuntime` is created separately for every Cognitive Profile. Each starts as a fresh process-local holder initialized from explicit capacity/lifetime inputs only. Selecting one Profile therefore cannot mutate another Profile's Continuity holder.

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

A Profile-local physical-model override is also incompatible with the current global single-pass Cognitive Budget token-counter configuration. Assembly fails that combination rather than assuming one counter is valid across physical models.

## Ordinary API wiring

The supported installed path is:

```text
runtime config
  -> resolve profiles[] + physical provider policy
  -> preflight
  -> assemble_runtime
  -> CognitiveProfileRegistry
  -> server.create_app(**assembly.app_kwargs())
  -> /v1/chat/completions
       request model
         -> exact Profile resolution
         -> Profile package/provider/runtime
         -> buffered | streaming
         -> selected cognition topology
```

`/v1/models` projects the registry's public Profile IDs. It does not project physical provider-model IDs.

For the default Core 1.0 product path, the selected topology is `two_pass` after the request has selected one Profile.

Direct Python callers of `create_app` must also supply an explicit `CognitiveProfileRegistry`; they do not bypass Profile identity or restore the removed Character-only API boundary.

## Error boundary

Assembly uses the existing release-facing error taxonomy. Typical failures include:

- `invalid_combination` — unresolved/evidence-only cognition mode or owner-control overlap;
- `capability_unavailable` — unavailable selected backend-specific capability or token-count capability;
- `provider_invalid` — configured provider cannot be constructed safely.

Messages contain configuration/capability metadata only, not Cognitive Package semantic content or secrets.

## Invariants

Assembly preserves:

- one configured public Profile -> one Cognitive Package root and runtime bundle;
- public Profile identity separated from physical provider/model identity;
- State/Event/MEMORY authority isolation across Profile roots;
- Profile-local Continuity and two-pass execution holders;
- #1533 cognition ownership;
- #1388 numeric/calibration-profile ownership;
- provider capability/wire ownership;
- backend identity even when a shared transport implementation is used;
- no unproven backend-specific control silently reaches the wire;
- buffered/streaming Profile and two-pass policy equivalence;
- response-first Pass 2 failure semantics;
- Retrieval/Continuity/State authority;
- secret separation.

> Assembly connects a public Cognitive Profile to its portable cognitive root and physical inference substrate. It does not become a new routing policy or semantic engine.
