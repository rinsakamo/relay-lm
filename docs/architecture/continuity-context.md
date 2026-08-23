# Continuity Context

> **Status:** accepted semantic architecture tracked by #1371. K1 typed boundaries are implemented in `relaylm.continuity`; K2 deterministic acceptance/lifecycle is implemented in `relaylm.continuity_validation`; K3 ordinary-turn orchestration is implemented across `relaylm.cognitive`, `relaylm.turn`, `relaylm.two_pass_turn`, and the explicit app/router runtime carriage.

## Purpose

RelayLM needs a bounded way to retain short-term semantic continuity that should survive beyond pure recent-message residency but should not become durable character truth merely because it matters for the next turn.

The accepted concept is **Continuity Context**:

> **Continuity Context is bounded, non-durable semantic continuity retained across ordinary turns after deterministic acceptance.**

It is intentionally smaller than a general intent subsystem and does not revive legacy `RelayINT` / `RelayCTX` machinery.

## Distinction from current Working Context

The current v1 **Working Context** keeps its existing meaning: current-turn conversational residency selected by the Context Compiler from RelayLM-owned recent message Events.

Continuity Context is different:

```text
Continuity Context
  accepted temporary semantic continuity retained across turns

Working Context
  current-turn selected recent conversational residency
```

Therefore:

```text
Continuity Context != Working Context
Continuity Context != Canonical State
Continuity Context != Event Journal
Continuity Context != crystallized MEMORY
```

The Context Compiler consumes already-accepted Continuity Context when assembling current cognition. Current residency does not own production or acceptance of continuity semantics.

## Ordinary-turn return path

Continuity semantics are independent of cognition topology. Current Core 1.0 cognition is two-pass first, while single-pass remains a compatibility/optimization surface:

```text
single_pass
  CognitiveInput
    -> combined response + ContinuityCandidate[]

two_pass
  CognitiveInput
    -> Pass 1 visible response
    -> Pass 2 ContinuityCandidate[]

both
  -> RelayLM deterministic continuity validation/lifecycle
  -> Continuity Context
  -> later-turn Context Compiler input
```

`ContinuityCandidate` is a proposal only. Model output is never accepted continuity merely because the model emitted it.

This mirrors the authority shape of `StateCandidate -> deterministic validation -> Canonical State` without making continuity into Canonical State.

The provider-independent cognitive boundary may carry continuity proposals through the currently selected cognition topology. Single-pass consumes proposals from its completed combined cognitive output. Two-pass consumes proposals only from a successful, current Pass 2 extraction after the visible Pass 1 response has already completed. Cognition topology does not move continuity acceptance semantics into a provider adapter.

Provider-specific structured-output grammar is a separate adapter concern. Continuity semantics do not require every adapter to share one wire representation.

## Canonical names

The initial semantic vocabulary is:

- `ContinuityCandidate` — model-produced proposal for bounded short-term continuity;
- `ContinuityItem` — deterministically accepted continuity record;
- `Continuity Context` — the bounded non-durable authority containing accepted items.

Initial item kinds are:

- `referent`;
- `unresolved`;
- `active_task`.

Additional kinds require separately bounded semantics. Different meanings do not imply separate machinery by default.

## Typed boundary — K1

`src/relaylm/continuity.py` is the typed semantic owner.

A `ContinuityCandidate` carries:

- one of the three bounded initial kinds;
- a non-empty lifecycle `key`;
- an explicit `set` or `resolve` operation;
- Event source IDs;
- an explicit epistemic role: `user_assertion`, `assistant_inference`, or `assistant_commitment`;
- a semantic value only for `set` proposals.

Constructor validity does not grant acceptance authority.

A `ContinuityItem` preserves kind, key, detached deeply immutable semantic value, Event sources, epistemic role, and an explicit revision-bounded lifetime (`accepted_revision` / `expires_revision`).

`ContinuityContext` is an immutable container with an explicit positive `max_items`, a monotonic non-negative `revision`, and a tuple of non-expired `ContinuityItem` values. It has no default runtime capacity policy and no persistence contract. The explicit bound is a semantic container boundary, not a runtime/default budgeting decision.

## Deterministic acceptance and lifecycle — K2

