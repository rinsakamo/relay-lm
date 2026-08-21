# Cognition Pass Execution Contract

Status: COGP provider-neutral per-pass execution-option contract for RelayLM v1, including the RelayLM-owned canonical two-pass extraction boundary.

This contract is owned by #1533 under the existing `cognitive_turn` owner. It defines the semantic intent and pre-generation capability-resolution boundary for Pass 1 and Pass 2 without choosing any numeric default or moving provider wire ownership into COGP.

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

For scalar controls, `None` in the typed policy means **profile-owned `auto`**, not a hidden provider default. COGP defines intent only; #1388 later resolves canonical `auto` values from evidence-backed profiles, while #1446 carries direct operator overrides and precedence.

The initial per-pass scalar controls are:

```text
temperature
top_p
max_output_tokens
```

A bounded reasoning policy may also carry an explicit positive integer reasoning budget. A missing budget under `bounded` means the budget remains profile-owned `auto`; it is not permission to silently inherit an unknown upstream setting at generation time.

COGP chooses no temperature, top-p, output-token, or reasoning-budget value.

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

`structured_output` remains a truthful provider capability because the legacy combined `single_pass` and therefore the current canonical side of `shadow_two_pass` still use it. It is **not** a prerequisite for canonical `two_pass`: Pass 2 returns ordinary message content containing the RelayLM-owned compact proposal IR, which RelayLM parses and validates itself.

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
- `single_pass` requires provider `structured_output` because its current legacy wire combines visible response and proposals in one structured result;
- `shadow_two_pass` currently requires provider `structured_output` because its canonical result remains that legacy `single_pass` path, even though its shadow extraction uses the RelayLM-owned proposal IR parser;
- canonical `two_pass` does **not** require provider `structured_output`; Pass 1 is plain natural language and Pass 2 is plain provider message content parsed into the RelayLM-owned proposal IR;
- a streaming execution request requires declared streaming support;
- unsupported requirements fail before generation rather than being silently ignored.

This gate does not claim that capability declaration proves product quality. #1386 actual-model evidence remains responsible for observed model behavior.

# RelayLM-owned Pass 2 structure

Canonical `two_pass` separates semantic extraction from provider structured-output features:

```text
Pass 2 model request
  -> ordinary provider chat/message generation
  -> plain text content containing compact proposal IR
  -> RelayLM JSON parse
  -> exact IR key/shape checks
  -> typed StateCandidate / ContinuityCandidate construction
  -> existing deterministic validation/lifecycle
```

The compact proposal IR contains only:

```text
state_candidates
continuity_candidates
```

The provider does not receive RelayLM's canonical Pass 2 schema through `response_format`, JSON-schema grammar, or an equivalent provider-owned structured-output field. The model is instructed in the RelayLM-owned Pass 2 prompt about the exact proposal-IR shape; the provider transports ordinary content. Malformed JSON, extra top-level keys, invalid candidate shape, or invalid typed values fail closed in RelayLM and produce no candidate commit.

This keeps multilingual semantic interpretation in the model while keeping structure, parsing, normalization, and authority in RelayLM. No language-specific parser is introduced.

# Relationship to existing OpenAI-compatible provider controls

The canonical OpenAI-compatible provider already owns explicit `temperature` and `top_p` carriage plus support declarations. COGP deliberately uses the same semantic control names rather than creating provider-specific aliases.

`max_output_tokens` and reasoning/thinking controls are provider-neutral COGP intent; COGP does not claim support until the provider owner supplies truthful capability/carriage. An explicit unsupported request must fail closed.

Existing provider `seed` remains provider-owned decoding configuration and is not promoted into the initial per-pass COGP control set. Controlled evaluation may continue holding provider-level seed/config identity fixed independently of per-pass policy.

Provider-native structured-output capability is similarly retained as provider truth for paths that actually use it, but it is not a hidden requirement for canonical `two_pass`.

# Reproducibility principle

Materially output-affecting pass configuration must remain distinguishable as applied, omitted, or unsupported. Reasoning/thinking state therefore cannot be treated as unrecorded ambient behavior when causal A/B/C evidence is claimed.

For canonical Pass 2, reproducibility also requires the RelayLM proposal-IR prompt/parser contract to be frozen by repository revision. A backend grammar mode is not part of the semantic authority because canonical Pass 2 does not depend on one.

This reuses the existing repository principle established by actual-model crystallization reasoning identity without copying CRY-specific LM Studio attestation semantics into ordinary-turn COGP authority.

# Ownership boundaries

COGP / #1533 owns:

- per-pass reasoning/decoding intent semantics;
- the `auto` versus effective omission distinction;
- the normalized execution-policy capability requirements;
- provider-facts-to-COGP vocabulary normalization;
- applied/omitted/unsupported classification;
- fail-closed semantics for explicit unsupported pass requests;
- the canonical Pass 2 compact proposal-IR contract and RelayLM-side parse/type-construction boundary.

Provider owners own:

- actual external request fields/endpoints;
- provider/model capability discovery and truthful declarations;
- provider-specific value/range validation;
- exact applied reasoning/decoding wire configuration;
- transport of ordinary Pass 2 message content.

Provider owners do not own canonical Pass 2 proposal structure merely because a backend offers JSON-schema/grammar features.

#1388 owns evidence-backed canonical profile/default resolution.

#1446 owns config schema carriage, precedence, direct operator overrides, and effective-config provenance.

#1386 owns actual-model evidence identity/methodology consuming the resulting applied configuration and must remeasure exact Pass 1/Pass 2 footprints after this contract change before revised screening.

# Non-goals

This contract does not implement or select:

- numeric defaults;
- profile selection;
- runtime-config keys;
- a reasoning endpoint switch;
- provider-specific fallback tables;
- language-specific extraction parsers;
- direct model mutation of State/Continuity;
- a provider-native structured-output requirement for canonical `two_pass`.

# Current resolved-request carriage

Merged provider work under #1545 supplies truthful configured-vLLM `off` / `bounded(N)` realization. The current COGP runtime carries a fully resolved `CognitionPassRequest` without moving backend wire policy into Turn semantics.

The ordinary legacy path is:

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
  -> plain visible response

pass2_request
  -> originating-turn-bound extraction task
  -> generate_extraction
  -> ordinary provider message content
  -> RelayLM proposal-IR parse/type construction
```

Neither Turn nor the provider chooses a reasoning budget or strengthens Pass 2 merely because it is Pass 2. The caller must supply the fully resolved request.

When no pass request is supplied, existing Turn/provider behavior is preserved. Existing generic providers are not required to accept a new keyword merely to continue serving the historical no-request path.

For the canonical OpenAI-compatible adapter:

- explicit per-pass `temperature` / `top_p` replace provider-wide values for that request;
- explicit omission leaves those per-pass fields omitted;
- provider-wide `seed` remains held fixed because seed is not currently a COGP-owned per-pass control;
- reasoning is translated only through the attested provider-owned `off` / `bounded(N)` realization;
- an explicit `max_output_tokens` request remains unsupported under current capability facts and fails before network generation;
- a `CognitionPassRequest` and a direct provider-owned reasoning request cannot both be supplied to the same call, avoiding ambiguous double authority;
- Pass 2 does not send provider-native `response_format`/JSON-schema structure; RelayLM parses the returned content itself.

The provider entry points use the same resolver for their streaming serializers. No release profile or numeric default is chosen here.
