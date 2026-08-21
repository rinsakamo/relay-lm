# Cognitive Runtime

Ordinary-turn cognition is governed by `docs/contracts/cognition-execution-policy.md`.

RelayLM 1.0 recognizes `single_pass`, `two_pass`, `shadow_two_pass`, and `auto`. Execution topology may vary, but model proposals gain authority only through existing deterministic State/Continuity owners.

## `single_pass`

The existing ordinary-turn APIs retain the one-generation baseline:

```text
CognitiveInput
  -> provider.generate / stream_generate
  -> plain combined cognitive IR content
  -> RelayLM JSON parse + exact shape/type construction
  -> CognitiveOutput(response, StateCandidate[], ContinuityCandidate[])
  -> existing deterministic commit boundary
```

A complete valid output is required before the Assistant Event, State validation, and Continuity validation commit. The OpenAI-compatible realization no longer requires provider-native `response_format`, JSON-schema grammar, or equivalent structured-output enforcement. The provider transports ordinary message content containing the RelayLM-owned combined cognitive IR; RelayLM owns exact top-level/candidate shape checks, typed candidate construction, and fail-closed behavior.

## `two_pass`

COGP implements an explicit response-first runtime in `relaylm.two_pass_turn`:

```text
originating CognitiveInput
  -> Pass 1 conversation
  -> visible response + Assistant Event
  -> return response-first result
       |
       +--> background Pass 2 extraction
              -> ordinary provider message containing compact proposal IR
              -> RelayLM JSON parse + typed candidate construction
              -> StateCandidate[] / ContinuityCandidate[]
              -> revision/Event + State/Continuity snapshot guards
              -> existing deterministic validators
```

The same supplied provider object is used sequentially. `CognitionConversationOutput` contains only the response. `CognitionExtractionInput` contains the originating `CognitiveInput` plus the Pass 1 response as lower-authority interpretive context. `CognitionExtractionOutput` contains only typed proposals after RelayLM has parsed the compact proposal IR.

Canonical Pass 2 does not require provider-native `response_format`, JSON-schema grammar, or equivalent structured-output support. The provider transports plain message content. RelayLM owns the proposal-IR grammar, exact top-level shape, JSON parsing, candidate type construction, and fail-closed behavior before deterministic State/Continuity validation.

`run_user_turn_two_pass(...)` and `run_user_turn_two_pass_streaming(...)` require an explicit process-local `CognitionExecutionRuntime`. They do not silently replace the existing single-pass APIs or select a release default.

### Ordering

A conversation lock serializes two-pass preparation and Pass 1 generation for one execution runtime. Pass 2 inference runs after that lock is released, so pending extraction does not itself block the next Pass 1.

A separate short authority lock covers new-turn revision reservation/binding and the final stale-check/validation/application boundary. A newer turn advances the process-local revision before preparing its input. Final Pass 2 application requires:

```text
origin revision is still latest
origin User Event is still latest bound turn
persisted State == origin State snapshot
accepted Continuity == origin Continuity snapshot, when configured
```

Any mismatch returns `stale` with no State/Continuity change. This guard is process-local and does not create a durable State revision or redefine cross-process storage concurrency.

### Failure

A valid Pass 1 remains a valid conversation if Pass 2 later fails. Pass 2 status is `committed`, `stale`, or `failed`. Continuity proposals without an explicit Continuity runtime fail the extraction before State change, preventing a partial cross-channel result.

Malformed JSON, extra top-level proposal-IR fields, or invalid candidate values fail closed inside RelayLM. Such a failure changes neither State nor Continuity and does not invalidate the already-delivered Pass 1 response.

## `shadow_two_pass`

COGP implements non-authoritative shadow execution in `relaylm.shadow_turn`:

```text
canonical single-pass turn
  -> plain combined cognitive IR
  -> RelayLM parse/type construction
  -> normal response / State / Continuity result

capture the same originating CognitiveInput
+ canonical response
  -> shadow Pass 2 plain extraction message
  -> RelayLM proposal-IR parse/type construction
  -> raw ShadowExtractionEvidence
  -> no State/Continuity acceptance or change
```

The explicit APIs are:

```text
run_user_turn_shadow_two_pass(...)
run_user_turn_shadow_two_pass_streaming(...)
```

