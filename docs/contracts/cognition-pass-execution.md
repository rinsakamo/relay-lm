# Cognition Pass Execution Contract

Status: COGP2 provider-neutral per-pass execution-option contract for RelayLM v1.

This contract is owned by #1533 under the existing `cognitive_turn` owner. It defines the semantic intent and pre-generation capability-resolution boundary for Pass 1 and Pass 2 without choosing any numeric default or changing provider wire semantics.

# Policy intent versus generation request

COGP distinguishes two stages.

## Policy intent

`CognitionPassPolicy` describes a per-pass policy before Calibration/profile resolution.

Reasoning mode is closed to:

```text
auto
off
bounded
```

For scalar controls, `None` in the typed policy means **profile-owned `auto`**, not a hidden provider default. COGP2 defines intent only; #1388 later resolves canonical `auto` values from evidence-backed profiles, while #1446 carries direct operator overrides and precedence.

The initial per-pass scalar controls are:

```text
temperature
top_p
max_output_tokens
```

A bounded reasoning policy may also carry an explicit positive integer reasoning budget. A missing budget under `bounded` means the budget remains profile-owned `auto`; it is not permission to silently inherit an unknown upstream setting at generation time.

COGP2 chooses no temperature, top-p, output-token, or reasoning-budget value.

## Fully resolved generation request

`CognitionPassRequest` is the pre-generation form after all policy-owned `auto` values have been resolved by an authorized caller/profile decision.

In this type:

- `reasoning_mode` may be `off`, `bounded`, or explicit omission;
- `reasoning_mode=auto` is invalid and fails before generation;
- an explicit reasoning budget requires `bounded` mode;
- scalar `None` means explicit omission from the effective provider request, not unresolved `auto`;
- explicit numeric controls are validated only for provider-neutral shape (finite numeric values, positive integer output/budget values). Provider-specific narrower ranges remain provider-owner validation.

This separation ensures `auto` and `omitted` are not conflated.

# Normalized capability view

`CognitionExecutionCapabilities` is a COGP-owned normalized **consumer view** over capability facts supplied by the actual provider/model owner. It is not a second provider authority and does not discover or infer provider support itself.

The view can express:

```text
structured_output
streaming
supported explicit reasoning modes: off / bounded
bounded reasoning-budget control
supported per-pass decoding/output controls
```

`auto` is never a provider capability. It is a RelayLM policy-resolution state.

Provider adapters remain authoritative for how support is discovered, declared, attested, or mapped onto an external API. COGP must consume truthful provider facts rather than invent support from common OpenAI-compatible field names.

## Provider-facts normalization boundary

`normalize_cognition_execution_capabilities(...)` is the provider-neutral bridge from primitive, provider-owned capability facts into the typed COGP consumer view.

The bridge performs **normalization only**. It does not import provider classes, inspect endpoints, discover support, infer aliases, or promote controls that merely look similar.

Accepted provider-fact vocabulary is exactly the current COGP vocabulary:

```text
reasoning modes:
  off
  bounded

per-pass decoding controls:
  temperature
  top_p
  max_output_tokens
```

The normalizer preserves provider-supplied `structured_output`, `streaming`, and `bounded_reasoning_budget` booleans, converts only exact closed strings into the existing COGP enums, and rejects duplicate facts before constructing the frozenset view.

Unknown values fail closed. `auto` also fails closed because it is policy resolution rather than provider capability. A provider-level control such as `seed` is rejected at this boundary unless COGP separately expands its owned per-pass vocabulary in a future transaction.

This prevents evaluation/runtime consumers from each re-implementing provider-to-COGP interpretation. The provider owner states the facts; COGP owns the exact semantic normalization; downstream consumers use the resulting typed view.

# Applied / omitted / unsupported identity

`resolve_pass_request(...)` classifies every materially output-affecting pass option as exactly one of:

```text
applied
omitted
unsupported
```

The resolution is content-free and records the requested value alongside its status. It is suitable for later runtime/evidence identity without containing prompts, Identity, State, Continuity, Events, MEMORY, API keys, or other semantic payload.

Meaning:

- `applied` — the requested explicit control is present in the supplied capability view and may be carried by the provider owner;
- `omitted` — the resolved request intentionally carries no explicit value for that option;
- `unsupported` — an explicit request was made but the supplied provider/model capability view does not declare support.

Unsupported is never silently rewritten to omitted.

`CognitionPassResolution.require_supported()` fails closed before generation if any explicit option is `unsupported`. A future calibrated profile may deliberately resolve a policy to an omitted or alternate supported request, but that fallback decision belongs to the profile/default owner and must remain auditable.

