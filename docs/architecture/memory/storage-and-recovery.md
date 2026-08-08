---
relaylm_doc_type: subsystem_architecture
relaylm_authority: memory_storage_commit_projection_and_recovery_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - canonical memory storage authority changes
  - commit-finalization or recovery responsibility changes
  - rebuildable projection or durable operations ownership changes
  - lifecycle publication or durable usage-event ownership changes
  - Primary compatibility storage or reconciliation retirement changes
relaylm_not_authoritative_for:
  - repository-wide current implementation completion or sequencing
  - exact Markdown page, block, renderer, or front-matter syntax
  - exact database, table, index, WAL, journal, lock, filesystem API, or fsync sequence
  - exact backup, restore, rollout, rollback, or migration procedure
  - exact RT-1 cutover state, R5/R6 retirement approval, or distributed-writer protocol
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source:
  - ../../adr/0003-subjective-mem-direction.md
  - ../../adr/0005-subjective-mem-storage-authority.md
relaylm_related_authority:
  - ../st1_subjective_mem_commit_runtime.md
  - ../subjective-mem-lifecycle-publication-engine.md
  - ../subjective-mem-retrieval-projection-hard-cutover.md
  - ../relaymem_m3d_primary_writer_handoff.md
  - ../relaymem_m3e_atomic_primary_page_writer.md
  - ../relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - ../relaymem_m3g_primary_index_log_reconciliation_apply.md
  - ../relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - ../relaymem_slp_current_target.md
  - retrieval-and-grounding.md
  - formation.md
relaylm_related_contracts:
  - ../../contracts/subjective-mem-storage-authority-and-commit-protocol.md
  - ../../contracts/shared-assessment-subjective-mem.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - memory persistence and lifecycle implementers
  - retrieval and projection maintainers
  - recovery, integrity, migration, and retirement reviewers
relaylm_authority_level: subsystem
---
# Memory Storage and Recovery

## Purpose

This page is the canonical subsystem architecture for durable memory storage, publication finalization, rebuildable projection, operational state, and crash recovery.

It owns the stable separation between:

1. canonical memory content and lifecycle-visible state;
2. non-rebuildable durable operational facts;
3. rebuildable retrieval/search projection state;
4. governed source/evidence authority; and
5. the recovery boundary that reconciles canonical state with durable operation intent and receipts.

It does not own exact schemas, filesystem calls, database layouts, platform-specific durability recipes, backup procedures, or repository-wide completion state. Exact target requirements remain contract-owned, and exact current implementation status remains owned by [Project Status](../../PROJECT_STATUS.md).

## Authority classes do not collapse

The durable memory system separates authority classes because persistence alone does not make two representations interchangeable.

```text
canonical memory documents
  own memory meaning, revision lineage, and lifecycle-visible state

rebuildable projection
  owns derived lookup/search/ranking state only

durable operations authority
  owns non-rebuildable intents, receipts, idempotency, recovery,
  job/attempt state, tombstones, and content-free usage events

governed evidence authority
  owns protected source and Shared Assessment under its own contracts
```

A persistent cache is not canonical merely because it is durable. An operations ledger is not a second editable memory store merely because it contains memory IDs and digests. Canonical memory documents do not absorb queue, lease, idempotency, receipt, or recovery facts that cannot be safely reconstructed from memory prose.

The target Subjective storage contract defines these classes normatively. Current implementation may realize only bounded slices of the full target contract; this architecture does not promote unimplemented target details to current runtime behavior.

## Canonical Subjective memory authority

The accepted steady-state Subjective memory authority is human-readable canonical Markdown with stable logical memory identity and immutable revision lineage.

Canonical memory owns durable semantic and lifecycle-visible facts such as:

- grounded content and subjective meaning;
- logical memory identity and revision lineage;
- memory kind and formation stage;
- character and governed scope;
- current lifecycle-visible revision state;
- references to authorizing formation or lifecycle decisions;
- user-visible organization and governed editability.

Physical path, heading, file order, modification time, or cache-row order is not logical memory identity or current-state authority.

Current ST-1 and lifecycle publication implementations provide bounded production evidence for this direction. Exact page syntax, block grammar, renderer behavior, selector schemas, and operation-record fields remain owned by their contracts and current implementation handoffs rather than this architecture page.

## Publication finalization

