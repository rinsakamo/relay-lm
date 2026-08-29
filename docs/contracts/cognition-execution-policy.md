# Cognition Execution Policy Contract

Status: current ordinary-turn cognition execution-policy contract for RelayLM 1.0.

Owner: #1533 / `cognitive_turn`.

Current authority is **two-pass first**. Historical topology-winner plans, the retired model-authored `turn_interpretation` scaffold, and prior fixed-axis cognition descriptions are not part of this contract.

## Core invariant

Execution topology and transport never change semantic authority:

```text
model semantic judgment
  -> RelayLM-owned proposal parsing / typed construction
  -> source validation
  -> deterministic State / Continuity validation and lifecycle
  -> RelayLM authority
```

The model proposes meaning. RelayLM owns materialization and acceptance.

## Core 1.0 product role

`CognitionExecutionMode` remains:

```text
two_pass
single_pass
shadow_two_pass
auto
```

- `two_pass` — primary release/reference architecture and the path that must be qualified before release;
- `single_pass` — compatibility / explicit opt-in / later optimization surface, not a Core 1.0 quality gate;
- `shadow_two_pass` — non-authoritative evidence support;
- `auto` — profile resolution owned by #1388 and carried by #1446; it must not silently select an unqualified optimization.

Core 1.0 reuses one already-loaded online model sequentially for Pass 1 and Pass 2. Two simultaneously resident online model artifacts are not required.

## Canonical `two_pass`

### Pass 1 — conversation

Pass 1 receives governed `CognitiveInput` and returns the user-visible natural-language response. It owns conversation quality, Character realization, current-context coherence, language preservation and visible tempo.

Pass 1 does not emit StateCandidate or ContinuityCandidate proposals in `two_pass` mode. It never receives the Pass 2 structured-output control or extraction schema.

### Pass 2 — immediate semantic extraction

Pass 2 receives the originating governed turn plus the accepted Pass 1 response as lower-authority interpretive context and directly projects:

```text
state_candidates
continuity_candidates
```

There is no canonical model-authored intermediate interpretation scaffold or fixed five/six cognition axes.

Pass 2 owns language-dependent semantic judgment needed for correction, negation, supersession, uncertainty, canonical class/key reuse, transient-versus-durable discipline, source/subject attribution and justified no-op behavior.

Current State projection preserves epistemic strength: tentative, hypothetical, guessed, hedged or explicitly self-uncertain meaning must not be silently upgraded to durable State. Deterministic validation remains language-agnostic and is not an NLU repair layer.

Continuity transition semantics are kind-local. Resolving or completing an `unresolved` or `active_task` meaning does not by itself resolve a related `referent`. A referent remains unchanged when work about it completes, new facts about it are learned, or immediate follow-up becomes unlikely; a referent resolve is justified only when the current turn replaces, dismisses, or invalidates the reference target itself. Deterministic validation must not infer these language-dependent conditions after the model has proposed a transition.

RelayLM owns the exact proposal grammar, JSON parsing, exact shape checks, typed candidate construction, origin/turn binding, source validation, State/Continuity lifecycle, persistence and canonical evidence envelopes.

## Pass 2 structured-output transport

`CognitionPassRequest.structured_output_mode` is Pass-2-only and closed to:

```text
plain
native
auto
```

- `plain` — ordinary OpenAI-compatible message content carrying RelayLM-owned direct proposal JSON;
- `native` — provider-native strict structured output constraining the same direct proposal wire;
- `auto` — native only with affirmative structured-output capability evidence, otherwise plain.

Omission preserves the compatibility `plain` path. Explicit `native` fails closed if the upstream provider rejects it and never silently retries as `plain`. Pass 1 cannot carry this control.

Provider-native schema owns only mechanical structure. It does not replace the semantic prompt, RelayLM parsing/type construction, source validation, lifecycle or commit authority.

A provider does **not** need native structured output merely to implement RelayLM cognition: `plain` remains a valid supported transport. Conversely, an evaluation or profile may explicitly select `native` when that exact transport is the condition being measured or qualified.

For the current Stage R vLLM reference, #1901 established materially stronger structural reliability for explicit native Pass 2 than for plain on the tested target class. Stage R may therefore bind its reference condition to `native` without making `native` a universal cognition prerequisite or an automatic Core 1.0 release default. #1388 owns later calibrated profile/default selection and #1446 owns release carriage.

## Authority ordering

For Pass 2 and shadow extraction:

```text
user / source evidence
  > accepted typed RelayLM State / Context / Continuity
  > assistant response interpretation
```

The Pass 1 response may help interpret the turn but cannot independently establish a user fact, preference, goal, experience, external truth, prior event or provenance source.

## Response-first and stale semantics

A valid Pass 1 response is independent of Pass 2 success.

