# Cognitive Runtime

Ordinary-turn cognition is governed by `docs/contracts/cognition-execution-policy.md`.

RelayLM 1.0 is **two-pass first**. The runtime may still expose `single_pass`, `two_pass`, `shadow_two_pass`, and `auto`, but the Core 1.0 release/reference path is `two_pass`.

Model output gains authority only through existing deterministic State/Continuity owners.

## Core 1.0 `two_pass` path

`relaylm.two_pass_turn` implements response-first execution:

```text
originating CognitiveInput
  -> Pass 1 conversation
  -> visible response + Assistant Event
  -> return response-first result
       |
       +--> Pass 2 semantic extraction
              -> ordinary provider message containing compact proposal IR
              -> RelayLM JSON parse + typed candidate construction
              -> StateCandidate[] / ContinuityCandidate[]
              -> revision/Event + State/Continuity snapshot guards
              -> existing deterministic validators
```

The same supplied provider/model object is reused sequentially. Core 1.0 does not require two simultaneously resident online model artifacts.

`CognitionConversationOutput` contains only the visible response.

`CognitionExtractionInput` contains the originating `CognitiveInput` plus the Pass 1 response as lower-authority interpretive context.

`CognitionExtractionOutput` contains only typed proposals after RelayLM parses the compact proposal IR.

Provider-native `response_format`, JSON Schema, grammar or equivalent constrained-output support is not required. The provider transports ordinary message content; RelayLM owns proposal-IR grammar, parsing, exact shape checks, type construction and fail-closed behavior.

## Pass 1

Pass 1 owns user-visible conversation quality and latency-sensitive tempo.

It emits plain natural-language response content with no State/Continuity proposal wrapper.

The response can be delivered independently of Pass 2 completion.

## Pass 2

Pass 2 owns language-dependent semantic extraction for immediate State/Continuity proposals.

The Pass 1 response is interpretive context only. Authority ordering remains:

```text
user / source evidence
  > accepted typed RelayLM State / Context / Continuity
  > assistant response interpretation
```

The assistant response cannot self-certify a user/external fact or become a provenance source.

RelayLM owns deterministic JSON/materialization mechanics after model semantic judgment.

## Ordering

A conversation lock serializes two-pass preparation and Pass 1 generation for one process-local execution runtime.

Pass 2 inference runs without holding the conversation lock, so pending extraction does not itself block the next Pass 1.

A short authority lock covers revision reservation/binding and final stale-check/application.

Final Pass 2 application requires:

```text
origin execution revision is still current
origin User Event is still the latest bound turn
persisted State == origin State snapshot
accepted Continuity == origin Continuity snapshot, when configured
```

A mismatch returns `stale` with no State/Continuity change.

This guard is process-local and does not create a durable State revision or redefine cross-process persistence rules.

Rapid-next-turn and pending-extraction behavior are product-quality/evidence cases owned by #1386.

## Failure

A valid Pass 1 remains a valid conversation if Pass 2 fails.

Pass 2 terminal status is `committed`, `stale`, or `failed`.

Malformed JSON, extra/missing proposal-IR keys, invalid candidate values, provider errors or stale guards cannot partially mutate State/Continuity.

Continuity proposals without the required Continuity runtime fail the extraction before State mutation, preserving cross-channel atomicity at the current boundary.

## Per-pass execution requests

`run_user_turn_two_pass(...)` supports independently resolved Pass 1 and Pass 2 requests.

Core 1.0 requires buffered and streaming two-pass paths to preserve equivalent resolved per-pass semantics. A streaming path that silently drops Pass 1/Pass 2 reasoning or decoding controls is an implementation defect, not a separate policy.

Numeric/default resolution belongs to #1388; exact provider carriage belongs to provider owners.

## `single_pass` compatibility / optimization path

`single_pass` remains implemented but is not the Core 1.0 quality reference.

```text
CognitiveInput
  -> provider.generate / stream_generate
  -> ordinary message containing RelayLM combined cognitive IR
  -> RelayLM JSON parse + exact shape/type construction
  -> CognitiveOutput(response, StateCandidate[], ContinuityCandidate[])
  -> existing deterministic commit boundary
```

The combined IR is:

```text
utterance
state_candidates
continuity_candidates
```