Canonical file replacement and durable operational finalization are separate responsibilities that must converge before a mutation is normally published.

The accepted logical relationship is:

```text
prepared immutable operation intent
  -> exact canonical post-image publication
  -> post-image verification and durability fence
  -> matching durable operation receipt/final result
  -> normally published memory state
```

The canonical document remains semantic authority. The durable receipt is the publication/finalization marker and non-rebuildable operation evidence; it does not become a second copy of memory prose or lifecycle state.

A canonical post-image without its required finalization receipt is recovery-pending physical state rather than normally published memory. A receipt whose expected canonical post-image cannot be verified is recovery-required, corrupt, or otherwise fail-closed rather than success.

Projection refresh is not semantic commit authority. A mutation does not become canonical merely because a search database or retrieval projection contains a row for it.

## Current Subjective publication implementation

The current Subjective stack contains bounded implementations of the accepted publication model.

ST-1 publishes a prepared revision-1 Subjective memory through an immutable rendered artifact, exact page pre-image/post-image verification, secure single-host publication, and matching durable finalization records.

The shared Subjective lifecycle publication engine generalizes operation-neutral mechanics for supported lifecycle successors:

```text
operation owner
  -> validates semantic transition and authorization
  -> constructs exact immutable successor

shared publication engine
  -> reserves/fences current selector
  -> records exact durable intent
  -> publishes/verifies canonical post-image
  -> invokes deterministic operation finalizer
  -> commits shared lifecycle receipt/result/current state
  -> supports exact replay and caller-invoked forward recovery
```

The shared engine does not own operation semantics. Correct, Forget, Pin/Unpin, Restore, Consolidate, and future lifecycle operations retain their own policy and semantic authority even when they reuse common publication mechanics.

Current implementation support for a bounded operation does not imply that every target storage, backup, migration, platform, or distributed-writer requirement is complete.

## Immutable transaction material is not authority

A writer may require immutable rendered artifacts, staged files, temp files, digest-bound plans, or other transaction material so an interrupted operation can resume without regenerating semantic content.

Such material is not an independently editable memory authority.

Stable rules are:

- transaction artifacts are bound to exact intent and digest identity;
- they do not become a second current memory selector;
- they are not ordinary Retrieval authority;
- they cannot be edited to redefine the prepared post-image after intent is durable;
- cleanup failure does not convert them into canonical memory;
- recovery uses them only through the owning exact operation protocol.

## Durable operations authority

The durable operations domain owns facts that cannot safely be reconstructed from canonical memory pages alone.

Representative responsibilities include:

- prepared operation intents and exact preconditions;
- idempotency reservations and finalized results;
- publication and lifecycle receipts;
- recovery-required and operator-reconciliation state;
- jobs, attempts, claims, leases, retries, and scheduling state where applicable;
- anti-reformation tombstones and their operation lineage;
- content-free durable usage events;
- projection-stale or rebuild-required state when behavior depends on it.

Operational records refer to stable IDs, revisions, digests, authority snapshots, and bounded reason classes. They do not duplicate unrestricted memory bodies, user queries, prompts, or governed source prose for convenience.

Operations authority does not own an independently editable lifecycle truth or second logical current selector.

## Rebuildable projection

Search, retrieval, and management surfaces may use a persistent derived projection containing bounded parsed and indexed state.

Typical derived responsibilities may include:

- parsed current revision lookup;
- canonical page/block digests;
- lifecycle and retrieval-eligibility projection;
- lexical/full-text indexes;
- semantic facets, vector or graph references;
- derived usage aggregates;
- explainable ranking features.

Projection persistence, WAL, replication, or backup convenience does not elevate it to canonical authority.

A stale, corrupt, unsupported, mixed-generation, or incompletely rebuilt projection fails closed. It may trigger rebuild/refresh or bounded unavailable state, but it cannot silently fall back to stale data or redefine committed content.

Deleting or rebuilding the projection must not delete or change canonical memory, lifecycle state, durable receipts, tombstones, or durable usage history.

Ordinary Retrieval consumes projection state only under the rules in [Ordinary Memory Retrieval and Grounding](retrieval-and-grounding.md); retrieval projection does not become a second memory store.

## Recovery is digest- and revision-driven

Recovery reasons from exact durable identity, not timestamps, newest-write-wins rules, cache rows, or filesystem names.