If Pass 2 fails, times out, returns malformed proposals, is rejected or becomes stale:

```text
visible Pass 1 response remains valid
Pass 2 proposals commit nothing
State mutation from failed/stale Pass 2 = none
proposal-driven Continuity mutation = none
original Event evidence remains preserved
failure/staleness remains observable
```

Owner-defined ordinary-turn lifecycle mechanics remain deterministic. A successful Pass 2 applies against the lifecycle revision reserved by that completed conversation and must not advance the Continuity clock a second time.

Every Pass 2 result is bound to its originating Event/revision and origin State/Continuity snapshots. Newer authority makes an older incompatible extraction stale. Rapid-next-turn and pending-extraction behavior remain actual-model quality dimensions under #1386.

## Reasoning and decoding

Pass 1 and Pass 2 may use independently resolved provider-neutral reasoning/decoding requests, but no pass gains greater semantic authority from a larger reasoning budget.

Pass 2 reasoning is an escalation mechanism, not an assumed default. Start from the lowest effective condition proven for the exact backend/model and increase effort only when actual-model evidence demonstrates semantic need.

Transport and reasoning are orthogonal identities: a reasoning escalation must not silently change `plain|native|auto` transport.

## `single_pass`

`single_pass` remains an implemented compatibility/optimization surface. One model generation returns the RelayLM-owned combined cognitive IR:

```text
utterance
state_candidates
continuity_candidates
```

RelayLM parses the combined IR and applies the same deterministic authority boundary. Core 1.0 does not require single-pass quality parity with the qualified two-pass reference.

## `shadow_two_pass`

`shadow_two_pass` is evidence-only. The canonical result follows its normal validation/commit path; shadow Pass 2 output is retained as evidence and cannot perform a second State/Continuity mutation or invalidate the canonical result.

## `auto`

Execution-mode `auto` is unresolved profile policy, not an execution that happened. #1388 owns evidence-backed resolution and #1446 carries the resolved value/provenance. Completed evidence records identify the actual resolved mode.

Structured-output `auto` is separate: it resolves native only from affirmative provider capability evidence and otherwise resolves plain.

## Streaming

Canonical two-pass streaming exposes Pass 1 provider content deltas directly as the visible response. Pass 2 starts only after the complete Pass 1 response is accepted and never emits a second user-visible response.

Buffered and streaming paths must preserve equivalent resolved pass semantics, including reasoning, decoding and structured-output identity.

## Deterministic semantic boundary

RelayLM normalizes structure, not natural language. Do not move correction, negation, uncertainty, temporal meaning, subject attribution or transient/durable interpretation into language-specific regex/keyword/grammar parsers merely to reduce model work.

Conversely, do not ask the model to reproduce IDs, timestamps, provider identity or evidence envelopes that RelayLM can construct deterministically.

## Evidence / capacity identity

Actual-model evidence qualifies an exact execution identity. Material changes to prompt, candidate wire, tokenizer/template, runtime or structured-output transport require fresh evidence or an explicitly scoped owner-approved waiver.

The current Stage R canonical plan must not silently inherit capacity evidence measured against an older prompt/wire/transport identity. Capacity is acquired on the exact current checkout/condition and bound explicitly into screening evidence.

## Ownership

#1533 owns execution topology, Pass 1/Pass 2 responsibilities, response-first/failure/stale semantics, provider-neutral per-pass intent, transport semantics, shadow semantics and the RelayLM cognition IR boundary.

Other owners remain unchanged:

- provider owners — external transport, capability truth and exact applied request carriage;
- #1386 — actual-model quality/qualification evidence;
- #1388 — calibrated profile/default selection;
- #1446 — release configuration/operator carriage;
- #1449 — release integration;
- State / Continuity / Context / Retrieval / Cognitive Budget owners — their existing semantics and deterministic authority.

## Core 1.0 acceptance

This contract is release-ready when the same-loaded-model two-pass path is fully supported; Pass 1 and Pass 2 are independently observable/configurable; Pass 2 directly projects State/Continuity candidates; transport identity is explicit/auditable; Pass 1 survives Pass 2 failure; stale extraction cannot overwrite newer authority; buffered/streaming paths preserve resolved pass semantics; actual-model evaluation qualifies the exact current identity; and no single-pass winner selection or second simultaneously resident online model is required.

## Deferred

- post-1.0 single-pass optimization against the qualified two-pass reference;
- learned/selective extraction routing;
- two simultaneously resident online models;
- semantic StateCandidate/ContinuityCandidate grammar redesign unless separately owned;
- execution-engine optimizations not yet represented by current owner contracts.

## Principle

> Keep the cognitive boundary small: model semantic judgment -> direct proposals -> deterministic RelayLM authority. Qualify that exact two-pass path before optimizing it.
