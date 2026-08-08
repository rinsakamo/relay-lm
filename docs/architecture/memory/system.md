---
relaylm_doc_type: subsystem_architecture
relaylm_authority: memory_subsystem_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - memory subsystem responsibility boundaries change
  - formation, retrieval, storage/recovery, or mutation-governance authority changes
  - Evidence, RelayCTX, RelaySLP, RelayREL, or RT-1 integration boundaries change
  - Primary compatibility retirement changes the memory subsystem topology
relaylm_not_authoritative_for:
  - repository-wide current implementation completion or sequencing
  - exact Evidence, Shared Assessment, Subjective MEM, projection, lifecycle, or storage schemas
  - exact ranking, model, queue, scheduler, API, UI, filesystem, database, or lock implementation
  - exact RT-1 cutover state or R5/R6 retirement approval
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source:
  - ../../adr/0003-subjective-mem-direction.md
  - ../../adr/0004-single-response-call-ordinary-conversation-deferred-formation.md
  - ../../adr/0005-subjective-mem-storage-authority.md
relaylm_related_authority:
  - formation.md
  - retrieval-and-grounding.md
  - storage-and-recovery.md
  - mutation-governance.md
  - ../memory_lifecycle_design.md
  - ../relaymem_slp_current_target.md
  - ../runtime/request-response-pipeline.md
  - ../runtime/scheduler.md
  - ../subjective-mem-retrieval-projection-hard-cutover.md
relaylm_related_contracts:
  - ../../contracts/shared-assessment-subjective-mem.md
  - ../../contracts/subjective-mem-storage-authority-and-commit-protocol.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - memory subsystem implementers and reviewers
  - RelayCTX, RelaySLP, and runtime integration maintainers
  - architecture, migration, and retirement reviewers
relaylm_authority_level: subsystem
---
# Memory Subsystem Architecture

## Purpose

This page is the canonical parent architecture for RelayLM memory responsibilities.

It owns the stable topology between four permanent child responsibilities:

1. [Subjective Memory Formation](formation.md) — when governed Evidence becomes Shared Assessment and Subjective memory candidates;
2. [Ordinary Memory Retrieval and Grounding](retrieval-and-grounding.md) — how one ordinary reader authority selects eligible evidence for the current request and grounds recall;
3. [Memory Storage and Recovery](storage-and-recovery.md) — which durable representations are canonical, operational, or derived and how publication/recovery converges;
4. [Memory Mutation Governance](mutation-governance.md) — how explicit lifecycle operations authorize immutable successors and interact with publication/recovery.

This page is intentionally thinner than its children. It does not duplicate exact schemas, runtime algorithms, lifecycle field sets, storage mechanics, ranking policy, or current milestone status.

## Memory is a set of responsibilities, not one store

RelayLM memory is not one undifferentiated database or prompt-history cache.

The permanent responsibility model is:

```text
Protected Source Evidence
  -> character-independent Shared Assessment
  -> character-scoped Subjective formation
  -> canonical durable memory and operational finalization
  -> rebuildable retrieval projection
  -> ordinary one-authority Retrieval
  -> request-local grounding

explicit lifecycle operation
  -> operation-specific authorization and immutable successor
  -> shared publication/storage/recovery mechanics
  -> new finalized current state
  -> projection refresh/rebuild
```

These arrows describe dependency direction. They do not imply that every stage runs synchronously or in every request.

## Interactive and deferred paths are separate

The ordinary managed response path is latency-sensitive and read-only with respect to canonical durable memory.

```text
current request
  -> bounded current/session context
  -> exact ordinary-memory reader decision
  -> read-only Retrieval and grounding
  -> Main LLM response
  -> finalized visible output and Evidence
```

Durable formation is deferred:

```text
finalized governed Evidence
  -> deferred assessment / episode handling
  -> Shared Assessment
  -> Subjective formation decision
  -> governed storage publication or hold
```

Lifecycle management is separately governed:

```text
explicit management / operator / policy authority
  -> Correct | Forget | Restore | Pin | Unpin | Consolidate | other governed operation
  -> immutable successor + publication/finalization
```

Ordinary conversation does not gain durable mutation authority merely because memory content was discussed.

## Authority layers

The subsystem distinguishes several authority classes that must not be collapsed.

### Governed Evidence

Protected Source Evidence owns what occurred, origin, provenance, authorization, and source lineage under its own contracts.

Memory may reference Evidence but does not rewrite Evidence history to fit later subjective meaning.

### Shared Assessment

Shared Assessment is character-independent support/uncertainty/contradiction/temporal interpretation over governed Evidence.

It cannot acquire SOUL/character identity merely because a later Subjective memory uses it.

### Subjective memory

Subjective memory is character-scoped durable memory whose grounded content remains bound to accepted assessment evidence while subjective meaning may reflect the identified character authority.

Subjective memory is not interchangeable with source Evidence, Shared Assessment, relationship policy, scene state, affect state, or SOUL.

### Durable operations

