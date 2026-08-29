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
  CognitiveBudgetRuntimeConfig | TwoPassCognitiveBudgetRuntimeConfig | None
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

A request still realizes one Cognitive Profile and one response-first two-pass turn. No second simultaneously resident online model or multi-agent scheduler is introduced by Profile routing.

The OpenAI-compatible API resolves the request `model` to one Profile before dispatching buffered or streaming execution to the response-first two-pass Turn owner. Pass 1 may complete visibly while Pass 2 continues. When a newer turn supersedes an older pending Pass 2, #1978 requires RelayLM to cancel and join that obsolete local extraction task before the newer Pass 1 begins provider generation; stale/no-commit guards remain authoritative after that scheduling boundary.

### `single_pass`

Explicit `single_pass` constructs one `OpenAICompatibleProvider` per Profile and preserves the existing `run_user_turn` / `run_user_turn_streaming` compatibility path after Profile resolution.

### `auto` and `shadow_two_pass`

`auto` is unresolved calibration policy until #1388 publishes calibrated authority. `shadow_two_pass` is evidence-only. Ordinary release assembly rejects both rather than guessing a serving topology.

## Pass controls

Assembly carries already-resolved `CognitionPassRequest` values unchanged. Empty requests mean the controls are omitted; assembly does not invent reasoning, temperature, top-p, output-token, or budget defaults.

Pass requests are common runtime policy carried into whichever Profile is selected. Capability truth and exact backend serialization remain provider-owned. Requested values are not evidence that values were applied.

For a budgeted two-pass release path, `max_output_tokens` is no longer optional: each pass must carry an explicit positive hard output limit that the selected provider backend can truthfully realize, and that limit must not exceed the configured Cognitive Budget output reservation.

## Provider/backend boundary

Runtime configuration carries:

```text
provider.adapter = openai_compatible
provider.backend = generic | vllm | lm_studio
```

Current assembly behavior:

- `generic` — ordinary OpenAI-compatible transport without claiming backend-specific capability truth;
- `vllm` — assembly-capable only with the explicit provider-owned reasoning capability attestation required by the current vLLM realizer;
- `lm_studio` — ordinary OpenAI-compatible buffered/two-pass transport is assembly-capable when LM Studio-specific reasoning controls are omitted. The resolved backend identity remains `lm_studio`; assembly does not rewrite it to `generic`.

Provider-owned backend capability mapping is also the authority for whether an explicit per-pass hard output limit can be carried. A known backend may expose that proven control; `generic` compatibility alone does not prove it. Budget assembly fails closed when a required hard output limit cannot be attested.

LM Studio capability metadata and exact Chat Completions reasoning realization are separate concerns. #1545 owns LM Studio capability attestation, while exact LM Studio Chat Completions reasoning wire remains separately qualified. An unsupported explicit Pass 1/Pass 2 reasoning control fails `capability_unavailable` before serving rather than being silently omitted or guessed onto a vendor field.

Reusing the common OpenAI-compatible transport for requests that require no backend-specific wire is not a backend-identity fallback. A backend-specific selection is preserved in resolved configuration and diagnostics, and any requested specialized capability still requires its provider-owned realizer.

Raw API-key material comes only from `RuntimeSecretInputs` and is not copied into effective diagnostics, Profile objects intended for diagnostics, or assembly representation.

## Retrieval and Continuity

Explicit retrieval settings map directly to their existing owner types. Assembly does not rank content, reinterpret MEMORY/Event evidence, or change retrieval semantics.

A configured `ContinuityRuntime` is created separately for every Cognitive Profile. Each starts as a fresh process-local holder initialized from explicit capacity/lifetime inputs only. Selecting one Profile therefore cannot mutate another Profile's Continuity holder.

## Cognitive Budget boundary

`runtime.cognitive_budget` carries the existing #1387 total-budget semantics. Assembly selects the owner runtime type according to the already-resolved cognition topology; it does not invent numeric values or a new degradation policy.

Assembly does not provide a tokenizer heuristic or numeric default. Missing, incompatible, or failed counter capabilities are `capability_unavailable`.

### Single-pass

For explicit `single_pass`, the configured total, policy and single-pass serialized-input counter construct the existing `CognitiveBudgetRuntimeConfig` unchanged.

### Two-pass

For `two_pass`, #1979 makes the explicit release configuration usable without adding a second budget schema. The one operator/configuration-supplied coarse total is intentionally applied to both real generation passes:

```text
runtime.cognitive_budget.total
        -> pass1_total
        -> pass2_total
```

This is explicit release carriage, not an inference that the two prompts have equal size and not a #1388 numeric default. Pass 1 and Pass 2 continue to count their distinct exact serialized request shapes independently against that same coarse safety envelope.

Two-pass budget assembly additionally requires:

```text
registered token counter implements both two-pass count operations
Pass 1 max_output_tokens is explicit
Pass 2 max_output_tokens is explicit
selected backend can attest hard output-limit carriage
pass1.max_output_tokens <= reserved_output_tokens
pass2.max_output_tokens <= reserved_output_tokens
```

Failure of any prerequisite is fail-closed before generation. The provider owner remains authoritative for the actual upstream hard-limit wire.

The direct-retrieval overlap rule remains topology-independent:

```text
cognitive_budget + memory_retrieval -> invalid_combination
cognitive_budget + event_retrieval  -> invalid_combination
```

A Profile-local physical-model override is also incompatible with the current global Cognitive Budget token-counter configuration. Assembly fails that combination rather than assuming one counter is valid across physical models.

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
         -> selected single-pass or two-pass Cognitive Budget runtime
```

`/v1/models` projects the registry's public Profile IDs. It does not project physical provider-model IDs.

For the default Core 1.0 product path, the selected topology is `two_pass` after the request has selected one Profile. Buffered and streaming two-pass routes receive the same assembled budget object and enforce the same per-pass totals/counter semantics.

Direct Python callers of `create_app` must also supply an explicit `CognitiveProfileRegistry`; they do not bypass Profile identity or restore the removed Character-only API boundary.

## Error boundary

Assembly uses the existing release-facing error taxonomy. Typical failures include:

- `invalid_combination` — unresolved/evidence-only cognition mode, owner-control overlap, missing two-pass hard output limit, or a pass hard limit larger than the reserved output capacity;
- `capability_unavailable` — unavailable selected backend-specific capability, hard output-limit carriage, or token-count capability;
- `provider_invalid` — configured provider cannot be constructed safely.

Messages contain configuration/capability metadata only, not Cognitive Package semantic content or secrets.

## Invariants

Assembly preserves:

- one configured public Profile -> one Cognitive Package root and runtime bundle;
- public Profile identity separated from physical provider/model identity;
- State/Event/MEMORY authority isolation across Profile roots;
- Profile-local Continuity and two-pass execution holders;
- #1533 cognition ownership and #1978 stale extraction scheduling bound;
- #1388 numeric/calibration-profile ownership;
- #1387 Cognitive Budget arithmetic/degradation ownership;
- provider capability/wire ownership;
- backend identity even when a shared transport implementation is used;
- no unproven backend-specific control silently reaches the wire;
- every budgeted two-pass hard output limit is no larger than its reserved output capacity;
- buffered/streaming Profile, two-pass policy and budget equivalence;
- response-first Pass 2 failure semantics;
- Retrieval/Continuity/State authority;
- secret separation.

> Assembly connects a public Cognitive Profile to its portable cognitive root and physical inference substrate. It carries explicit safety envelopes but does not invent calibrated numbers or semantics.