`src/relaylm/continuity_validation.py` is the deterministic acceptance/lifecycle owner.

One successfully completed ordinary turn consumes exactly one Continuity revision. The semantic order for that turn is fixed:

1. advance to the next revision;
2. expire items whose `expires_revision` has been reached;
3. validate and apply any candidates belonging to that same turn revision;
4. if capacity is exceeded, evict oldest accepted items deterministically.

`apply_continuity_candidates(...)` remains the composed K2 operation for paths where turn completion and candidate availability coincide. It performs the lifecycle advance and then candidate application at the resulting revision.

Response-first two-pass execution may realize the same K2 semantics in two deterministic steps without creating a second continuity policy:

- `advance_continuity_lifecycle(...)` reserves the completed turn revision and performs expiry;
- `apply_continuity_candidates_at_current_revision(...)` applies a later, still-current Pass 2 candidate set at that already-reserved revision without advancing again.

The caller must provide a positive `lifetime_revisions` value. K2 does not choose a default TTL or runtime budget. Accepted items expire at `accepted_revision + lifetime_revisions` unless superseded, resolved, or evicted earlier.

Candidate acceptance requires known Event source IDs. A caller may additionally require intersection with current-evidence Event IDs. A `user_assertion` candidate must include at least one user-authored source Event. A `set` value must be JSON-serializable with non-finite numeric values rejected. These checks preserve provenance and reject malformed authority rather than inferring missing meaning.

For each lifecycle `key`, transition semantics are:

- no existing item + valid `set` -> `admit`;
- existing item + exact same kind/value/deduplicated sources/epistemic role -> `duplicate` noop, with no lifetime refresh;
- existing item + valid changed `set` on the same key -> `supersede`, replacing the prior item directly;
- valid `resolve` + no existing key -> `not_found` noop;
- valid `resolve` + existing same-kind key -> `resolve`, removing the item;
- valid `resolve` + existing different-kind key -> reject `kind_mismatch`.

Accepted item IDs are deterministic from the owning turn revision and candidate order. Superseded items are newly accepted for lifecycle age. Capacity eviction chooses the oldest `accepted_revision`, using existing tuple order as deterministic tie-breaker.

The validation result exposes candidate decisions plus expired and evicted item IDs. Its `changed` flag means accepted-item membership/payload changed; revision-only advancement after duplicates, rejections, or no candidates does not make `changed` true.

## Ordinary-turn orchestration — K3

`ContinuityRuntime` in `relaylm.turn` is the first process-local orchestration holder. It owns no continuity semantics. It holds only:

- an explicit `ContinuityContext` supplied by the caller;
- an explicit positive `lifetime_revisions` supplied by the caller.

It defines no default capacity, TTL, persistence, session identity, or Context Compiler policy.

When a runtime is configured, every successfully completed ordinary buffered or streamed turn consumes exactly one K2 lifecycle revision, even when no continuity candidate is produced. This advances the deterministic revision clock and therefore allows expiry to occur without requiring a new candidate.

For single-pass, the completed cognitive output and K2 candidate application remain one composed return-path transition.

For canonical two-pass, successful ordinary-turn completion is the complete accepted Pass 1 response after its Assistant Event is committed. At that point RelayLM advances the Continuity lifecycle exactly once in conversation order and performs any due expiry. Pass 2, if it later succeeds and is still current, applies candidates at that already-advanced revision without a second lifecycle advance.

A failed or stale Pass 2 applies no proposal-driven Continuity mutation, but it does not undo the lifecycle revision/expiry already caused by the successfully completed ordinary conversation. A newer successful Pass 1 may therefore advance the clock again and make an older pending extraction stale without letting that older extraction double-advance the clock.

The current user Event is required as current evidence for ordinary-turn continuity candidates. Candidate validation is computed before the candidate result replaces the runtime holder. A streamed two-pass turn does not advance Continuity while response deltas are still being emitted; the advance occurs only after the complete Pass 1 response is accepted and its Assistant Event is committed. Pass 1 provider failure, cancellation, or failure to commit the Assistant Event does not advance Continuity.

If a cognitive output contains continuity candidates but no explicit runtime is configured, the owning turn/extraction boundary fails rather than silently discarding semantic proposals. Two-pass Pass 1 remains independently valid under its cognition-owner response-first rules; a missing Continuity runtime prevents the Pass 2 proposal set from committing.

