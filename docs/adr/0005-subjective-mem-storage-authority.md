---
relaylm_doc_type: adr
relaylm_authority: decision_to_adopt_subjective_mem_storage_authority
relaylm_status: target
relaylm_decision_status: accepted
relaylm_decided_on: 2026-07-21
relaylm_volatility: low
relaylm_owner: architecture
relaylm_update_trigger:
  - Subjective MEM canonical storage authority changes
  - canonical lifecycle-visible state moves away from Markdown
  - rebuildable projection or durable operations authority changes
  - commit-finalization or crash-recovery authority changes
  - backup, restore, migration, or platform policy is accepted
relaylm_not_authoritative_for:
  - exact Markdown page or block syntax
  - exact SQLite schema, table, index, WAL, locking, or migration implementation
  - exact filesystem atomic-replace or durability implementation
  - exact backup, restore, rollback, migration, or platform procedure
  - multi-host writer coordination
  - runtime implementation, rollout, or completion status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_supersedes: []
relaylm_superseded_by: null
---
# ADR 0005: Subjective MEM storage authority and commit finalization

## Status

Accepted as target architecture on 2026-07-21. Runtime implementation, migration, and deployment remain separately governed.

PR #578 is treated as isolated technical evidence. Its experimental package, Markdown syntax, SQLite schema, command surface, benchmark, and Linux-specific implementation are not adopted as production code or wire format.

## Context

[ADR 0003](0003-subjective-mem-direction.md) accepted the high-level direction that durable Subjective MEM prose and canonical lifecycle-visible state use human-readable Markdown, rebuildable SQLite is projection only, and a separate durable operations store may own non-rebuildable operational facts without becoming a second memory-content authority.

[Shared Assessment and Subjective MEM Contract](../contracts/shared-assessment-subjective-mem.md) now defines immutable Subjective MEM revisions, lifecycle transitions, exact current-state selection, and authorization lineage. A storage decision is required so later implementation does not invent conflicting answers for:

- which representation is canonical;
- whether a persistent cache is authority merely because it is on disk;
- where jobs, intents, idempotency, receipts, anti-reformation tombstones, failures, and durable usage events live;
- when a memory mutation becomes committed;
- how a crash between intent, file replacement, receipt, and projection refresh is reconciled;
- whether migration may retain permanent dual authority.

The Markdown/SQLite spike in PR #578 demonstrated single-host Linux feasibility for deterministic parse/render, projection rebuild, stale-snapshot rejection, durable intents and receipts, reversible Forget/Restore, durable usage events, and digest-based recovery. It did not validate final syntax, production integration, Windows/WSL durability, multi-host writers, backup/restore, migration, or operational performance guarantees.

## Decision

### 1. Canonical Subjective MEM authority

Human-readable Markdown workspace files are the target steady-state authority for:

- durable Subjective MEM grounded content and subjective meaning;
- stable logical memory identity and immutable revision lineage;
- user-visible organization;
- canonical lifecycle-visible state, including active, hidden, pinned, superseded, and other contract-owned states;
- references needed to reach governed provenance and authorizing decisions.

Memory pages are human-scale documents rather than one physical file per memory revision. Stable logical memory IDs survive page movement, heading changes, and title changes.

Exact page syntax, block grammar, file partitioning, stable-ID encoding, and edit workflow remain contract-owned and deferred.

### 2. Rebuildable projection authority

A persistent SQLite cache may project canonical Markdown and durable operational aggregates for:

- parsed memory revisions and current selectors;
- full-text search;
- metadata and semantic facets;
- relation indexes;
- lifecycle and retrieval eligibility;
- page/block digests;
- vector or graph references;
- explainable retrieval features.

Persistence does not make the cache authoritative. Deleting, corrupting, or replacing the cache must not destroy committed Subjective MEM prose, canonical lifecycle-visible state, or durable operational history. The cache must be rebuildable from canonical Markdown plus the permitted durable operations inputs.

A stale, corrupt, unsupported, or incompletely rebuilt projection fails closed from ordinary retrieval or mutation planning. It must not silently become a fallback authority.

### 3. Durable operations authority

A separate durable operations store owns non-rebuildable operational facts such as:

- jobs, claims, leases, retries, and scheduling state;
- prepared mutation intents and exact preconditions;
- idempotency reservations and results;
- commit receipts and recovery state;
- failures and operator-reconciliation state;
- anti-reformation tombstones and their operation lineage;
- content-free durable usage events when behavior depends on usage history.

The operations store must not own:

- a second copy of Subjective MEM prose;
- an independently editable canonical lifecycle state;
- a second current-revision selector;
- CTX-OVL content;
- governed SourceEvent prose;
- relationship, scene, SOUL, or product-knowledge content authority.

Operational records reference stable IDs, revisions, digests, authority snapshots, and reason classes. They do not duplicate memory bodies or user query text merely for convenience.

### 4. Lifecycle and tombstone separation

Forget remains a canonical hidden successor, not physical deletion. Restore remains a canonical active successor. Purge is a separate irreversible authority.

An anti-reformation tombstone may enforce that canonically hidden material is not automatically re-created. Purge enforcement remains owned by a separate irreversible authority. The tombstone is operational authority, not the canonical lifecycle representation. A lifecycle mutation is valid only when the canonical Markdown successor and its operation receipt agree.

Restore clears or supersedes the applicable anti-reformation tombstone through the same finalized operation that publishes the active successor. A tombstone cannot silently hide an otherwise active canonical revision, and its absence cannot silently reactivate a hidden canonical revision.

### 5. Commit finalization

A Subjective MEM mutation becomes committed only when both are durable and mutually consistent:

1. the canonical Markdown post-image with its expected digest and revision lineage; and
2. the matching durable operations receipt that finalizes the intent, idempotency result, lifecycle enforcement changes, and operation outcome.