They call the existing `run_user_turn` / `run_user_turn_streaming` through a transparent input-capturing provider wrapper. Therefore canonical single-pass Context/Retrieval/Budget preparation and deterministic commit semantics remain owned by the existing Turn path rather than being copied into shadow runtime code.

After canonical completion, shadow extraction uses the original pre-turn `CognitiveInput` plus the canonical response. Shadow output is raw proposal evidence only. It does not call State or Continuity validation for the purpose of changing accepted authority and does not advance Continuity lifecycle.

The canonical side of `shadow_two_pass` uses the same RelayLM-owned combined-IR parsing boundary as ordinary `single_pass`; shadow extraction uses the RelayLM-owned proposal-IR parser shared with canonical `two_pass`.

A shadow provider or RelayLM proposal-IR parsing failure becomes bounded `shadow_pass2_failed`; the already-completed canonical turn is unaffected.

Shadow extraction may complete after later conversation activity because it has no canonical write path. Its evidence remains bound to the originating User Event ID.

## Execution evidence identity

`relaylm.cognition_execution_evidence` defines provider-neutral topology identity for `single_pass`, `two_pass`, and `shadow_two_pass` plus the RelayLM semantic output-contract identities used by each topology. `auto` is not an executed identity.

`relaylm_cognitive_output:v1` identifies the RelayLM-owned combined cognitive IR and parse/type-construction boundary. `relaylm_structured_cognition_output:v1` identifies the RelayLM-owned Pass 2 proposal IR and parse/type-construction boundary. Neither identity requires a provider-native JSON-schema request field.

The identity deliberately does not duplicate exact provider/model/reasoning/decoding/runtime identity. #1386 combines those separate owners when constructing citable actual-model evidence.

See `docs/contracts/cognition-execution-evidence.md`.

## Context / Retrieval / Budget reuse

Canonical `single_pass` and `two_pass` both consume the existing Character/Identity, State, Context Compiler, optional MEMORY/Event retrieval, accepted Continuity projection, and Cognitive Budget owners.

`shadow_two_pass` uses the canonical single-pass Turn path directly and captures the exact `CognitiveInput` supplied to that canonical model call. No shadow-specific relevance or budget policy exists.

## Continuity

`relaylm.continuity` and `relaylm.continuity_validation` remain the acceptance/lifecycle owners.

- `single_pass`: existing common commit boundary after RelayLM combined-IR parsing/type construction.
- `two_pass`: guarded Pass 2 commit boundary after RelayLM proposal-IR parsing/type construction.
- `shadow_two_pass`: only canonical single-pass proposals may affect accepted Continuity; shadow proposals are evidence-only.

## Streaming

Two-pass streaming exposes only Pass 1 response deltas and schedules Pass 2 after complete Pass 1 acceptance.

Single-pass streaming incrementally decodes the visible `utterance` from the plain combined IR stream, then RelayLM parses and validates the complete IR before commit. Shadow streaming uses that canonical single-pass streaming path. Shadow extraction starts only after the complete canonical output has committed and never emits a second visible response.

## Provider boundary

The OpenAI-compatible adapter inherits model/endpoint/decoding and provider-owned reasoning configuration across cognition modes. Structure ownership is topology-specific but RelayLM-owned in both canonical forms:

```text
canonical single_pass
  -> ordinary provider message containing combined cognitive IR
  -> RelayLM relaylm_cognitive_output:v1 parse/type construction

canonical or shadow Pass 2
  -> ordinary provider message containing proposal IR
  -> RelayLM relaylm_structured_cognition_output:v1 parse/type construction
```

Provider-native JSON-schema/grammar support may exist as a backend capability, but it is not the owner or prerequisite of either RelayLM cognition contract. Provider capability truth and exact applied reasoning/decoding request configuration remain provider-owned.

## Capacity / evidence consequence

Both model-facing structure wires have changed from the earlier provider-native single-pass / Pass-2 schema-carriage implementations. Prior exact serialized-input footprints remain historical evidence for their exact old wires. #1386 must reacquire current fixed prompt/wire footprint evidence before revised topology screening cites capacity assumptions. This runtime change itself selects no context window, output reserve, reasoning budget, profile, or default.

## Deferred

#1386 owns fresh actual-model execution-topology/capacity evidence against these exact wires. #1388 owns calibrated selection, #1446 owns release-config integration, and #1449 owns final release reconciliation.
