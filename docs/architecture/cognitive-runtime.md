# Cognitive Runtime

Ordinary-turn cognition is governed by `docs/contracts/cognition-execution-policy.md`.

RelayLM 1.0 is **two-pass first**. The runtime may still expose `single_pass`, `two_pass`, `shadow_two_pass`, and `auto`, but the Core 1.0 release/reference path is `two_pass`.

Model output gains authority only through existing deterministic State/Continuity owners.

## Core 1.0 `two_pass` path

`relaylm.two_pass_turn` implements response-first execution:

```text
originating CognitiveInput
  -> shared canonical cognitive prefix
  -> Pass 1 conversation suffix
  -> visible response + Assistant Event
  -> return response-first result
       |
       +--> same canonical cognitive prefix
            + Pass 2 cognition/extraction suffix
              -> semantic State/Continuity guidance
              -> direct state_candidates / continuity_candidates
              -> RelayLM exact top-level validation + typed candidate construction
              -> revision/Event + State/Continuity snapshot guards
              -> existing deterministic validators
```

The same supplied provider/model object is reused sequentially. Core 1.0 does not require two simultaneously resident online model artifacts.

The OpenAI-compatible two-pass adapter serializes the same common system instruction and the same canonical `CognitiveInput` prefix for both passes. The requests diverge only after the explicit `<PASS>` boundary. Backends may reuse that token-identical prefix when their cache semantics support it; RelayLM does not infer cache reuse merely from semantic equivalence.

`CognitionConversationOutput` contains only the visible response.

`CognitionExtractionInput` contains the originating `CognitiveInput` plus the Pass 1 response as lower-authority interpretive context.

`CognitionExtractionOutput` contains only typed State/Continuity proposals. Pass 2 does not expose or require an intermediate model-authored interpretation scaffold.

Pass 2 extraction transport is selectable. `plain` carries the direct candidate JSON as ordinary provider message content. `native` sends provider-native strict JSON Schema for the same direct wire. `auto` uses native only with affirmative capability evidence and otherwise remains plain. RelayLM owns JSON parsing, exact top-level checks, candidate type construction, source validation and fail-closed authority mechanics in every transport mode.

## Pass 1

Pass 1 owns user-visible conversation quality and latency-sensitive tempo.

Its canonical two-pass suffix is intentionally minimal:

```text
CONVERSATION

Respond as this character.
```

Pass 1 emits the user-visible character response directly, with no State/Continuity proposal wrapper. RelayLM does not impose a separate visible response format, so a legitimate user request for JSON, Markdown, code or another representation is not contradicted by a blanket Pass 1 output ban.

The response can be delivered independently of Pass 2 completion.

## Pass 2

Pass 2 owns language-dependent subjective cognition and semantic extraction for immediate State/Continuity proposals.

The model projects directly to:

```text
state_candidates
continuity_candidates
```

There is no canonical six-field `turn_interpretation` output. Language-dependent interpretation happens inside generation under the shared Identity/State/context and semantic projection guidance rather than being materialized as a separate parse-and-discard model artifact.

A State proposal still requires an adequately grounded, sufficiently resolved and meaningful durable change in accepted current understanding. Continuity remains bounded cross-turn meaning whose carriage materially improves coherence. Ambiguity or incomplete evidence does not mechanically require Continuity.

The Pass 1 response is interpretive context only. Authority ordering remains:

```text
user / source evidence
  > accepted typed RelayLM State / Context / Continuity
  > assistant response interpretation
```

The assistant response cannot self-certify a user/external fact or become a provenance source merely because it was generated in Pass 1.

The current contract preserves existing model-authored candidate `sources`, Event-ID rules, source validation, State/Continuity validation and commit semantics. Deterministic source reconstruction is not part of this transaction.

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

Malformed JSON, extra/missing direct-IR keys, invalid candidate values, provider errors or stale guards cannot partially mutate State/Continuity.

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

Provider-native structured output is not required here.

Core 1.0 does not require single-pass prompt tuning to match two-pass quality. A later optimization may compare a single-pass candidate against the qualified two-pass reference when explicit latency/token/resource benefit is being evaluated.

