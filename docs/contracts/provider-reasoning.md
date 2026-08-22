# OpenAI-compatible provider reasoning control contract

Status: #1545 R1–R3C provider-owned reasoning contract, LM Studio capability attestation, vLLM configured-runtime capability, exact realization, and single/two-pass carriage for RelayLM v1.

This contract defines the deterministic provider boundary for explicit reasoning controls, backend-specific capability truth, and proven backend request spelling. It does not choose cognition policy, per-pass defaults, numeric reasoning budgets, or calibration values.

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

The request concepts are not backend wire names. Exact translation from fully resolved cognition semantics to supported backend field/value spelling belongs to backend realization.

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

## vLLM exact reasoning wire vocabulary

`src/relaylm/providers/vllm_reasoning.py` freezes the exact vLLM Chat Completions request field spelling that current upstream authority exposes:

```text
reasoning_effort
thinking_token_budget
```

The current public `reasoning_effort` vocabulary frozen by this provider dialect is:

```text
none | minimal | low | medium | high | xhigh | max
```

`VLLMReasoningWireControls` is deliberately a **wire-level** type. It serializes only exact vLLM public request spelling and chooses no RelayLM semantic policy. Empty controls serialize to an empty mapping, so omission remains omission.

RelayLM's provider-neutral mode spelling is not reused as vLLM wire spelling:

```text
RelayLM semantic: off | bounded
vLLM wire:        none | minimal | low | medium | high | xhigh | max
```

Therefore `off` and `bounded` are rejected by the low-level vLLM wire type rather than silently rewritten. The semantic-to-wire mapping requires separate model/runtime capability proof.

For `thinking_token_budget`, RelayLM's vLLM wire primitive accepts only a positive explicit integer. Current vLLM itself also has provider-specific meanings for zero and `-1`; RelayLM does not expose those through this primitive because its existing explicit provider reasoning budget is positive and omission already represents no explicit RelayLM budget. This is an intentional supported subset, not a claim about vLLM's entire public input domain.

Crucially, existence of these fields does not establish that they are semantically effective for every configured model/runtime:

- `reasoning_effort` may interact with model chat-template thinking controls;
- some reasoning models/templates use different thinking switches;
- `thinking_token_budget` requires reasoning configuration/parser support and model/runtime compatibility;
- backend identity alone does not prove either control is applicable.

Accordingly, this low-level wire vocabulary still chooses no RelayLM semantic policy. The R3C realizer below is the only provider-owned path that may combine it with an attested configured runtime and construct an applied application record.

## Configured vLLM/model reasoning capability attestation

`src/relaylm/providers/vllm_reasoning_capability.py` records explicit probe
results for one already-attested vLLM server/model runtime. The attestation
requires only a structural frozen target identity view carrying these four
non-empty strings:

```text
target_id
revision
model_artifact_identity
artifact_repository_revision
```

The caller owns loading, verifying, and selecting the target representation.
The provider does not import or require an actual-model evaluation target type.
The resulting capability evidence carries the supplied target identity alongside
the vLLM backend version and exact served model identity; it does not infer target
identity from a model name.

Each control is classified independently as:

```text
unsupported
accepted_but_effect_unproven
semantically_attested
malformed_or_ambiguous
```

Protocol acceptance is not semantic proof. A control reaches
`semantically_attested` only when the supplied evidence records an accepted
exact wire, a repeatable observed effect, and the configured activation context
required by that control. Positive bounded reasoning additionally requires the
numeric `thinking_token_budget` field and an exact template activation kwarg;
effort labels are not numeric budget substitutes. The exact probe wire and
template kwargs remain separate from a later
`OpenAICompatibleReasoningApplication`.

For OFF, a probe that also activates the configured template thinking control
is `malformed_or_ambiguous`. The attestation records the deterministic later
realizer rule that conflicting template kwargs must be rejected. Unsupported,
unproven, or ambiguous observations never receive an effort-tier or generic
fallback wire.

## vLLM semantic realization and carriage

`vllm_reasoning_realization.py` accepts only a fully resolved
`OpenAICompatibleReasoningRequest` and the matching R3B capability attestation.
It produces the requested, resolved, and applied identities from the same
serializer that produces the request fields:

```text
RelayLM off
  -> reasoning_effort: none
  -> no template kwargs (conflicting enable_thinking kwargs fail closed)

RelayLM bounded(N)
  -> thinking_token_budget: N
  -> chat_template_kwargs: { enable_thinking: true }
```

`bounded` never chooses `N`, and `low`/`medium`/`high` are never used as a
substitute. If the corresponding capability status is not
`semantically_attested`, the realizer constructs an unsupported application and
refuses to produce request fields. An unresolved `auto`, missing bounded
budget, mismatched target/model attestation, or conflicting template kwargs
fails closed before network serialization.

The canonical ordinary single-pass builder and both two-pass builders consume
this same realizer. A caller may pass different fully resolved requests for
Pass 1 and Pass 2; Pass 2 is not implicitly strengthened merely by being Pass
2. When a vLLM capability is explicitly attached to the provider, provider
cognition facts expose only the attested `off`/`bounded` modes and budget
support.

## Fail-closed rules

- an explicit mode fails preflight when mode control is not attested;
- an explicit mode fails preflight when mode control exists but the accepted option set is unknown;
- an explicit mode fails preflight when the requested value is absent from the exact attested option set;
- an explicit token budget fails preflight unless token-budget support is attested;
- omitted reasoning remains omitted;
- preflight `ready` must never be reported as `applied` without exact serialized wire fields;
- backend-native discovery that is missing, malformed, or ambiguous cannot be converted into optimistic support;
- a known backend wire field does not by itself establish model-specific semantic applicability;
- provider-neutral reasoning modes must not be silently treated as backend-public effort values.

## Relationship to current provider cognition facts

`OpenAICompatibleCognitionCapabilityFacts` remains the current content-free provider-to-COGP bridge introduced before R1. Without an explicitly attached configured vLLM attestation, the generic adapter remains reasoning-empty/unsupported. With one attached attestation, only the modes whose R3B status is `semantically_attested` are exposed.

R1–R3C do not rewrite historical provider identity or the existing #1386 unsupported/not-executed reasoning evidence. A later actual-model transaction may consume the applied identity only when the same canonical request path carries the attested control.

## Deferred work

Current provider authority still does not implement:

- exact LM Studio Chat Completions reasoning wire;
- runtime config or calibrated reasoning defaults;
- actual-model COGP5 reasoning ON/OFF execution.

Those remain later #1545 transactions and consumers.
