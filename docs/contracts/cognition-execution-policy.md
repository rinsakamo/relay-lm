# Cognition Execution Policy Contract

Status: current ordinary-turn cognition execution-policy contract for RelayLM 1.0.

Owner: #1533 / `cognitive_turn`.

Current authority is **two-pass first**. Historical topology-winner plans are available in Git/Issue history but are not part of this contract.

## Core invariant

Execution topology never changes semantic authority:

```text
model semantic judgment
  -> RelayLM-owned IR parsing / type construction
  -> existing deterministic State / Continuity validation
  -> RelayLM authority
```

The model proposes meaning. RelayLM owns deterministic materialization and acceptance.

## Core 1.0 product role

`CognitionExecutionMode` remains:

```text
two_pass
single_pass
shadow_two_pass
auto
```

For Core 1.0 these modes have different product roles:

- `two_pass` — primary release/reference architecture and the path that must be qualified before release;
- `single_pass` — compatibility / explicit opt-in / future optimization surface; high-quality single-pass prompt tuning is not a Core 1.0 gate;
- `shadow_two_pass` — non-authoritative evidence support;
- `auto` — profile resolution owned by #1388 and carried by #1446. For Core 1.0 it must not silently select an unqualified single-pass optimization.

A later single-pass optimization must be compared against an already-qualified two-pass reference.

## Canonical `two_pass`

### Pass 1 — conversation

```text
input
  governed CognitiveInput

output
  plain natural-language response
```

Pass 1 owns:

- natural response quality;
- persona / identity continuity;
- current-context coherence;
- language preservation;
- latency-sensitive visible tempo.

Pass 1 does not emit StateCandidate or ContinuityCandidate proposals in `two_pass` mode and is not required to wrap the response in JSON.

### Pass 2 — immediate semantic extraction

Pass 2 receives the originating governed turn plus the accepted Pass 1 response as lower-authority interpretive context.

```text
input
  originating CognitiveInput
  + Pass 1 response

output
  ordinary provider message containing compact RelayLM proposal IR

IR keys
  state_candidates
  continuity_candidates
```

Pass 2 owns semantic judgment needed for:

- StateCandidate / ContinuityCandidate proposals;
- correction / negation / supersession;
- uncertainty / degree preservation where owned semantics exist;
- canonical class/key reuse;
- transient-versus-durable discipline;
- subject/source attribution;
- no-op behavior when no proposal is justified.

RelayLM owns:

- exact proposal-IR grammar;
- JSON parsing;
- exact-key / exact-shape checks;
- typed candidate construction;
- origin/turn binding;
- source validation;
- State / Continuity validation and lifecycle;
- persistence and canonical runtime/evidence envelopes.

The model does not author execution IDs, timestamps, commit status, provider identity, evidence envelopes or other mechanical structure RelayLM can construct deterministically.

## Authority ordering

For Pass 2 and shadow extraction:

```text
user / source evidence
  > accepted typed RelayLM State / Context / Continuity
  > assistant response interpretation
```

The Pass 1 response may help interpret the turn but cannot independently establish a user fact, preference, goal, experience, external truth, prior event or provenance source.

Assistant-to-user factual contamination is a model/product-quality failure even when the returned JSON is syntactically valid.

## Response-first semantics

A valid Pass 1 response is independent of Pass 2 success.

Successful ordinary-turn completion remains allowed to trigger deterministic owner-defined lifecycle mechanics that are not Pass 2 proposals. In particular, when a Continuity runtime is configured, the completed Pass 1 conversation consumes exactly one #1371 Continuity lifecycle revision after the Assistant Event is committed. Due expiry at that revision is turn-clock behavior, not semantic authority granted by Pass 2.

If Pass 2 fails, times out, returns malformed IR, is rejected, or later becomes stale:

```text
visible Pass 1 response remains valid
Pass 2 proposals do not commit
State mutation from failed/stale Pass 2 = none
Pass 2 proposal-driven Continuity mutation = none
successful-turn Continuity lifecycle revision/expiry remains
original Events/evidence remain preserved
failure/staleness remains observable in content-free diagnostics/evidence
```

A successful, still-current Pass 2 may apply its Continuity candidates at the lifecycle revision already reserved by that completed conversation; it must not advance the Continuity clock a second time.

Do not turn post-response extraction failure into a false failure of the already-valid conversation, and do not let extraction failure freeze an owner-defined ordinary-turn lifecycle clock.

## Ordering / stale results

Every Pass 2 result is bound to its originating Event and process-local execution revision.

Pass 2 inference does not hold the conversation or authority lock. A newer turn may advance the execution revision while an older extraction is still pending. Final application requires the originating revision/Event plus the origin State/Continuity snapshots still to match current authority under the short deterministic commit boundary.

For Continuity, the origin snapshot used by the Pass 2 stale guard is the post-conversation lifecycle snapshot for that turn. A newer completed conversation may advance Continuity again and thereby make the older extraction stale. The stale extraction applies no candidates and performs no second lifecycle advance.

A mismatch is `stale` and changes no proposal-owned authority.

Pass 1 for turn N+1 should not ordinarily wait for Pass 2 from turn N merely to preserve visible conversation tempo. Rapid-next-turn and pending-extraction behavior must be evaluated under #1386.

## Same-model 1.0 boundary

Core 1.0 reuses one already-loaded online model sequentially for Pass 1 and Pass 2.

Two simultaneously resident online model artifacts are not required.

Pass 1 and Pass 2 may use independently resolved reasoning/decoding requests, but no pass gains greater semantic authority from a larger reasoning budget.

## Provider structure ownership

Canonical cognition does not require provider-native `response_format`, JSON Schema, grammar or constrained-decoding support.

Current OpenAI-compatible realization is:

```text
two_pass Pass 1
  ordinary provider message
  -> visible response

two_pass Pass 2
  ordinary provider message containing RelayLM proposal IR
  -> RelayLM parse/type construction

single_pass compatibility path
  ordinary provider message containing RelayLM combined cognitive IR
  -> RelayLM parse/type construction
```

Provider-native structured-output capability may remain a truthful provider fact for other uses, but it is not a mode-level prerequisite for the current RelayLM cognition IR paths.

## `single_pass`

`single_pass` remains an implemented compatibility/optimization surface.

One model generation returns the RelayLM-owned combined cognitive IR:

```text
utterance
state_candidates
continuity_candidates
```

RelayLM parses the combined IR, constructs `CognitiveOutput`, and applies the existing deterministic commit boundary.

Core 1.0 does not require single-pass to reach the same quality as the two-pass reference. A later optimization transaction may qualify it only when it demonstrates explicit performance/resource benefit while remaining within accepted conversation/semantic/grounding regression bounds relative to the frozen two-pass reference.

## `shadow_two_pass`

`shadow_two_pass` is evidence-only:

```text
canonical single_pass result
  -> normal validation / commit

same originating input + canonical response
  -> Pass 2 proposal IR
  -> raw shadow evidence only
  -> no second State / Continuity mutation
```

Shadow failure cannot invalidate the canonical result.

It is not a Core 1.0 prerequisite and must not be mistaken for the primary two-pass release path.

## `auto`

`auto` is unresolved profile policy, not an execution that happened.

#1388 owns evidence-backed profile/default resolution. #1446 carries the resolved values and provenance through release configuration.

A completed execution evidence record identifies the actual resolved mode, not `auto`.

For Core 1.0, `auto` must resolve only to a path qualified by current #1386/#1388 evidence. An unqualified single-pass optimization must not become the implicit fallback.

## Per-pass execution controls

Provider-neutral per-pass reasoning/decoding intent is defined in `docs/contracts/cognition-pass-execution.md`.

Pass 2 reasoning is an escalation mechanism, not an assumed default. Start from the lowest effective condition proven by the exact backend/model capability. Increase Pass 2 effort only when #1386 evidence demonstrates semantic need while Pass 1 remains controlled.

## Streaming

Canonical two-pass streaming exposes Pass 1 provider content deltas directly as the visible response stream. Pass 2 starts only after the complete Pass 1 response is accepted and never emits a second user-visible response.

Buffered and streaming two-pass paths must preserve equivalent resolved pass semantics. Streaming must not silently lose Pass 1/Pass 2 reasoning or decoding requests.

Single-pass streaming remains a compatibility path that incrementally exposes only provable `utterance` content while withholding candidate commit until the complete combined IR has been parsed and validated.

## Deterministic semantic boundary

RelayLM normalizes structure, not natural language.

Do not move correction, negation, uncertainty, temporal meaning, subject attribution, transient/durable interpretation or similar multilingual semantics into language-specific regex/keyword/grammar parsers merely to reduce model work.

Conversely, do not ask the model to reproduce metadata, IDs or envelopes that deterministic RelayLM code can construct without language understanding.

## Performance policy

A performance problem in two-pass execution is not by itself a reason to collapse semantic responsibilities.

Before considering one-pass as a release optimization, evaluate two-pass-preserving improvements such as:

- response-first streaming;
- prompt-prefix / KV-cache reuse where the backend can prove it;
- scheduler / batching / cache tuning;
- bounded Pass 2 output;
- lowest sufficient Pass 2 reasoning effort;
- background / lower-priority Pass 2 execution;
- backend/runtime execution-engine tuning.

Performance evidence belongs to #1386; calibrated values/profile choices belong to #1388.

## Current implementation obligations

The Core 1.0 two-pass path must reconcile all current surfaces so that:

1. no cognition mode falsely requires provider-native structured output when its current RelayLM-owned IR path does not;
2. buffered and streaming two-pass paths carry equivalent per-pass resolved requests;
3. single-pass combined IR and Pass 2 proposal IR reuse shared candidate parsing/type-construction mechanics rather than making Pass 2 depend on a synthetic single-pass wrapper;
4. rapid-turn / stale / pending-extraction behavior is deterministically tested;
5. #1386 qualifies two-pass first instead of forcing topology winner-selection.

## Ownership

#1533 owns:

- execution topology and product role;
- Pass 1 / Pass 2 responsibilities;
- response-first / failure / stale semantics;
- provider-neutral per-pass intent;
- execution-topology identity;
- shadow semantics;
- RelayLM cognition IR ownership boundary.

Other owners remain unchanged:

- provider owners — external transport, capability truth and exact applied request carriage;
- #1386 — actual-model quality/evidence;
- #1388 — calibrated two-pass profile/defaults;
- #1446 — release config/operator carriage;
- #1449 — release integration;
- State / Continuity / Context / Retrieval / Cognitive Budget owners — their existing semantics and deterministic authority.

## Core 1.0 acceptance

This contract is release-ready when the same-loaded-model two-pass path is fully supported; Pass 1 and Pass 2 are independently observable and configurable; Pass 1 survives Pass 2 failure; stale extraction cannot overwrite newer authority; provider-native structured output is not falsely required; streaming preserves the same pass semantics; and no single-pass quality optimization is required to complete Core 1.0.

## Deferred

- post-1.0 single-pass optimization against the qualified two-pass reference;
- learned/selective extraction routing;
- two simultaneously resident online models;
- semantic StateCandidate/ContinuityCandidate grammar redesign unless separately owned;
- execution-engine optimizations not yet represented by current owner contracts.

## Principle

> First establish quality with separated conversation and semantic judgment. Optimize execution only after the reference behavior is known.