---
relaylm_doc_type: concept_policy
relaylm_authority: pinned_normal_memory_semantics
relaylm_status: current
relaylm_volatility: low
relaylm_owner: memory
relaylm_update_trigger:
  - Pin or Unpin lifecycle semantics change
  - ordinary Retrieval changes pinned eligibility or ranking treatment
  - automatic maintenance or consolidation changes pinned-memory protection
  - RT-1 retirement changes Primary pin compatibility evidence
relaylm_not_authoritative_for:
  - exact Pin/Unpin API, UI, proposal, receipt, selector, or token schemas
  - exact ranking weights, formulas, candidate budgets, or cache implementation
  - exact maintenance, consolidation, purge, or retirement procedure
  - current implementation completion or RT-1 cutover state
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - mutation-governance.md
  - retrieval-and-grounding.md
  - system.md
  - ../subjective-mem-pin-unpin-runtime.md
  - ../subjective-mem-consolidate-runtime.md
  - ../subjective-mem-retrieval-projection-hard-cutover.md
relaylm_related_contracts:
  - ../../contracts/shared-assessment-subjective-mem.md
  - ../../contracts/subjective-mem-storage-authority-and-commit-protocol.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - memory lifecycle and maintenance implementers
  - ordinary Retrieval and ranking maintainers
  - memory management UI/API reviewers
relaylm_authority_level: concept
---
# Pinned Memory

## Authority summary

Pinned memory is ordinary durable memory whose lifecycle state expresses explicit protection and retrieval emphasis without changing its semantic content or creating a new reader authority.

Pinning is a governed lifecycle transition, not an orthogonal mutable flag, a separate pin database, a disclosure permission, or an unconditional ranking override.

Exact Pin/Unpin operation mechanics remain owned by [Memory Mutation Governance](mutation-governance.md), its contracts, and the current Pin/Unpin runtime handoff. Ordinary candidate consumption and ranking remain owned by [Ordinary Memory Retrieval and Grounding](retrieval-and-grounding.md).

## Problem

Some ordinary memories need to remain easy to recall and protected from routine automated maintenance even when recency, usage, or ordinary ranking signals would otherwise reduce their prominence.

A naive `pinned=true` flag creates several authority problems:

- it can drift from the canonical lifecycle selector;
- a stale cache can make an old revision appear pinned;
- a ranking layer can accidentally make hidden or unsafe material retrievable;
- maintenance can treat pin state as a separate mutable truth;
- Primary compatibility pin projections can compete with Subjective lifecycle authority;
- UI state can be mistaken for a durable mutation.

Pinned memory avoids these problems by treating Pin/Unpin as canonical lifecycle governance over immutable revisions.

## Definition

For Subjective memory, Pin is the governed transition:

```text
active revision N
  -> pinned revision N+1
```

Unpin is:

```text
pinned revision N
  -> active revision N+1
```

The successor preserves memory identity and semantic payload while changing the lifecycle state through its exact operation authority.

A pinned revision remains ordinary retrieval memory only when all other currentness, scope, mutation-state, disclosure, and retrieval-eligibility rules pass.

## Pin is lifecycle state

The canonical state model treats `pinned` as a lifecycle state rather than a second independent property.

Stable consequences are:

- the exact singleton current selector identifies the current pinned revision;
- the predecessor remains immutable history;
- a later Unpin creates another immutable successor;
- a stale pin receipt or UI token cannot pin an older revision;
- no second pin-state projection becomes canonical;
- pin state cannot be inferred from filesystem order, timestamps, cache rows, or old Primary artifacts.

During prepared publication, the logical selector is mutation-fenced and ordinary Retrieval fails closed until exact finalization restores a normal current state.

## Semantic payload does not change

Pin/Unpin is not a correction or content rewrite.

The operation preserves the logical memory's grounded content, subjective meaning, character, memory kind, formation stage, scope, formation snapshot, and other semantic dimensions required by the exact contract.

The lifecycle successor changes only the operation-authorized lifecycle/revision/lineage and bounded governance metadata.

A request that also needs semantic correction must use the Correct authority rather than hiding a correction inside Pin/Unpin.