# Mode-level capability gate

`require_mode_capabilities(...)` is the provider-neutral pre-generation mode gate.

- `auto` must already be resolved before generation;
- the current RelayLM cognition modes require a structured-output capability somewhere in their semantic result path;
- a streaming execution request requires declared streaming support;
- unsupported requirements fail before generation rather than being silently ignored.

This gate does not claim that capability declaration proves product quality. #1386 actual-model evidence remains responsible for observed model behavior.

# Relationship to existing OpenAI-compatible provider controls

The canonical OpenAI-compatible provider already owns explicit `temperature` and `top_p` carriage plus support declarations. COGP2 deliberately uses the same semantic control names rather than creating provider-specific aliases.

`max_output_tokens` and reasoning/thinking controls are provider-neutral COGP intent in this transaction; COGP2 does not claim that the current OpenAI-compatible adapter can carry them. Until the provider owner supplies truthful support, an explicit resolved request for such a control is unsupported and must fail closed.

Existing provider `seed` remains provider-owned decoding configuration and is not promoted into the initial per-pass COGP control set by this transaction. Controlled evaluation may continue holding provider-level seed/config identity fixed independently of per-pass policy.

# Reproducibility principle

Materially output-affecting pass configuration must remain distinguishable as applied, omitted, or unsupported. Reasoning/thinking state therefore cannot be treated as unrecorded ambient behavior when causal A/B/C evidence is claimed.

This reuses the existing repository principle established by actual-model crystallization reasoning identity without copying CRY-specific LM Studio attestation semantics into ordinary-turn COGP authority.

# Ownership boundaries

COGP / #1533 owns:

- per-pass reasoning/decoding intent semantics;
- the `auto` versus effective omission distinction;
- the normalized execution-policy capability requirements;
- provider-facts-to-COGP vocabulary normalization;
- applied/omitted/unsupported classification;
- fail-closed semantics for explicit unsupported pass requests.

Provider owners own:

- actual external request fields/endpoints;
- provider/model capability discovery and truthful declarations;
- provider-specific value/range validation;
- exact applied wire configuration.

#1388 owns evidence-backed canonical profile/default resolution.

#1446 owns config schema carriage, precedence, direct operator overrides, and effective-config provenance.

#1386 owns actual-model evidence identity/methodology consuming the resulting applied configuration.

# COGP2 non-goals

COGP2 does not implement:

- OpenAI/LM Studio reasoning wire controls;
- a reasoning endpoint switch;
- provider-specific prompt hacks;
- numeric defaults;
- profile selection;
- runtime-config keys;
- Pass 1 / Pass 2 orchestration;
- shadow evidence execution;
- model-specific fallback tables.

# Current resolved-request carriage

Later merged provider work under #1545 supplies truthful configured-vLLM `off` / `bounded(N)` realization. The current COGP runtime now carries a fully resolved `CognitionPassRequest` through the canonical buffered Turn path without moving backend wire policy into Turn semantics.

The ordinary path is:

```text
CognitionPassRequest
  -> run_user_turn(..., pass_request=...)
  -> OpenAICompatibleProvider.generate(..., pass_request=...)
  -> provider-owned capability normalization + require_supported()
  -> provider-owned exact vLLM realization
  -> exact Chat Completions request
```

The two-pass path carries independently resolved requests:

```text
pass1_request
  -> run_user_turn_two_pass
  -> generate_conversation

pass2_request
  -> originating-turn-bound extraction task
  -> generate_extraction
```

Neither Turn nor the provider chooses a reasoning budget or strengthens Pass 2 merely because it is Pass 2. The caller must supply the fully resolved request.

When no pass request is supplied, existing Turn/provider behavior is preserved. Existing generic providers are not required to accept a new keyword merely to continue serving the historical no-request path.

For the canonical OpenAI-compatible adapter:

- explicit per-pass `temperature` / `top_p` replace provider-wide values for that request;
- explicit omission leaves those per-pass fields omitted;
- provider-wide `seed` remains held fixed because seed is not currently a COGP-owned per-pass control;
- reasoning is translated only through the attested provider-owned `off` / `bounded(N)` realization;
- an explicit `max_output_tokens` request remains unsupported under current capability facts and fails before network generation;
- a `CognitionPassRequest` and a direct provider-owned reasoning request cannot both be supplied to the same call, avoiding ambiguous double authority.

The provider entry points also use the same resolver for their streaming serializers. This bounded runtime transaction wires the canonical buffered Turn path needed for first COGP5 actual-model screening; it does not choose a streaming release profile or any numeric default.