Provider-native structured output is not required here either.

Core 1.0 does not require single-pass prompt tuning to match two-pass quality. A later optimization may compare a single-pass candidate against the qualified two-pass reference when explicit latency/token/resource benefit is being evaluated.

## `shadow_two_pass`

`relaylm.shadow_turn` provides non-authoritative evidence support:

```text
canonical single-pass turn
  -> RelayLM combined-IR parse/type construction
  -> normal response / State / Continuity result

same originating CognitiveInput
+ canonical response
  -> shadow Pass 2 proposal IR
  -> RelayLM parse/type construction
  -> raw ShadowExtractionEvidence
  -> no second State/Continuity mutation
```

Shadow failure cannot invalidate the canonical turn.

Shadow mode is not the Core 1.0 release architecture and must not be mistaken for canonical two-pass execution.

## `auto`

`auto` is unresolved profile policy, not an execution topology identity.

#1388 resolves an evidence-backed profile. #1446 carries that profile through release configuration.

A completed evidence record records the actual resolved mode.

For Core 1.0, `auto` must not silently select an unqualified single-pass optimization.

## Execution evidence identity

`relaylm.cognition_execution_evidence` distinguishes the current RelayLM semantic output contracts:

```text
single_pass
  relaylm_cognitive_output:v1

two_pass Pass 1
  relaylm_conversation_output:v1

two_pass / shadow Pass 2
  relaylm_structured_cognition_output:v1
```

These are RelayLM contract identities and do not imply provider-native response schemas.

#1386 combines them with exact provider/model/reasoning/decoding/runtime identity when producing citable evidence.

## Context / Retrieval / Budget reuse

Canonical two-pass and single-pass consume the existing Identity, State, Context Compiler, optional MEMORY/Event retrieval, accepted Continuity projection and Cognitive Budget owners.

Execution topology does not create alternate relevance or budget semantics.

## Continuity

`relaylm.continuity` and `relaylm.continuity_validation` remain acceptance/lifecycle owners.

- `two_pass` — guarded Pass 2 commit boundary after RelayLM proposal-IR parse/type construction;
- `single_pass` — combined-IR commit boundary after full parse/type construction;
- `shadow_two_pass` — shadow proposals are evidence-only.

## Streaming

Two-pass streaming exposes only Pass 1 response deltas and starts Pass 2 after complete Pass 1 acceptance.

Single-pass streaming remains a compatibility path that exposes only safely decoded `utterance` text and withholds candidate commit until the complete combined IR validates.

## Provider boundary

Current OpenAI-compatible structure transport is ordinary message content:

```text
two-pass Pass 1
  plain natural language

two-pass Pass 2
  compact RelayLM proposal IR
  -> RelayLM parse/type construction

single-pass
  RelayLM combined cognitive IR
  -> RelayLM parse/type construction
```

Provider-native JSON-schema/grammar support may exist as capability truth but is not a mode-level prerequisite for these current cognition paths.

## Capacity / performance

Pass 1 and Pass 2 have separate prompt/output/runtime footprints and must be measured separately.

#1386 owns actual-model quality/capacity/performance evidence. #1388 owns calibrated profile/default selection.

If two-pass performance is problematic, first evaluate two-pass-preserving execution improvements such as streaming, prefix/KV reuse, scheduler/cache tuning, bounded Pass 2 output, lowest sufficient Pass 2 reasoning effort and backend execution-engine tuning.

Do not collapse semantic responsibilities into single-pass solely because it is faster before reference-quality regression is measured.

## Current implementation obligations

Before Core 1.0 release:

1. remove stale provider-native structured-output mode gates;
2. preserve equivalent per-pass request carriage for buffered and streaming two-pass execution;
3. share candidate parsing/type-construction mechanics cleanly between combined and proposal IR paths;
4. test rapid-turn / stale / pending-extraction behavior;
5. let #1386 qualify the two-pass reference before #1388 calibration;
6. wire the qualified two-pass path through #1446 release runtime assembly.

## Deferred

- post-1.0 single-pass optimization against the qualified reference;
- learned/selective extraction routing;
- two concurrently resident online models;
- execution-engine optimizations not yet exposed by current owner contracts.

## Principle

> Two passes are the quality architecture; runtime tuning is the first response to performance cost.