`TurnResult.continuity` exposes the composed deterministic K2 validation receipt on the single-pass return path when a runtime is configured. Two-pass extraction exposes its candidate-validation receipt when Pass 2 commits; the process-local `ContinuityRuntime.context` already contains the turn-ordered lifecycle revision before that later extraction completes. Turn/Runtime only orchestrates already-owned semantics and does not redefine `referent`, `unresolved`, `active_task`, provenance, duplicate, supersession, resolution, expiry, or eviction meaning.

The OpenAI API/server wiring can carry an explicitly supplied runtime through buffered and streamed requests. `create_app_from_env()` does not invent one, preserving the prohibition on new runtime/default budgeting policy in this lane.

## Ownership

### Proposal producer

The selected cognitive execution may produce `continuity_candidates` through its owner-defined output path.

No separate semantic producer subsystem is introduced by Continuity Context.

### Acceptance owner

Continuity acceptance is deterministic and implemented by `relaylm.continuity_validation`. The acceptance boundary owns schema validation, provenance checks, lifecycle-key transitions, duplicate/supersession/resolution rules, expiry, eviction, and rejection.

Candidate generation is not acceptance.

### Accepted temporary authority

Continuity Context owns only accepted temporary continuity. It does not gain durable factual authority by surviving multiple turns.

### Turn / Runtime

Turn / Runtime carries proposal output through deterministic validation and updates the process-local holder at the owner-defined ordinary-turn boundaries. It is orchestration only. Response-first two-pass timing may separate lifecycle advance from later candidate application, but both operations remain K2-owned Continuity semantics.

### Context Compiler

The Context Compiler is a consumer. It selects/retains already-accepted `ContinuityItem` values for current cognition under its own bounded residency rules.

It must not inspect raw language and invent missing `referent`, `unresolved`, or `active_task` semantics merely to satisfy retention policy.

## Authority invariants

Continuity Context is not:

- validated durable truth;
- a new Canonical State class;
- occurrence/provenance authority for what happened;
- durable MEMORY;
- durable GOAL / SELF / REL authority;
- disclosure permission;
- capability or action authority.

Accepted continuity must preserve source Event provenance and epistemic role.

In particular:

- assistant inference must not silently become user assertion;
- a user assertion may remain a user assertion without becoming timeless external truth;
- ambiguity may remain unresolved rather than becoming a confident referent;
- accepted continuity cannot mutate Canonical State, MEMORY, or Event occurrence history as a side effect;
- active Canonical State remains authoritative for current-understanding conflicts.

## Initial lifecycle boundary

The first implementation is deliberately non-durable.

It does not require:

- a new durable character file;
- cross-restart continuity;
- a new session identity model;
- durable Working Memory;
- synchronous memory formation.

K1 exposes typed boundaries, K2 supplies deterministic lifecycle semantics, and K3 supplies provider-independent ordinary-turn orchestration with an explicit process-local holder.

## Context Compiler dependency

The implemented dependency is:

```text
#1371 K1 typed continuity model
      |
      v
#1371 K2 deterministic acceptance/lifecycle
      |
      v
#1371 K3 ordinary-turn continuity return path
      |
      v
#1267 Context Compiler C2/C3
accepted referent / unresolved / active_task retention
      |
      v
#1383 ordinary-turn cognition wiring
accepted pre-generation ContinuityRuntime.context
```

Current Context Compiler/Turn wiring consumes accepted `ContinuityItem` values. It does not introduce raw-language inference, temporary duplicate fields, a second semantic owner, compatibility bridges, or speculative retention classification.

## Non-goals

This architecture does not introduce:

- legacy `RelayINT` or `RelayCTX` subsystems;
- a generalized intent engine;
- durable continuity persistence in the first slice;
- long-term memory formation;
- retrieval semantics;
- runtime/default budget policy;
- free-form State-vs-MEMORY contradiction adjudication;
- shared evaluation/authority aggregate ownership.

## Principle

> **The model may propose short-term continuity; RelayLM validates it, Continuity Context temporarily owns it, and Context Compiler decides whether it belongs in cognition now.**
