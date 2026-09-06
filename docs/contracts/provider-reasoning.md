# OpenAI-compatible provider reasoning control contract

Status: #1545 current provider-owned reasoning contract for RelayLM v1, including LM Studio configured-runtime capability attestation and exact request-time OFF carriage, plus vLLM configured-runtime capability and exact realization.

This contract defines the deterministic provider boundary for explicit reasoning controls, backend-specific capability truth, and exact backend request spelling. It does not choose cognition policy, per-pass defaults, numeric reasoning budgets, or calibration values.

## Ownership

```text
calibration/profile/config
  -> fully resolved provider-neutral cognition request
  -> provider reasoning request/capability contract
  -> backend-specific deterministic realization
  -> exact request fields
```

`auto` is not a provider realization value. It must resolve before this boundary. The provider does not decide that Pass 1 or Pass 2 deserves a particular reasoning mode or budget.

## Capability truth

`OpenAICompatibleReasoningCapabilities` distinguishes unsupported controls, controls whose exact accepted values are unknown, and controls whose exact accepted values are attested. Unknown capability is never permission to send an explicit request. Explicit reasoning-token budget support is represented independently.

The generic OpenAI-compatible contract never infers reasoning capability from model names, output style, or backend reputation.

## Explicit request and application

`OpenAICompatibleReasoningRequest` contains only explicit caller intent: a provider-neutral `mode` and optional explicit `token_budget`. The empty request means RelayLM adds no reasoning control.

Capability preflight and application are distinct. `ready` means only that the attested capability can represent the request. `OpenAICompatibleReasoningApplicationStatus.APPLIED` requires both the semantic request and non-empty exact wire fields produced by the same realization path used for the network request.

## LM Studio configured-runtime capability attestation

LM Studio-native capability discovery is isolated in `lm_studio_reasoning.py`; it is not assumed for generic OpenAI-compatible providers.

`LMStudioReasoningCapabilityAttestation` consumes native `/api/v1/models` data and binds capability to:

```text
exact request_model
exact unambiguous loaded_instance_id
reasoning.allowed_options
reasoning.default
```

The native metadata vocabulary currently accepted by the attestation is:

```text
off | on | low | medium | high
```

This native vocabulary is capability metadata, not the OpenAI-compatible Chat Completions wire vocabulary. The native default is recorded only as an observed runtime fact; it never becomes an implicit RelayLM request value.

Fail-closed rules include missing reasoning metadata, ambiguous model or loaded-instance identity, malformed or duplicate options, unknown options, and a default absent from the attested option set. Native model metadata does not attest an explicit reasoning-token budget, so current LM Studio `token_budget_supported` remains false.

## LM Studio exact Chat Completions OFF realization

Current Core requires only provider-neutral reasoning OFF. For an exact loaded LM Studio model whose native metadata attests the `off` capability, the production OpenAI-compatible serializer realizes that semantic request as:

```text
RelayLM semantic mode: off
LM Studio native capability: off is allowed
OpenAI-compatible wire: reasoning_effort: none
```

The native toggle value `off` is therefore not copied literally into the Chat Completions request. The current realizer deliberately supports only this OFF mapping. Native `on`, `low`, `medium`, and `high` metadata do not create current RelayLM wire support, and explicit reasoning-token budgets remain unsupported.

The canonical single-pass request builder, two-pass Pass 1 builder, streaming Pass 1 builder, two-pass Pass 2 builder, and off-turn Crystallization builder consume the same backend reasoning dispatcher. For current LM Studio OFF they serialize:

```json
{"reasoning_effort":"none"}
```

They do not add `reasoning_tokens`, `thinking_token_budget`, or vLLM chat-template controls.

Current LM Studio Stage R and observed-condition Crystallization obtain native model metadata, bind the exact loaded instance, require native `off` capability, and attach that attestation to the production serializer. Evidence keeps three facts separate:

```text
provider-neutral intent     = off
live LM Studio default      = separately observed, for example on
actual Chat Completions wire = reasoning_effort: none
```

A live default of `on` therefore does not satisfy OFF by omission; the request must still carry the explicit OFF realization.

## Current cognition capability bridge

`OpenAICompatibleCognitionCapabilityFacts` is the content-free provider-to-cognition bridge.

- generic OpenAI-compatible providers remain reasoning-empty without backend-specific attestation;
- attached LM Studio capability exposes provider-neutral `off` only when native `off` is attested;
- LM Studio `bounded(N)` remains unsupported because no explicit reasoning-token budget is attested;
- current runtime assembly accepts explicit LM Studio `reasoning_mode=off` only;
- no provider capability chooses a calibration default.

Backend-specific reasoning attestations are mutually exclusive on one provider instance.

## vLLM exact reasoning realization

vLLM remains a separate provider dialect. Its current exact realization is unchanged:

```text
RelayLM off
  -> reasoning_effort: none
  -> no conflicting template thinking activation

RelayLM bounded(N)
  -> thinking_token_budget: N
  -> chat_template_kwargs: { enable_thinking: true }
```

Configured-runtime vLLM capability evidence classifies each control independently as `unsupported`, `accepted_but_effect_unproven`, `semantically_attested`, or `malformed_or_ambiguous`. Protocol acceptance alone is not semantic proof, and unsupported or ambiguous observations never receive a fallback wire.

## Shared fail-closed rules

- explicit mode without exact capability fails before generation;
- unknown accepted values do not authorize a request;
- explicit token budget requires independently attested budget support;
- omitted reasoning remains omitted;
- `ready` is never recorded as `applied` without exact serialized fields;
- backend-native metadata and backend wire vocabulary are not silently conflated;
- model/runtime defaults are not treated as applied per-request controls.

## Deferred work

Current provider authority still defers:

- evidence-backed reasoning defaults or calibrated profiles (#1388);
- causal actual-model reasoning ON/OFF comparison where owned by #1386/#1533;
- LM Studio provider-neutral ON or effort-tier semantics;
- LM Studio explicit reasoning-token-budget support unless a later exact capability contract proves it.

Exact LM Studio request-time semantic OFF carriage as `reasoning_effort: none` is current behavior, not deferred work.