## `shadow_two_pass`

`relaylm.shadow_turn` provides non-authoritative evidence support:

```text
canonical single-pass turn
  -> RelayLM combined-IR parse/type construction
  -> normal response / State / Continuity result

same originating CognitiveInput
+ canonical response
  -> shadow Pass 2 direct proposal IR
  -> RelayLM exact top-level validation + candidate parse/type construction
  -> raw ShadowExtractionEvidence containing typed proposals
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

These identities describe the typed RelayLM semantic outputs, not the complete provider prompt/wire grammar. The direct Pass 2 wire changes the prompt/wire identity while `CognitionExtractionOutput` remains the same typed State/Continuity proposal output. Actual-model evidence must therefore also bind the exact current prompt/IR/parser repository identity rather than treating the semantic-output label alone as sufficient.

These are RelayLM contract identities and do not imply one mandatory provider-native transport.

#1386 combines them with exact provider/model/reasoning/decoding/runtime identity when producing citable evidence.

## Context / Retrieval / Budget reuse

Canonical two-pass and single-pass consume the existing Identity, State, Context Compiler, optional MEMORY/Event retrieval, accepted Continuity projection and Cognitive Budget owners.

Execution topology does not create alternate relevance or budget semantics.

## Continuity

`relaylm.continuity` and `relaylm.continuity_validation` remain acceptance/lifecycle owners.

- `two_pass` — guarded Pass 2 commit boundary after RelayLM direct proposal parse and candidate type construction;
- `single_pass` — combined-IR commit boundary after full parse/type construction;
- `shadow_two_pass` — shadow proposals are evidence-only.

## Streaming

Two-pass streaming exposes only Pass 1 response deltas and starts Pass 2 after complete Pass 1 acceptance.

Single-pass streaming remains a compatibility path that exposes only safely decoded `utterance` text and withholds candidate commit until the complete combined IR validates.

## Provider boundary

Current OpenAI-compatible structure transport is selectable for Pass 2:

```text
two-pass Pass 1
  direct user-visible character response

two-pass Pass 2
  semantic guidance + direct proposal IR
  -> plain ordinary message JSON
     OR native strict response_format=json_schema
  -> RelayLM candidate parse/type/source validation

single-pass
  RelayLM combined cognitive IR
  -> RelayLM parse/type construction
```

Provider-native JSON-schema/grammar support is not a topology-level prerequisite because the plain Pass 2 path remains available.

## Capacity / performance

Pass 1 and Pass 2 have separate output/runtime footprints but intentionally share the same token-identical cognitive prefix through the pass boundary. Actual prefix-cache reuse remains backend-dependent and must be measured rather than assumed.

Pass 2 adds its compact direct-proposal suffix, so prompt tokens, completion tokens, latency and reasoning tokens must be qualified against the existing scenario set. The completed #1898 ablation selected direct candidates over the previous six-field scaffold; that experiment is evidence for this wire simplification, not a replacement for release qualification.

#1386 owns actual-model quality/capacity/performance evidence. #1388 owns calibrated profile/default selection.

If two-pass performance is problematic, first evaluate two-pass-preserving execution improvements such as streaming, prefix/KV reuse, scheduler/cache tuning, bounded Pass 2 output, lowest sufficient Pass 2 reasoning effort and backend execution-engine tuning.

Do not collapse semantic responsibilities into single-pass solely because it is faster before reference-quality regression is measured.

## Current implementation obligations

Before Core 1.0 release:

1. preserve equivalent per-pass request carriage for buffered and streaming two-pass execution;
2. share candidate parsing/type-construction mechanics cleanly between combined and proposal IR paths;
3. test rapid-turn / stale / pending-extraction behavior;
4. let #1386 qualify the two-pass reference before #1388 calibration;
5. wire the qualified two-pass path through #1446 release runtime assembly.

## Deferred

- post-1.0 single-pass optimization against the qualified reference;
- learned/selective extraction routing;
- two concurrently resident online models;
- execution-engine optimizations not yet exposed by current owner contracts.

## Principle

> Two passes are the quality architecture; Pass 2 projects semantic proposals directly and RelayLM keeps the authority boundary.
