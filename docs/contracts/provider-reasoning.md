# OpenAI-compatible provider reasoning control contract

Status: #1545 R1 provider-owned reasoning capability/request contract for RelayLM v1.

This contract defines the deterministic provider boundary for explicit reasoning controls before backend-specific discovery and exact Chat Completions wire spelling are attached. It does not choose cognition policy, per-pass defaults, numeric reasoning budgets, or calibration values.

## Ownership

The semantic flow remains:

```text
calibration/profile/config
  -> fully resolved provider-neutral cognition request
  -> provider reasoning request/capability contract
  -> backend-specific deterministic realization
  -> exact request fields
```

`auto` is not a provider realization value. It must already be resolved by the upstream cognition policy/profile boundary before this provider contract is used.

The provider does not decide that Pass 1 or Pass 2 deserves a particular reasoning mode or budget.

## Capability truth

`OpenAICompatibleReasoningCapabilities` distinguishes three separate facts for mode-like controls:

```text
mode_control_supported = false
  no mode/effort-like request control has been attested

mode_control_supported = true
supported_mode_values = unknown
  a control exists, but its exact accepted option set is not attested
  -> explicit mode requests fail closed

mode_control_supported = true
supported_mode_values = exact tuple
  exact public accepted values are attested
```

Explicit reasoning-token budget support is represented independently as `token_budget_supported`.

Unknown capability is never treated as permission to send an explicit request. The generic OpenAI-compatible contract does not infer capability from a model name, output style, or the presence of a backend-specific endpoint.

## Explicit request

`OpenAICompatibleReasoningRequest` contains only explicitly supplied values:

```text
mode
explicit token_budget
```

Both are optional. The empty request means RelayLM does not add a reasoning control. No provider reasoning default is invented by R1.

R1 deliberately does not freeze backend wire names. `mode` and `token_budget` are provider-contract request concepts, not claims that a backend accepts fields with those literal names.

## Preflight versus application

Capability preflight and actual application are distinct.

`OpenAICompatibleReasoningPreflightStatus` is:

```text
omitted
ready
unsupported
```

`ready` means only that the attested capability can represent the explicit request. It is not evidence that any backend field was sent.

`OpenAICompatibleReasoningApplicationStatus` is:

```text
omitted
unsupported
applied
```

`applied` is intentionally stronger. `OpenAICompatibleReasoningApplication` requires both the explicit requested values and the exact serialized wire field/value mapping. A request cannot be represented as applied with an empty wire mapping.

R1 creates this invariant but does not yet create an applied request path. Exact backend serialization belongs to the later wire-carriage transaction, which must construct application identity from the same serializer used for the network request.

## Fail-closed rules

- an explicit mode fails preflight when mode control is not attested;
- an explicit mode fails preflight when mode control exists but the accepted option set is unknown;
- an explicit mode fails preflight when the requested value is absent from the exact attested option set;
- an explicit token budget fails preflight unless token-budget support is attested;
- omitted reasoning remains omitted;
- preflight `ready` must never be reported as `applied` without exact serialized wire fields.

## Relationship to current provider cognition facts

`OpenAICompatibleCognitionCapabilityFacts` remains the current content-free provider-to-COGP bridge introduced before R1. Until backend/model reasoning capability is attached to the canonical provider request path, its current reasoning facts remain empty/unsupported.

R1 does not rewrite historical provider identity or the existing #1386 unsupported/not-executed evidence. Later #1545 transactions may extend the current capability facts only after exact backend/model attestation and request carriage exist.

## Deferred work

R1 does not implement:

- LM Studio-native capability discovery;
- `reasoning_effort`, `reasoning_tokens`, or any other exact wire field;
- semantic mapping or fallback from `off` / `bounded` to backend values;
- distinct Pass 1 / Pass 2 request carriage;
- runtime config or calibrated defaults;
- actual-model COGP5 execution.

Those remain later #1545 transactions and consumers.
