# Continuity Context

> **Status:** accepted semantic architecture tracked by #1371. K1 typed boundaries are implemented in `relaylm.continuity`; K2 deterministic acceptance/lifecycle is implemented in `relaylm.continuity_validation`; K3 ordinary-turn return-path wiring is implemented in `relaylm.cognitive`, `relaylm.turn`, and the explicit app/router runtime carriage.

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

A later Context Compiler transaction may select accepted Continuity Context into current cognition, but current residency does not own production or acceptance of continuity semantics.

## Ordinary-turn return path

The ordinary cognitive model remains one semantic generation:

```text
CognitiveInput
      |
      v
LM x 1
      |
      v
CognitiveOutput
  response
  state_candidates
  continuity_candidates
        |
        v
 deterministic continuity validation
        |
        v
 Continuity Context
        |
        v
 later-turn Context Compiler input
```

`ContinuityCandidate` is a proposal only. Model output is never accepted continuity merely because the model emitted it.

This mirrors the authority shape of `StateCandidate -> deterministic validation -> Canonical State` without making continuity into Canonical State.

K3 exposes `CognitiveOutput.continuity_candidates` on the provider-independent cognitive boundary. Buffered turns consume proposals from the same single `provider.generate()` call. Streamed turns consume them only after the same single `stream_generate()` call completes successfully. K3 introduces no second semantic generation.

Provider-specific structured-output grammar is a separate adapter concern. K3 does not require every adapter to emit the new proposal channel immediately and does not move continuity semantics into an adapter.

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

One call to `apply_continuity_candidates` advances the context revision exactly once. Its order is fixed:

1. advance to the next revision;
2. expire items whose `expires_revision` has been reached;
3. validate and apply candidates in input order;
4. if capacity is exceeded, evict oldest accepted items deterministically.

The caller must provide a positive `lifetime_revisions` value. K2 does not choose a default TTL or runtime budget. Accepted items expire at `accepted_revision + lifetime_revisions` unless superseded, resolved, or evicted earlier.

Candidate acceptance requires known Event source IDs. A caller may additionally require intersection with current-evidence Event IDs. A `user_assertion` candidate must include at least one user-authored source Event. A `set` value must be JSON-serializable with non-finite numeric values rejected. These checks preserve provenance and reject malformed authority rather than inferring missing meaning.

For each lifecycle `key`, transition semantics are:

- no existing item + valid `set` -> `admit`;
- existing item + exact same kind/value/deduplicated sources/epistemic role -> `duplicate` noop, with no lifetime refresh;
- existing item + valid changed `set` on the same key -> `supersede`, replacing the prior item directly;
- valid `resolve` + no existing key -> `not_found` noop;
- valid `resolve` + existing same-kind key -> `resolve`, removing the item;
- valid `resolve` + existing different-kind key -> reject `kind_mismatch`.

Accepted item IDs are deterministic from the new context revision and candidate order. Superseded items are newly accepted for lifecycle age. Capacity eviction chooses the oldest `accepted_revision`, using existing tuple order as deterministic tie-breaker.

The validation result exposes candidate decisions plus expired and evicted item IDs. Its `changed` flag means accepted-item membership/payload changed; revision-only advancement after duplicates, rejections, or no candidates does not make `changed` true.

## Ordinary-turn orchestration — K3

`ContinuityRuntime` in `relaylm.turn` is the first process-local orchestration holder. It owns no continuity semantics. It holds only:

- an explicit `ContinuityContext` supplied by the caller;
- an explicit positive `lifetime_revisions` supplied by the caller.

It defines no default capacity, TTL, persistence, session identity, or Context Compiler policy.

When a runtime is configured, every successfully completed ordinary buffered or streamed turn invokes K2 exactly once, even when `continuity_candidates` is empty. This advances the deterministic revision clock and therefore allows expiry to occur without requiring a new candidate.

The current user Event is required as current evidence for ordinary-turn continuity candidates. Candidate validation is computed before the runtime holder is updated. A streamed turn does not update Continuity Context while response deltas are still being emitted; provider failure or cancellation therefore does not commit continuity.

If a cognitive output contains continuity candidates but no explicit runtime is configured, Turn rejects the output before Assistant Event, State, or Continuity commit rather than silently discarding semantic proposals.

`TurnResult.continuity` exposes the deterministic K2 validation receipt when a runtime is configured. Turn/Runtime only orchestrates already-owned semantics and does not redefine `referent`, `unresolved`, `active_task`, provenance, duplicate, supersession, resolution, expiry, or eviction meaning.

The OpenAI API/server wiring can carry an explicitly supplied runtime through buffered and streamed requests. `create_app_from_env()` does not invent one, preserving the prohibition on new runtime/default budgeting policy in this lane.

## Ownership

### Proposal producer

The existing cognitive generation may produce `continuity_candidates` alongside `response` and `state_candidates` in the same semantic generation.

No separate semantic producer subsystem and no mandatory second LLM call are introduced.

### Acceptance owner

Continuity acceptance is deterministic and implemented by `relaylm.continuity_validation`. The acceptance boundary owns schema validation, provenance checks, lifecycle-key transitions, duplicate/supersession/resolution rules, expiry, eviction, and rejection.

Candidate generation is not acceptance.

### Accepted temporary authority

Continuity Context owns only accepted temporary continuity. It does not gain durable factual authority by surviving multiple turns.

### Turn / Runtime

Turn / Runtime carries proposal output through deterministic validation and updates the process-local holder after successful ordinary-turn completion. It is orchestration only.

### Context Compiler

The Context Compiler is a consumer. It may later select, retain, or project already-accepted `ContinuityItem` values into the current cognitive working set.

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

K1 exposes typed boundaries, K2 supplies deterministic lifecycle semantics, and K3 supplies provider-independent ordinary-turn return-path orchestration with an explicit process-local holder.

## Context Compiler dependency

The implementation dependency is:

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
#1267 Context Compiler C2
accepted referent / unresolved retention
      |
      v
#1267 C3 active_task retention
```

With K1-K3 present on current `v1`, the Continuity foundation dependency for #1267 C2 is satisfied. C2 remains a separate Context Compiler transaction and must consume accepted `ContinuityItem` values rather than introduce raw-language inference, temporary fields, duplicate semantic owners, compatibility bridges, or speculative retention classification.

## Non-goals

This architecture does not introduce:

- legacy `RelayINT` or `RelayCTX` subsystems;
- a generalized intent engine;
- a second mandatory semantic model call;
- durable continuity persistence in the first slice;
- long-term memory formation;
- retrieval semantics;
- runtime/default budget policy;
- free-form State-vs-MEMORY contradiction adjudication;
- shared evaluation/authority aggregate ownership.

## Principle

> **The model may propose short-term continuity; RelayLM validates it, Continuity Context temporarily owns it, and Context Compiler decides whether it belongs in cognition now.**
