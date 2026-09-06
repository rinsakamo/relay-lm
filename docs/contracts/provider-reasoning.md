# OpenAI-compatible provider reasoning control contract

Status: #1545 current provider-owned reasoning contract for RelayLM v1, including LM Studio configured-runtime capability attestation and exact binary Chat Completions carriage, plus vLLM configured-runtime capability and exact realization.

This contract defines the deterministic provider boundary for explicit reasoning controls, backend-specific capability truth, and proven backend request spelling. It does not choose cognition policy, per-pass defaults, numeric reasoning budgets, or calibration values.

## Ownership

The semantic flow is:

```text
calibration/profile/config
  -> fully resolved provider-neutral cognition request
  -> provider reasoning request/capability contract
  -> backend-specific deterministic realization
  -> exact request fields
```

`auto` is not a provider realization value. It must resolve before this boundary. The provider does not decide that Pass 1 or Pass 2 deserves a particular reasoning mode or budget.

## Capability truth

`OpenAICompatibleReasoningCapabilities` distinguishes:

```text
mode_control_supported = false
  no mode-like request control is attested

mode_control_supported = true
supported_mode_values = unknown
  a control exists but exact accepted values are unknown
  -> explicit mode requests fail closed

mode_control_supported = true
supported_mode_values = exact tuple
  exact public accepted values are attested
```

Explicit reasoning-token budget support is independent as `token_budget_supported`.

Unknown capability is never permission to send a control. The generic OpenAI-compatible contract does not infer capability from model names, output style, or backend reputation.

## Explicit request and application

`OpenAICompatibleReasoningRequest` contains only explicit caller intent:

```text
mode
explicit token_budget
```

The empty request means RelayLM adds no reasoning control. No hidden provider default is manufactured.

Capability preflight and actual application are distinct. `ready` means only that an attested capability can represent the request. `OpenAICompatibleReasoningApplicationStatus.APPLIED` is stronger and requires both the requested semantic value and non-empty exact serialized wire fields produced by the same realization path used for the network request.

## LM Studio configured-runtime capability attestation

LM Studio-native capability discovery is isolated in `lm_studio_reasoning.py`; it is not assumed for generic OpenAI-compatible providers.

`LMStudioReasoningCapabilityAttestation` consumes native `/api/v1/models` data and binds capability to:

```text
exact request_model
exact unambiguous loaded_instance_id
reasoning.allowed_options
reasoning.default
```

The accepted LM Studio public reasoning metadata vocabulary is:

```text
off | on | low | medium | high
```

The native default is recorded as an observed runtime fact only. It never becomes an implicit RelayLM request value.

Fail-closed rules include:

- no reasoning capability object -> mode control unsupported;
- model family/name never creates capability by inference;
- zero or multiple matching model records fail;
- zero or multiple loaded instances fail;
- loaded-instance identity mismatch fails;
- malformed, duplicate, unknown, or default-inconsistent options fail.

Native model metadata does not attest an explicit reasoning-token budget for Chat Completions, so current LM Studio `token_budget_supported` remains false.

## LM Studio exact Chat Completions realization

For an exact loaded LM Studio model whose native capability attests the requested binary option, the current backend realizer uses the OpenAI-compatible Chat Completions field:

```text
reasoning_effort
```

Current exact binary mapping is identity-preserving:

```text
LM Studio public off -> reasoning_effort: off
LM Studio public on  -> reasoning_effort: on
```

The lower-level provider realizer accepts only these attested binary values. `low`, `medium`, and `high` may appear in native capability metadata but are not currently qualified by this realizer and therefore fail closed. Explicit reasoning-token budgets also fail closed.

RelayLM's current provider-neutral cognition vocabulary is narrower than LM Studio's public vocabulary. Current Core cognition exposes `off` and `bounded(N)`, not a generic `on` or effort-tier semantic mode. Consequently:

- an attached LM Studio attestation exposes provider-neutral `off` to current cognition capability resolution only when `off` is attested;
- `bounded(N)` remains unsupported for LM Studio because no reasoning-token budget is attested;
- current runtime assembly accepts explicit LM Studio `reasoning_mode=off` only;
- an attested live default such as `on` does not satisfy an explicit OFF request.

The canonical single-pass request builder, two-pass Pass 1 builder, two-pass Pass 2 builder, streaming Pass 1 builder, and off-turn Crystallization request builder all consume the same provider-owned reasoning dispatcher. For LM Studio OFF they serialize the exact same request field:

```json
{"reasoning_effort":"off"}
```

No `reasoning_tokens`, `thinking_token_budget`, or vLLM chat-template controls are added by the LM Studio OFF realization.

The current LM Studio Stage R and observed-condition Crystallization runners obtain native model metadata, bind the exact loaded instance, require an attested `off` option, and attach that capability to the production OpenAI-compatible serializer. Their execution evidence records the live model default separately from the request-time explicit OFF realization. Therefore a model may truthfully report `default=on` while the qualified request is still explicitly `reasoning_effort=off`.

## vLLM exact reasoning wire vocabulary

`src/relaylm/providers/vllm_reasoning.py` freezes the current vLLM Chat Completions request spelling:

```text
reasoning_effort
thinking_token_budget
```

The vLLM public `reasoning_effort` vocabulary represented by that wire type is:

```text
none | minimal | low | medium | high | xhigh | max
```

This is a wire-level vocabulary, not RelayLM cognition semantics. RelayLM provider-neutral values are not silently reused as vLLM wire values.

For current vLLM realization:

```text
RelayLM off
  -> reasoning_effort: none
  -> no conflicting template thinking activation

RelayLM bounded(N)
  -> thinking_token_budget: N
  -> chat_template_kwargs: { enable_thinking: true }
```

`bounded` never chooses `N`; the caller must provide it. Effort labels are not numeric-budget substitutes.

## Configured vLLM/model capability attestation

`vllm_reasoning_capability.py` records explicit probe results for one already-attested vLLM server/model runtime. Each control is classified independently as:

```text
unsupported
accepted_but_effect_unproven
semantically_attested
malformed_or_ambiguous
```

Protocol acceptance is not semantic proof. A control reaches `semantically_attested` only when the supplied evidence records an accepted exact wire, repeatable observed effect, and the configured activation context required by that control. Positive bounded reasoning additionally requires the numeric `thinking_token_budget` field and exact template activation.

Unsupported, unproven, or ambiguous observations never receive a fallback wire.

## Shared fail-closed rules

- an explicit mode fails when mode control is not attested;
- an explicit mode fails when accepted option values are unknown;
- an explicit mode fails when its value is absent from the exact attested set;
- an explicit token budget fails unless token-budget support is attested;
- omitted reasoning remains omitted;
- `ready` is never recorded as `applied` without exact serialized wire fields;
- backend-native discovery that is missing, malformed, or ambiguous cannot become optimistic support;
- backend wire-field existence alone does not establish model-specific applicability;
- backend-specific capabilities are mutually exclusive on one provider instance.

## Provider cognition capability bridge

`OpenAICompatibleCognitionCapabilityFacts` is the content-free provider-to-cognition bridge.

- generic OpenAI-compatible providers remain reasoning-empty without a backend-specific attestation;
- attached vLLM capability exposes only semantically attested `off`/`bounded` modes;
- attached LM Studio capability exposes current provider-neutral `off` only when the exact loaded model attests `off`;
- no provider capability chooses a calibration default.

Requested reasoning and applied reasoning remain distinct evidence. Actual-model consumers may cite an applied configuration only when the same canonical serializer carried its exact request fields.

## Deferred work

Current provider authority still defers:

- evidence-backed reasoning defaults or calibrated profiles (#1388);
- causal actual-model reasoning ON/OFF comparison where owned by #1386/#1533;
- LM Studio provider-neutral effort-tier semantics beyond current Core vocabulary;
- LM Studio explicit reasoning-token-budget support unless a later exact capability contract proves it.

Exact LM Studio request-time OFF carriage is no longer deferred.