For an unresolved exact mutation intent, the stable recovery classes are conceptually:

```text
current canonical image == expected pre-image
  -> replacement did not become durable
  -> exact retry or governed abort may be considered under original authority

current canonical image == expected post-image
  -> replacement became durable
  -> roll forward the missing receipt/idempotency/enforcement/projection work

current canonical image == neither
  -> foreign modification, corruption, unsupported normalization, or stale writer
  -> fail closed and preserve reconciliation evidence
```

Recovery does not call a semantic model to invent a new post-image. It reuses the exact prepared transaction material and original authority references when roll-forward is valid.

A foreign image is never overwritten automatically merely because an older intent exists.

## Recovery and authorization are separate

Recovery evidence does not itself grant mutation authority.

A plan, receipt, lock, idempotency match, pre-image match, post-image match, retry classification, or recovery candidate can describe what state exists and what bounded continuation may be safe. Any mutation step must still satisfy its current owning authorization and fencing boundary.

This distinction is especially important during RT-1 transition. Historical Primary recovery or reconciliation evidence cannot revive Primary mutation after the exact RT-1 writer decision has fenced that writer class.

Likewise, a Subjective lifecycle recovery path cannot bypass the operation owner's semantic authorization merely because the shared publication engine recognizes a recoverable durable state.

## Concurrency and writer fencing

Storage concurrency and semantic mutation authority are distinct layers.

Stable publication requires exact revision/digest fencing immediately before mutation. A stale writer cannot overwrite a newer canonical image merely because it previously prepared a valid operation.

Filesystem locks, page-domain locks, advisory locks, compare-and-swap digests, and lease tokens may coordinate implementation concurrency. They do not independently authorize a semantic mutation.

The accepted target remains one canonical writer authority per affected page/operation domain unless a stronger distributed protocol is separately accepted. Multi-host coordination, fairness, backoff, batching, and exact lock implementation remain separately governed.

## Primary compatibility storage and reconciliation

The repository still contains bounded Primary persistence/reconciliation components as compatibility, regression, migration, rollback, and retirement evidence while their final RT-1 disposition remains owned by R5/R6.

Their current compatibility chain is:

```text
exact RT-1 Primary writer decision must permit
  -> M3d writer-handoff preflight             read-only
  -> M3e atomic Primary page publication      mutation
  -> M3f index/log reconciliation preflight   read-only
  -> M3g index-before-log reconciliation      mutation
  -> M3h recovery audit                       read-only
```

These components remain detailed implementation sources, not permanent subsystem-architecture parents.

Stable compatibility lessons retained here are:

- preflight/readiness state is not semantic writer authorization;
- page publication and control-file reconciliation have distinct owners;
- index-before-log ordering avoids a supported log-without-index apply order;
- per-file atomic replacement does not claim a page/index/log transaction;
- idempotent existing state is consistency evidence, not permission;
- M3g's advisory writer lock is a filesystem concurrency boundary, not RT-1 writer authority;
- M3h classifications are read-only recovery evidence, not repair permission;
- resumable or retryable state still requires current writer authorization for any later mutation.

Final removal or explicit retained disposition of these Primary compatibility surfaces belongs to the owning R5/R6 dependency and retirement review.

## Primary control-file recovery boundary

The retained Primary path historically uses a Markdown page plus bounded `index.md` and `log.md` reconciliation rather than the Subjective canonical-page-plus-finalization-receipt model.

M3g intentionally allows a recoverable intermediate state in which the index reaches its proposed state before the log. M3h can classify durable state after an interrupted or uncertain apply.

This compatibility model is not the target Subjective storage authority and is not a reason to duplicate Primary control-file semantics in the permanent Subjective architecture.

A future journaled Primary repair apply is not implied by the current read-only M3h audit. If operational evidence ever requires such repair before retirement, it needs its own explicit mutation/authorization contract.

## Durable usage events

When retrieval ranking, management UI, or lifecycle policy depends on usage history, the underlying usage events are durable operational facts rather than cache-only counters.

Usage events remain content-free by default and may carry bounded identities, event classes, times, or selection/query-plan digests as required by their exact contract.

Derived aggregates such as count, last-used time, or ranking features remain rebuildable projection state.

Usage does not become evidence confidence, truth authority, merge authority, disclosure permission, lifecycle authority, or current-reader authority.