Operational intent, receipts, idempotency, recovery, jobs, attempts, tombstones, usage events, and related non-rebuildable control facts live in durable operational authority rather than being inferred from memory prose.

### Rebuildable projection

Lookup/ranking/search projection is derived state. Persistence does not make it canonical.

## Permanent child responsibilities

### Formation

[Subjective Memory Formation](formation.md) owns target timing, grouping, Shared Assessment / Subjective Formation separation, and the interactive-versus-deferred boundary.

Its `relaylm_status: target` is intentional: the accepted formation architecture may be ahead of current runtime completion. The parent architecture must not convert target timing or episode behavior into a claim of present implementation.

Formation decides what durable memory candidate is justified. It does not own ordinary reader selection, canonical commit mechanics, or lifecycle-management authorization.

### Retrieval and grounding

[Ordinary Memory Retrieval and Grounding](retrieval-and-grounding.md) owns stable request-side memory serving:

```text
exact reader decision
  -> exactly one selected family or neither
  -> within-authority eligibility/discovery
  -> request-local selected evidence
  -> common grounding policy
```

It is read-only with respect to canonical memory. It never repairs storage, commits a lifecycle change, or uses an empty/failed result to switch durable-memory authority.

### Storage and recovery

[Memory Storage and Recovery](storage-and-recovery.md) owns the separation of canonical content/lifecycle, durable operations, rebuildable projection, and governed Evidence; commit finalization; exact recovery; and writer/concurrency fencing principles.

Storage existence is not reader authority. Locks, receipts, idempotency, or recoverable state are not semantic mutation permission.

### Mutation governance

[Memory Mutation Governance](mutation-governance.md) owns durable lifecycle-operation responsibility: operation-specific semantic authorization, immutable successors, payload fences, selector fencing, publication/finalization integration, exact replay/recovery, and the separation of reversible lifecycle changes from irreversible purge authority.

Shared mutation mechanics do not become a universal semantic operation owner.

## Cross-component boundaries

### RelayCTX

RelayCTX owns bounded request/session continuity and overlays needed for the current answer.

It may carry request-local selected memory or temporary correction/suppression input, but it is not canonical durable memory, an operations ledger, or a lifecycle selector.

A value surviving in request/session context does not become durable memory solely because it affected a prompt.

### RelaySLP

RelaySLP owns deferred assessment/formation orchestration and related operational execution under its accepted contracts.

It may produce or execute governed memory work, but it does not redefine canonical memory meaning, storage authority, lifecycle-transition semantics, ordinary reader authority, or shared grounding merely because it schedules the work.

Queue, retry, worker, scheduler, lease, and service state are operational facts, not memory truth or mutation permission.

### RelaySCN

RelaySCN may constrain persistence and disclosure by scene/audience policy. It cannot invent memory content or become a durable memory store.

Scene policy may narrow retrieval or formation only inside the memory authority already selected by the owning boundary.

### RelayREL

RelayREL owns target-specific relationship policy and relationship state.

It may constrain trusted identity, salience, persistence, and disclosure, but it does not replace RelayMEM storage or silently mutate memory pages.

Relationship strength does not imply disclosure permission or durable-memory authority.

### RelayEMO

RelayEMO may contribute typed, bounded non-authoritative salience or formation evidence. It cannot prove a user fact, increase grounded confidence by itself, or become durable memory simply because an affect estimate was strong.

### RelayRUN and scheduler/runtime control

Execution priority, cancellation, checkpointing, queue scheduling, retry, service supervision, and process placement are runtime-control concerns.

They can decide whether work executes now, later, or not at all; they do not change the semantic authority of memory content, lifecycle, reader choice, or writer permission.

## One ordinary reader authority

RT-1 established the current ordinary-memory serving topology.

```text
primary_only
  -> retained Primary compatibility reader only

neither
  -> no ordinary durable-memory reader

subjective_only
  -> finalized Subjective reader only
  -> no Primary root resolution, discovery, recall, ranking, or fallback
```

Exactly one reader authority, or none, is resolved before ordinary memory-family access.

No configuration setting, store presence, old successful request, ranking result, grounding result, cache row, lifecycle receipt, empty Subjective result, or failed Subjective result can select or restore another reader family.

The detailed cutover state machine remains owned by the RT-1 architecture and current status authority, not by this parent page.

## Primary compatibility is transitional

The repository retains bounded Primary reader, writer, storage/reconciliation, lifecycle, and worker surfaces as compatibility, migration, rollback, regression, operational, or retirement evidence while their final RT-1 disposition remains incomplete.

Those surfaces are not the permanent parent architecture.

Stable transition rules are:

- Primary ordinary serving runs only when the exact reader decision is `primary_only`;
- Primary mutation runs only while the exact writer decision permits it;
- `primary_writer_fenced` cannot be bypassed by an old token, lock, queue item, recovery state, idempotency result, API, UI, or existing store state;
- `subjective_only` never falls back to Primary on empty, refused, failed, stale, or malformed Subjective retrieval;
- continuing read-only/historical/operational consumers must be proved explicitly before a Primary source or runtime surface is retained;
- R5/R6 own final runtime and source-document retirement disposition.

