# Cognitive Runtime

Ordinary-turn cognition is governed by `docs/contracts/cognition-execution-policy.md`.

RelayLM 1.0 recognizes `single_pass`, `two_pass`, `shadow_two_pass`, and `auto`. Execution topology may vary, but model proposals gain authority only through existing deterministic State/Continuity owners.

## `single_pass`

The existing ordinary-turn APIs retain the one-generation baseline:

```text
CognitiveInput
  -> provider.generate / stream_generate
  -> CognitiveOutput(response, StateCandidate[], ContinuityCandidate[])
  -> existing deterministic commit boundary
```

A complete valid output is required before the Assistant Event, State validation, and Continuity validation commit.

## `two_pass`

COGP3 implements an explicit response-first runtime in `relaylm.two_pass_turn`:

```text
originating CognitiveInput
  -> Pass 1 conversation
  -> visible response + Assistant Event
  -> return response-first result
       |
       +--> background Pass 2 extraction
              -> StateCandidate[] / ContinuityCandidate[]
              -> revision/Event + State/Continuity snapshot guards
              -> existing deterministic validators
```

The same supplied provider object is used sequentially. `CognitionConversationOutput` contains only the response. `CognitionExtractionInput` contains the originating `CognitiveInput` plus the Pass 1 response as lower-authority interpretive context. `CognitionExtractionOutput` contains only proposals.

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

## `shadow_two_pass`

COGP4 implements non-authoritative shadow execution in `relaylm.shadow_turn`:

```text
canonical single-pass turn
  -> normal response / State / Continuity result

capture the same originating CognitiveInput
+ canonical response
  -> shadow Pass 2 extraction task
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

A shadow provider failure becomes bounded `shadow_pass2_failed`; the already-completed canonical turn is unaffected.

Shadow extraction may complete after later conversation activity because it has no canonical write path. Its evidence remains bound to the originating User Event ID.

## Execution evidence identity

`relaylm.cognition_execution_evidence` defines provider-neutral topology identity for `single_pass`, `two_pass`, and `shadow_two_pass` plus the RelayLM semantic output-contract identities used by each topology. `auto` is not an executed identity.

The identity deliberately does not duplicate exact provider/model/reasoning/decoding/runtime identity. #1386 combines those separate owners when constructing citable actual-model evidence.

See `docs/contracts/cognition-execution-evidence.md`.

## Context / Retrieval / Budget reuse

Canonical `single_pass` and `two_pass` both consume the existing Character/Identity, State, Context Compiler, optional MEMORY/Event retrieval, accepted Continuity projection, and Cognitive Budget owners.

`shadow_two_pass` uses the canonical single-pass Turn path directly and captures the exact `CognitiveInput` supplied to that canonical model call. No shadow-specific relevance or budget policy exists.

## Continuity

`relaylm.continuity` and `relaylm.continuity_validation` remain the acceptance/lifecycle owners.

- `single_pass`: existing common commit boundary.
- `two_pass`: guarded Pass 2 commit boundary.
- `shadow_two_pass`: only canonical single-pass proposals may affect accepted Continuity; shadow proposals are evidence-only.

## Streaming

Two-pass streaming exposes only Pass 1 response deltas and schedules Pass 2 after complete Pass 1 acceptance.

Shadow streaming uses the existing canonical single-pass streaming path. Shadow extraction starts only after the complete canonical output has committed and never emits a second visible response.

## Provider boundary

The OpenAI-compatible two-pass extension inherits the canonical adapter client/model/endpoint/decoding configuration. Its extraction schema reuses the canonical State/Continuity candidate schemas and parser, so no provider-specific candidate grammar is introduced.

That same object can perform canonical `relaylm_cognitive_output` followed by shadow `relaylm_structured_cognition_output`. This proves topology reuse; provider capability truth and exact applied request configuration remain provider-owned.

## Deferred

COGP5 owns #1386 actual-model execution-topology carriage and controlled A/B/C evidence. COGP6/#1388 owns calibrated selection, COGP7/#1446 owns release-config integration, and COGP8/#1449 owns final release reconciliation.