## Retrieval eligibility comes first

Pin is subordinate to ordinary Retrieval eligibility.

Conceptually:

```text
exact reader authority
  -> exact current revision
  -> lifecycle / mutation / scope / disclosure eligibility
  -> candidate relevance and other required gates
  -> pinned status may influence ordering among remaining eligible candidates
```

Pin cannot make any of the following retrievable:

- hidden or purged memory;
- held memory that has not been governed into an eligible state;
- prepared or recovery-required memory;
- stale or prior revisions;
- corrupt, ambiguous, unsafe, or unverifiable state;
- cross-character, cross-workspace, cross-participant, or otherwise out-of-scope evidence;
- evidence blocked by scene/audience/disclosure policy;
- evidence from a memory family that the request's exact reader decision did not select.

`pinned` is therefore a bounded ranking/protection signal after eligibility, not a shortcut around eligibility.

## Ranking semantics

A retrieval implementation may use pinned state as an explicit, inspectable ordering feature among already-eligible candidates.

The exact ranking weight, tie-break order, candidate budget, vector/lexical interaction, or token budget remains implementation/contract detail.

Stable rules are:

- pinning should not silently suppress stronger scope or disclosure constraints;
- pinning should not create a second candidate-discovery path;
- pinning should not force every pinned memory into every prompt;
- pinning should not replace query relevance when relevance is required by the selected retrieval authority;
- a pinned memory omitted by final bounded packing remains pinned canonically;
- ranking outcomes do not mutate pin state.

## Protection from ordinary maintenance

Pinned memory is protected from ordinary automatic maintenance that would demote, consolidate, hide, replace, or otherwise lifecycle-transform it without an authority that explicitly permits operating on pinned state.

This protection is semantic, not a permanent physical lock.

Stable consequences are:

- automatic maintenance must check exact current lifecycle state before acting;
- a transition whose contract requires `active` cannot treat `pinned` as equivalent merely to make progress;
- a stale pre-pin proposal cannot apply after Pin finalizes;
- background maintenance does not auto-Unpin to satisfy its own precondition;
- explicit user/operator management may still Correct, Forget, Unpin, or otherwise govern memory only through the exact operation whose contract permits the current pinned state;
- Purge remains a separate irreversible authority and is not defined by this concept.

The exact maintenance operations that honor or reject pinned state remain owned by their contracts and implementation authorities.

## Consolidation boundary

Primary-to-Secondary Consolidate and Pin are distinct lifecycle concepts.

A current contract that allows Consolidate only from `active` must fail closed for `pinned`; it cannot implicitly Unpin, consolidate, then re-Pin as one hidden operation.

If future policy ever permits consolidation of pinned memory, that change requires an explicit contract and lifecycle decision explaining preservation of pin semantics. This concept does not pre-authorize it.

## Explicit management authority

Pin and Unpin require the exact management/operator authority accepted by their operation contract.

Pin state cannot be created from:

- ordinary conversation alone;
- model preference or ranking score;
- a browser checkbox that was not successfully finalized through the owning operation;
- an old operation token after the current revision changed;
- a Primary compatibility pin projection;
- an idempotency or recovery record from another lifecycle operation.

A UI or API may request Pin/Unpin, but canonical state changes only after the exact lifecycle operation publishes and finalizes successfully.

## Idempotency and replay

Exact replay may return the already-finalized Pin/Unpin result when operation identity, direction, current lineage, authority, and successor bindings all match.

Replay does not create additional successors and does not reverse the operation.

Reusing one idempotency key for a different proposal or for the inverse direction is an integrity conflict rather than an instruction to toggle state.

Idempotency proves duplicate-operation convergence; it does not grant authority to Pin or Unpin a different current revision.

## Recovery boundary

Prepared or interrupted Pin/Unpin publication follows the owning lifecycle publication/recovery protocol.

Recovery may complete an exact already-authorized successor when durable pre-image/post-image evidence supports it. Recovery does not regenerate a different successor, infer a new operation direction, or convert a stale proposal into current authority.