## Current versus target architecture

This parent page is current as a responsibility map, but its children may contain both current and accepted-target material.

In particular:

- formation timing and episode behavior are target architecture unless Project Status says otherwise;
- current Retrieval is governed by the live RT-1 reader decision and existing runtime handoffs;
- current Subjective storage/publication exists only in the bounded implemented slices recorded by Project Status and their implementation handoffs;
- mutation support differs by operation and does not imply one universal implementation path;
- backup, restore, purge, distributed writers, Secondary consolidation, and other target capabilities remain separately governed where not implemented.

Architecture status must therefore be read per responsibility, not as a claim that the complete target memory system is already deployed.

## Privacy and observability

Content-bearing memory evidence remains protected and purpose-bounded.

Runtime-private surfaces may carry memory prose, selected evidence, protected source material, immutable transaction content, or grounded backend context when required by their owning responsibility.

Public, workflow, audit, and generic diagnostic surfaces remain content-free by default. They may expose bounded statuses, counts, booleans, authority classes, lifecycle/recovery reasons, or omission flags, but not unrestricted memory prose, prompt text, paths, namespace values, digests, lineage, tokens, claims, leases, or internal operation artifacts.

A nested content-free projection does not make its enclosing runtime-private artifact safe to persist wholesale.

## Fail-closed dependency direction

Subsystem boundaries fail closed rather than substituting another authority.

Examples:

```text
invalid reader decision
  -> no unauthorized durable-memory access

formation uncertainty
  -> hold / abstain / leave as evidence
  -> do not force a merge or durable memory

storage finalization mismatch
  -> recovery-pending / recovery-required
  -> do not declare normal committed success

prepared or unresolved mutation
  -> retrieval-ineligible
  -> do not serve stale or guessed current state

retrieval/grounding failure
  -> omit/suppress unsupported memory detail
  -> do not select another memory family
```

Cross-component failure never creates a new semantic authority merely to keep the request moving.

## Responsibility flow

The stable subsystem flow can be summarized as:

```text
Evidence authority
  -> Formation responsibility
       -> Shared Assessment
       -> Subjective memory decision
       -> Storage / finalization responsibility
            -> canonical durable memory
            -> durable operations
            -> rebuildable projection

explicit management / lifecycle authority
  -> Mutation Governance
       -> Storage / finalization responsibility
       -> finalized new current state
       -> projection rebuild/refresh

ordinary request
  -> RT-1 reader decision
  -> Retrieval / Grounding
       -> current eligible evidence only
       -> request-local grounded context
```

No child is allowed to reverse these dependency arrows by becoming a fallback owner for another responsibility.

## Source and documentation disposition

This canonical parent replaces phase-oriented memory overview responsibility, not the detailed contracts or current implementation evidence.

`memory_lifecycle_design.md`, `relaymem_slp_current_target.md`, RT-1 hard-cutover architecture, lifecycle operation handoffs, Primary M3 implementation handoffs, and other phase/evidence documents may remain necessary while current consumers, migration gates, validators, or historical responsibilities exist.

Their stable responsibility should converge into this parent and its child pages. Exact schemas stay in contracts; current execution details stay in implementation handoffs/evidence; current completion stays in Project Status; historical truth remains in Git.

Final D6 retirement is atomic and may occur only after references, validators, accepted continuing consumers, R5/R6 dependencies, and replacement validation are proved.

## Stable invariants

- Governed Evidence, Shared Assessment, Subjective memory, durable operations, and rebuildable projection remain distinct authority classes.
- Formation is deferred from the ordinary response path and does not block visible output.
- Ordinary Retrieval is read-only and resolves exactly one durable-memory reader authority or none before memory-family access.
- Retrieval does not mutate or repair storage; storage does not select request reader authority.
- Lifecycle mutation requires operation-specific authorization and immutable successor semantics.
- Shared publication/recovery mechanics do not become semantic operation authority.
- Canonical content/lifecycle and matching durable finalization evidence must converge before normal publication success.
- Prepared, recovery-required, stale, corrupt, or non-current state is not ordinary-Retrieval eligible.
- Locks, queues, leases, idempotency, caches, projections, UI state, and recovery classifications do not create semantic authority.
- Primary compatibility readers/writers remain subordinate to RT-1 decisions while they exist.
- No permanent dual read, dual write, or fallback-driven migration is accepted.
- Public/audit surfaces remain content-free while protected memory content stays runtime-private or canonical under its owning authority.

## Non-goals

This parent architecture does not authorize:

- R5/R6 implementation or Primary deletion;
- exact memory, Evidence, lifecycle, storage, projection, or API schemas;
- a ranking, embedding, vector, graph, model, database, filesystem, queue, scheduler, or lock technology;
- a final backup/restore/purge/disaster-recovery procedure;
- distributed writer implementation;
- automatic durable mutation from ordinary conversation;
- reader fallback between Primary and Subjective;
- RelaySOUL, RelayREL, RelaySCN, or RelayEMO authority transfer into memory;
- media-runtime behavior.
