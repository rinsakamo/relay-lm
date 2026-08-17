# Continuity Context

> **Status:** accepted semantic architecture tracked by #1371. K1 typed boundaries are implemented in `relaylm.continuity`; K2 deterministic acceptance/lifecycle is implemented in `relaylm.continuity_validation`; ordinary-turn return-path wiring (K3) remains deferred.

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

## Accepted return-path shape

The ordinary cognitive model remains one semantic generation. The accepted target return path is:

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

## Current typed boundary — K1

`src/relaylm/continuity.py` is the current typed semantic owner for the K1 boundary.

A `ContinuityCandidate` carries:

- one of the three bounded initial kinds;
- a non-empty lifecycle `key` used by deterministic lifecycle rules;
- an explicit `set` or `resolve` operation;
- Event source IDs;
- an explicit epistemic role: `user_assertion`, `assistant_inference`, or `assistant_commitment`;
- a semantic value only for `set` proposals.

The candidate remains a proposal. Constructor validity does not grant acceptance authority.

A `ContinuityItem` is the typed shape reserved for accepted temporary authority. It preserves kind, key, semantic value, Event sources, epistemic role, and an explicit revision-bounded lifetime (`accepted_revision` / `expires_revision`).

`ContinuityContext` is an immutable container with an explicit positive `max_items`, a monotonic non-negative `revision`, and a tuple of non-expired `ContinuityItem` values. It has no default runtime capacity policy and no persistence contract. The explicit bound is a semantic container boundary, not a runtime/default budgeting decision.

## Deterministic acceptance and lifecycle — K2

`src/relaylm/continuity_validation.py` is the deterministic acceptance/lifecycle owner.

One call to `apply_continuity_candidates` advances the context revision exactly once. Its order is fixed:

1. advance to the next revision;
2. expire items whose `expires_revision` has been reached;
3. validate and apply candidates in input order;
4. if capacity is exceeded, evict oldest accepted items deterministically.

The caller must provide a positive `lifetime_revisions` value. K2 does not choose a default TTL or runtime budget. Accepted items expire at `accepted_revision + lifetime_revisions` unless they are superseded, resolved, or evicted earlier.

Candidate acceptance requires known Event source IDs. A caller may additionally require intersection with a set of current-evidence Event IDs. A `user_assertion` candidate must include at least one user-authored source Event. A `set` value must be JSON-serializable with non-finite numeric values rejected. These checks preserve provenance and reject malformed authority rather than inferring missing meaning.

For each lifecycle `key`, transition semantics are:

- no existing item + valid `set` -> `admit`;
- existing item + exact same kind/value/deduplicated sources/epistemic role -> `duplicate` noop, with no lifetime refresh;
- existing item + valid changed `set` on the same key -> `supersede`, replacing the prior item directly;
- valid `resolve` + no existing key -> `not_found` noop;
- valid `resolve` + existing same-kind key -> `resolve`, removing the item;
- valid `resolve` + existing different-kind key -> reject `kind_mismatch`.

Accepted item IDs are deterministic from the new context revision and candidate order. Superseded items are treated as newly accepted for lifecycle age. When `max_items` is exceeded after candidate processing, eviction chooses the oldest `accepted_revision`, using existing tuple order as the deterministic tie-breaker.

The validation result exposes candidate decisions plus expired and evicted item IDs. Its `changed` flag means accepted-item membership/payload changed; revision-only advancement after duplicates/rejections/no candidates does not make `changed` true.

K2 does not inspect raw language, mutate Canonical State/MEMORY/Event occurrence history, persist Continuity Context, or wire the cognitive return path. Those ownership boundaries remain unchanged.

## Ownership

### Proposal producer

The existing cognitive generation may produce `continuity_candidates` alongside `response` and `state_candidates` after K3 wires the return path.

No separate semantic producer subsystem and no mandatory second LLM call are introduced.

### Acceptance owner

Continuity acceptance is deterministic and implemented by `relaylm.continuity_validation`. The acceptance boundary owns schema validation, provenance checks, lifecycle-key transitions, duplicate/supersession/resolution rules, expiry, eviction, and rejection.

Candidate generation is not acceptance.

### Accepted temporary authority

Continuity Context owns only accepted temporary continuity. It does not gain durable factual authority by surviving multiple turns.

### Turn / Runtime

Turn / Runtime may orchestrate candidate validation and commit after K3, but does not redefine referent, unresolved, active-task, provenance, or lifecycle semantics.

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

The first runtime holder may be process/runtime-local, but implementation must expose typed boundaries so storage can change later without changing semantic ownership.

K1 exposes typed boundaries and K2 supplies deterministic admit/reject/duplicate/supersede/resolve/evict/expire behavior. K3 wires the accepted result into ordinary buffered/streamed turn orchestration.

## Context Compiler dependency

The previously blocked #1267 `referent / unresolved` retention work is no longer an architecture-owner question after this authority document merges.

Its implementation dependency is explicit:

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

Until K1-K3 exist on current `v1`, the Context Compiler must not work around the dependency with raw-language inference, temporary fields, duplicate semantic owners, compatibility bridges, or speculative retention classification.

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