## Failure model

Storage and recovery fail closed instead of inventing authority from persistence state.

Examples:

```text
canonical post-image exists but receipt absent
  -> recovery pending
  -> do not serve as normally finalized state until exact recovery succeeds

receipt exists but canonical post-image does not verify
  -> recovery required / corrupt
  -> no success claim

projection stale or corrupt
  -> rebuild/refresh or unavailable
  -> do not redefine canonical memory

foreign canonical image under an unresolved intent
  -> preserve evidence and fail closed
  -> do not overwrite automatically

Primary writer fenced by RT-1
  -> historical M3 plan/page/index/log/lock state cannot restore permission
```

Storage failure never authorizes post-hoc rewriting of an already delivered visible response.

## Backup, restore, and migration direction

The accepted architecture requires authoritative backup to account for both canonical Subjective memory documents and the non-rebuildable durable operations authority. Rebuildable projections may be regenerated when their source authorities remain intact.

Exact snapshot consistency markers, encryption, platform semantics, backup scheduling, restore validation, rollback procedure, migration tooling, and disaster-recovery workflow remain separate decisions and are not claimed implemented here.

Migration converges on one authority. Permanent dual read, dual write, or conflict resolution by precedence between old and new memory stores is prohibited.

Temporary migration/compatibility surfaces must have explicit owners, bounded consumers, removal gates, and replacement validation, then retire when authority transfer and dependency review permit it.

## Relationship to Retrieval

Storage determines which durable representations are canonical, operational, or derived. Retrieval determines which eligible current memory evidence may enter one request.

```text
storage / publication / recovery
  -> canonical current and finalized state
  -> rebuildable projection may represent eligible derived state

ordinary Retrieval
  -> exact one-authority reader decision
  -> select eligible current evidence only
  -> shared grounding policy
```

Retrieval cannot repair storage corruption or complete a pending mutation. Storage cannot choose a request's ordinary reader authority merely because one store exists.

## Source and evidence disposition

This permanent page absorbs stable architecture from ADR 0005, the Subjective storage contract, ST-1, the shared lifecycle publication engine, and the Primary M3 persistence/reconciliation family.

The detailed source pages remain for their narrower roles while current consumers still depend on them:

- `st1_subjective_mem_commit_runtime.md` — current create-publication implementation;
- `subjective-mem-lifecycle-publication-engine.md` — shared lifecycle publication/replay/recovery implementation architecture;
- `subjective-mem-retrieval-projection-hard-cutover.md` — RT-1 projection/cutover target and transition authority;
- `relaymem_m3d_primary_writer_handoff.md` through `relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md` — Primary compatibility implementation and retirement evidence.

These sources are not competing permanent storage/recovery architecture parents. Their final evidence or retirement disposition must be handled atomically after current consumers, contracts, R5/R6 gates, links, tests, and recovery needs are accounted for.

## Stable invariants

- Canonical memory content/lifecycle, durable operations, rebuildable projection, and governed evidence are distinct authority classes.
- Persistent derived state does not become canonical merely because it survives restart.
- Canonical publication and matching durable finalization evidence must converge before normal published success.
- Projection refresh is not semantic commit authority.
- Recovery is exact pre-image/post-image/foreign-image reasoning, not timestamp guessing.
- Recovery reuses immutable prepared transaction material and does not semantically regenerate content.
- Stale or foreign writers fail closed through revision/digest fencing.
- Concurrency locks are not semantic writer permission.
- Durable usage events are operational facts, not truth or disclosure authority.
- Retrieval never repairs storage or elevates a stale projection to authority.
- Primary compatibility persistence remains subordinate to the RT-1 writer decision while it exists.
- No permanent dual-authority migration is accepted.

## Non-goals

This architecture does not authorize:

- RT-1D-R5/R6 implementation or Primary deletion;
- a final Markdown grammar or database/filesystem schema;
- a particular SQLite, vector, graph, journal, WAL, or locking technology;
- a final backup/restore/disaster-recovery procedure;
- distributed or multi-host writer implementation;
- automatic repair of a foreign canonical image;
- generic persistence of memory prose in operations records;
- lifecycle-policy decisions owned by operation-specific authorities;
- queue/scheduler policy, browser authority, RelaySOUL mutation, or media-runtime behavior.
