# OpenAI-compatible provider reasoning control contract

Status: #1545 R1–R2 provider-owned reasoning capability/request contract and LM Studio capability attestation for RelayLM v1.

This contract defines the deterministic provider boundary for explicit reasoning controls and backend-specific capability truth before exact Chat Completions wire spelling is attached. It does not choose cognition policy, per-pass defaults, numeric reasoning budgets, or calibration values.

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

The request concepts are not backend wire names. Exact translation from fully resolved cognition semantics to supported backend field/value spelling belongs to the wire-realization transaction.

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

Exact backend serialization must construct application identity from the same serializer used for the network request.

## LM Studio reasoning capability attestation

LM Studio-native capability discovery is isolated from the generic OpenAI-compatible protocol in `lm_studio_reasoning.py`.

`LMStudioReasoningCapabilityAttestation` consumes the native `/api/v1/models` response and binds reasoning capability to:

```text
exact request_model
exact unambiguous loaded_instance_id
reasoning.allowed_options
reasoning.default
```

The current LM Studio public reasoning option vocabulary accepted by this attestation is:

```text
off | on | low | medium | high
```

The option set is canonicalized before it becomes `OpenAICompatibleReasoningCapabilities.supported_mode_values`. The native `default` is recorded separately as the loaded model/runtime default; it is not represented as a RelayLM per-request override and does not become a hidden provider request value.

LM Studio documents the `reasoning` capability object as optional and absent when no public reasoning configuration is exposed. Accordingly:

- an exact loaded model with no reasoning capability object attests mode control as unsupported;
- a model family/name does not create capability by inference;
- zero or multiple matching model records fail closed;
- zero or multiple loaded instances fail closed because the configured runtime is ambiguous;
- a loaded-instance identity mismatch fails closed;
- malformed, duplicate, unknown, or default-inconsistent reasoning options fail closed.

The native `/api/v1/models` reasoning object attests public reasoning settings and their default. It does **not** itself attest an explicit reasoning-token budget for the exact configured model/runtime. Therefore R2 leaves `token_budget_supported = false`; a later exact-wire/runtime proof may change that fact only when the provider owner can prove it.

This LM Studio-native attestation is backend-specific. The generic OpenAI-compatible adapter never assumes that another compatible backend exposes `/api/v1/models` or LM Studio's reasoning metadata shape.

## Fail-closed rules

- an explicit mode fails preflight when mode control is not attested;
- an explicit mode fails preflight when mode control exists but the accepted option set is unknown;
- an explicit mode fails preflight when the requested value is absent from the exact attested option set;
- an explicit token budget fails preflight unless token-budget support is attested;
- omitted reasoning remains omitted;
- preflight `ready` must never be reported as `applied` without exact serialized wire fields;
- backend-native discovery that is missing, malformed, or ambiguous cannot be converted into optimistic support.

## Relationship to current provider cognition facts

`OpenAICompatibleCognitionCapabilityFacts` remains the current content-free provider-to-COGP bridge introduced before R1. R2 adds backend/model capability attestation but does not yet attach reasoning carriage to the canonical Chat Completions request path. Therefore the current adapter cognition facts remain reasoning-empty/unsupported until exact request realization exists.

R1–R2 do not rewrite historical provider identity or the existing #1386 unsupported/not-executed evidence. A later transaction may extend effective provider identity/cognition facts only when the same canonical request path can actually carry the attested reasoning control.

## Deferred work

R1–R2 do not implement:

- exact `reasoning_effort`, `reasoning_tokens`, or any other Chat Completions wire field;
- semantic mapping or fallback from provider-neutral `off` / `bounded` intent to backend values;
- distinct Pass 1 / Pass 2 request carriage;
- an `applied` reasoning result on the current adapter;
- runtime config or calibrated defaults;
- actual-model COGP5 reasoning ON/OFF execution.

Those remain later #1545 transactions and consumers.