The receipt is the commit-finalization marker. It does not replace Markdown as content or lifecycle authority.

A Markdown post-image without its matching receipt is recovery-pending physical state. It must not be treated as a normally published mutation or used as the basis for another writer until recovery reconciles it.

A receipt whose expected Markdown post-image cannot be verified is corruption or incomplete recovery and fails closed.

Projection refresh is not semantic commit authority. It may occur before or after receipt finalization only when the implementation prevents an unfinalized or stale projection from being served as current. A rebuildable cache failure cannot redefine the committed content.

### 6. Recovery direction

Every prepared mutation records enough durable information to distinguish at least:

- the expected canonical pre-image digest;
- the expected canonical post-image digest;
- the target page and logical memory/revision identity;
- the authorizing decision or lifecycle transition;
- the idempotency identity;
- required authority and schema revisions.

Recovery compares the current canonical digest with the intent:

- **pre-image digest**: replacement did not become durable; retry or abort under the original preconditions;
- **post-image digest**: canonical replacement became durable; roll forward the missing receipt, tombstone, idempotency, and projection work without re-rendering a different post-image;
- **any other digest**: foreign modification, corruption, or stale writer; fail closed and require deterministic reconciliation.

Recovery runs before normal mutation service can rely on affected pages. It never guesses from timestamps, cache contents, or file names.

### 7. Concurrency direction

Every mutation is revision- and digest-fenced. A writer must verify the exact expected canonical pre-image immediately before replacement. A stale writer cannot overwrite a newer page.

The target is single canonical writer authority per affected page/operation domain unless a later contract defines a stronger distributed protocol. Lock fairness, backoff, batching, page partitioning, and multi-host coordination remain deferred.

### 8. Durable usage events

When retrieval ranking, management UI, or lifecycle policy depends on usage history, the underlying usage events are durable operational facts rather than cache-only counters.

Usage records are content-free by default and contain only bounded identifiers, event classes, times, and non-reversible query-plan or selection digests as required. Cache aggregates such as count and last-used time are derived and rebuildable.

Usage never becomes evidence confidence, truth authority, merge authority, or permission to disclose.

### 9. Backup, restore, and migration direction

A complete authoritative backup must include canonical Markdown and the durable operations store. Rebuildable caches and indexes may be omitted and regenerated.

Exact consistency markers, snapshot order, encryption, restore validation, platform behavior, rollback, and disaster-recovery procedure require separate accepted contracts and tests.

A production migration converges on one authority. Permanent dual-read, dual-write, or conflict-resolution-by-precedence between old and new memory stores is prohibited. Temporary migration bridges must be bounded, observable, reversible before cutover, and removed at authority transfer.

## Consequences

### Positive

- Human-editable memory and user-visible lifecycle remain inspectable and portable.
- Persistent SQLite can provide fast retrieval without becoming an accidental second source of truth.
- Operational facts that cannot be reconstructed are retained without duplicating memory semantics.
- Crash recovery has deterministic pre-image, post-image, and foreign-image outcomes.
- Forget/Restore enforcement and canonical lifecycle cannot drift silently.
- Future migration begins from a no-permanent-dual-authority rule.

### Costs

- Canonical files and operations receipts must be reconciled before affected state is served.
- Backup must preserve two different authority classes even though the cache is disposable.
- Page-level digest fencing may serialize hot writers until a later partitioning contract is accepted.
- Platform-specific durability and distributed-writer behavior remain unresolved.

## Rejected alternatives

### Make persistent SQLite the canonical memory store

Rejected because user-visible Markdown would become an export or lossy mirror, cache deletion would threaten committed memory, and file-first editing would require permanent dual authority.

### Treat Markdown alone as sufficient operational state

Rejected because jobs, leases, idempotency, crash intents, receipts, anti-reformation enforcement, failures, and durable usage events are not safely reconstructable from memory prose.

### Store canonical lifecycle independently in operations.db

Rejected because active/hidden/restored/successor state would have two competing authorities. Operations may enforce and finalize lifecycle mutations but cannot own a second lifecycle representation.

### Define commit at file replacement alone

Rejected because a crash may leave idempotency, tombstone, receipt, and recovery state incomplete.

### Define commit at cache refresh

Rejected because the cache is rebuildable projection and cannot become semantic commit authority.

### Preserve permanent compatibility with the old store

Rejected because permanent dual read/write retains ambiguous authority and makes correction, Forget, recovery, and rebuild depend on two live systems.

## Fixed boundaries

- Markdown owns committed Subjective MEM content and canonical lifecycle-visible state.
- A matching durable operations receipt finalizes publication but does not own memory semantics.
- Rebuildable cache state is never canonical merely because it persists.
- Operations state owns non-rebuildable operational facts, not a second memory body or lifecycle representation.
- Forget/Restore canonical successors and anti-reformation tombstones must agree through one finalized operation.
- Recovery is digest- and revision-driven and fails closed on a foreign image.
- Durable usage events are content-free operational facts and never truth or merge authority.
- Exact syntax, schemas, platform durability, backup, migration, and implementation remain separately governed.
- PR #578 remains experiment evidence and is not merged as production code.

## Related documents

- [ADR 0003: Subjective MEM direction](0003-subjective-mem-direction.md)
- [Shared Assessment and Subjective MEM Contract](../contracts/shared-assessment-subjective-mem.md)
- [Memory Lifecycle Design](../architecture/memory_lifecycle_design.md)
- [Primary MEM Forget / Hide Contract](../architecture/phase_i4_primary_mem_forget_hide_contract.md)
- [Primary Forget Hidden-Successor Commit](../architecture/phase_i4c1_primary_forget_hidden_successor.md)
- [Project Status](../PROJECT_STATUS.md)