While recovery remains unresolved, ordinary Retrieval fails closed for the affected logical memory.

## Primary compatibility boundary

Historical Primary Pin/Unpin projection and ranking behavior remains compatibility, regression, migration, or retirement evidence only.

It is not Subjective pin semantic authority and cannot create a parallel durable pin state.

No Primary pin artifact, receipt, UI state, or ranking helper bypasses RT-1 reader/writer decisions. After Primary mutation is fenced, old Primary Pin/Unpin authority cannot be restored by a retained pin projection or exact historical receipt.

R5/R6 own the final disposition of Primary compatibility pin surfaces.

## Interaction with mutation governance

[Memory Mutation Governance](mutation-governance.md) owns the durable lifecycle-operation responsibility:

```text
exact current active/pinned revision
  + exact management authority
  -> Pin or Unpin operation
  -> immutable successor
  -> shared publication/finalization
  -> exact current selector
```

This concept owns the semantic meaning of being pinned; it does not duplicate the operation engine.

## Interaction with Retrieval

[Ordinary Memory Retrieval and Grounding](retrieval-and-grounding.md) owns candidate consumption and request-time ranking.

Retrieval reads finalized pinned state as one eligible-candidate feature. It never writes pin state merely because a pinned memory was used, omitted, highly ranked, or judged irrelevant for one request.

A reader decision of `neither` or a different selected memory authority still dominates pin status.

## Interaction with storage

Pin state is part of canonical lifecycle authority, while durable claims/receipts/idempotency/recovery facts live in the operations domain and lookup/ranking projection remains rebuildable.

A persistent projection row saying `pinned` does not override a canonical selector or finalized lifecycle receipt that says otherwise.

Projection rebuild must recover pinned state from canonical/authorized lifecycle sources rather than becoming the source of truth.

## Privacy and diagnostics

Pinning does not relax content protection.

Public and audit surfaces may expose bounded lifecycle/status booleans, operation result classes, counts, or reason IDs when their exact interface permits it. They do not gain permission to expose unrestricted memory prose, raw management reasons, filesystem paths, namespace values, digests, raw tokens, or internal operation artifacts merely because a memory is pinned.

## Invariants

- Pinned memory is ordinary memory in canonical `pinned` lifecycle state.
- Pin and Unpin create immutable consecutive successors; they do not mutate predecessors in place.
- Pin/Unpin does not rewrite semantic memory content.
- Pin status is canonical lifecycle authority, not an orthogonal flag or second projection authority.
- Ordinary Retrieval eligibility, scope, disclosure, currentness, and reader authority are checked before pin may influence ordering.
- Pin cannot make hidden, held, prepared, recovery-required, corrupt, stale, or out-of-scope memory retrievable.
- Pin is a bounded ranking/protection signal, not unconditional prompt inclusion.
- Ordinary automatic maintenance cannot silently bypass pinned state or auto-Unpin to make another transition legal.
- UI state, cache rows, old tokens, idempotency, locks, or recovery records do not independently create pin authority.
- Historical Primary pin artifacts do not compete with Subjective lifecycle authority or bypass RT-1.

## Non-goals

Pinned Memory does not define:

- exact Pin/Unpin API or UI fields;
- exact ranking weights or candidate budgets;
- automatic Pin/Unpin from model output or ordinary conversation;
- a separate pin database or canonical pin projection;
- disclosure permission or cross-scope override;
- physical undeletability or a Purge implementation;
- generic maintenance policy for all lifecycle operations;
- R5/R6 retirement implementation.

## Related architecture and contracts

- [Memory Mutation Governance](mutation-governance.md)
- [Ordinary Memory Retrieval and Grounding](retrieval-and-grounding.md)
- [Memory Subsystem Architecture](system.md)
- [Subjective MEM Pin / Unpin Runtime](../subjective-mem-pin-unpin-runtime.md)
- [Shared Assessment and Subjective MEM Contract](../../contracts/shared-assessment-subjective-mem.md)
- [Subjective MEM Storage Authority and Commit Protocol](../../contracts/subjective-mem-storage-authority-and-commit-protocol.md)
