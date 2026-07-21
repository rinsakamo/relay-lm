---
relaylm_doc_type: contract
relaylm_authority: subjective_mem_storage_authority_commit_finalization_and_recovery_contract
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - ADR 0005 storage authority changes
  - Subjective MEM revision or lifecycle contract changes
  - canonical Markdown or operations authority changes
  - commit, recovery, idempotency, tombstone, usage, or projection rules change
  - backup, restore, migration, or platform contracts are accepted
relaylm_not_authoritative_for:
  - exact Markdown page, heading, block, or front-matter syntax
  - exact SQLite database, table, column, index, WAL, or migration schema
  - exact filesystem APIs, lock implementation, fsync sequence, or platform guarantee
  - exact backup, restore, rollout, rollback, or legacy migration procedure
  - multi-host or distributed-writer coordination
  - runtime implementation or completion status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source:
  - ../adr/0003-subjective-mem-direction.md
  - ../adr/0005-subjective-mem-storage-authority.md
relaylm_related_authority:
  - shared-assessment-subjective-mem.md
  - ../architecture/memory_lifecycle_design.md
  - ../architecture/phase_i4_primary_mem_forget_hide_contract.md
  - ../architecture/phase_i4c1_primary_forget_hidden_successor.md
  - ../architecture/phase_i4e_primary_restore_apply.md
---
# Subjective MEM Storage Authority and Commit Protocol Contract

## Status and purpose

This is the normative **target logical contract** for durable Subjective MEM storage authority, mutation finalization, projection behavior, recovery, and operational state.

It does not select final Markdown syntax, SQLite schemas, filesystem calls, migration code, or supported platforms. It does not claim that the current runtime implements this contract.

PR #578 is supporting experiment evidence only. Its code, schemas, commands, and benchmark are not production authority.

## Authority classes

The storage model has four non-interchangeable authority classes.

### Canonical memory documents

Human-readable Markdown owns committed:

- logical memory identity and revision lineage;
- grounded content and subjective meaning;
- memory kind and formation stage;
- canonical lifecycle-visible state;
- current/successor relationships represented by the Subjective MEM contract;
- user-visible organization and governed editability;
- references to authorizing decisions, lifecycle transitions, and provenance.

Canonical content is organized in human-scale pages. A file path, heading, or title is not the logical memory identity. Stable memory IDs survive movement and reorganization.

### Rebuildable projection

A cache or search database may own only derived projection state, including:

- parsed page/block records;
- exact source-page and source-block digests;
- current-revision lookup;
- lifecycle and ordinary-Retrieval eligibility projection;
- full-text indexes;
- semantic facets and metadata indexes;
- relation, vector, and graph references;
- derived usage aggregates;
- explainable ranking features.

A projection is rebuildable and disposable. Persistence, WAL, replication, or backup convenience does not elevate it to canonical authority.

### Durable operations ledger

A durable operations database owns non-rebuildable operational facts:

- jobs, attempts, claims, leases, retries, and scheduling state;
- prepared mutation intents;
- exact revision and digest preconditions;
- idempotency reservations and finalized results;
- commit receipts;
- recovery and reconciliation status;
- failures and operator-action requirements;
- anti-reformation tombstones;
- content-free durable usage events.

It never owns a second editable memory body, second current-revision selector, or second canonical lifecycle representation.

### Governed evidence authority

Protected Source Evidence and Shared Assessment remain governed by their owning contracts. Storage of Subjective MEM does not duplicate or absorb governed source authority. Canonical documents retain opaque resolvable references rather than copying all source payloads into ordinary memory pages.

## Canonical publication rule

A mutation is **finalized and published** only when:

1. the canonical Markdown post-image exists durably at the exact expected digest and contains the expected memory/revision lineage; and
2. a matching durable operations receipt finalizes the exact prepared intent.

The receipt is the commit-finalization marker. Markdown remains the semantic and lifecycle authority.

The pair must agree on at least:

- operation ID;
- idempotency key;
- logical memory ID;
- from-revision or create precondition;
- to-revision;
- authorizing decision or lifecycle-transition reference;
- target page identity;
- canonical pre-image digest;
- canonical post-image digest;
- relevant schema and authority revisions;
- operation outcome;
- receipt time.

A canonical post-image without its receipt is `recovery_pending`, not normally published. A receipt without its verifiable canonical post-image is `recovery_required` or `corrupt`, never success.

## Mutation intent

Before canonical replacement, the system durably records a prepared intent containing enough immutable information to recover without semantic regeneration.

A prepared intent includes conceptually:

```yaml
operation_id: op-...
idempotency_key: ...
operation_kind: create | correct | forget | restore | consolidate | pin | unpin
memory_id: mem-...
from_revision_or_null: 3
to_revision: 4
authority_ref: ...
target_page_id: ...
pre_image_digest: sha256:...
post_image_digest: sha256:...
post_image_artifact_ref: ...
schema_revisions: {}
authority_snapshots: {}
prepared_at: ...
```

The durable intent references a bounded immutable post-image artifact or an equivalently deterministic representation. Recovery must not call an LLM or re-run subjective formation to invent a replacement post-image.

## Preconditions

Immediately before replacement, a writer verifies:

- the expected canonical page and memory revision still exist;
- the current page digest equals `pre_image_digest`;
- the exact from-revision is still current where the operation requires currentness;
- authorizing decision/lifecycle records remain resolvable and applicable;
- no conflicting finalized idempotency result exists;
- required lifecycle tombstone conditions are satisfied;
- schema and authority revisions are supported;
- the operation owns or holds the required writer lease/mutex.

Failure of any precondition prevents replacement. A stale writer never overwrites a newer canonical page.

## Canonical replacement boundary

Canonical replacement must provide an implementation-specific atomicity and durability guarantee appropriate to the supported platform.

The logical requirements are:

- readers never accept a torn or partially rendered canonical page;
- replacement occurs only after exact pre-image verification;
- the installed post-image is byte-identical to the prepared artifact;
- the installed digest is verified after replacement;
- the operation cannot silently fall back to a different page or memory ID;
- temporary files or staging artifacts never become independent authority;
- unsupported durability semantics fail closed.

This contract does not prescribe a particular rename, fsync, journal, or filesystem API. A platform-specific contract must demonstrate how these logical requirements are met.

## Receipt finalization

After the post-image digest is verified, one durable operations transaction finalizes all non-rebuildable effects belonging to the operation:

- insert the commit receipt;
- finalize the idempotency result;
- apply, clear, or supersede an anti-reformation tombstone when applicable;
- update job/attempt state;
- clear or finalize the prepared intent;
- record any required content-free operation event;
- record projection freshness or rebuild requirement without making it semantic authority.

The receipt transaction must not store the memory body. It may store stable IDs, revision numbers, digests, bounded reason classes, and resolvable artifact references.

## Projection consistency

Projection refresh is not the semantic commit event.

An implementation may refresh the projection before or after receipt finalization only if it enforces these invariants:

- an unfinalized post-image is never served as a committed retrieval result;
- a finalized receipt with stale projection causes rebuild/refresh or fail-closed retrieval, not fallback to stale data;
- cache rows identify the exact canonical page/block digest they project;
- mixed projection generations cannot be presented as one current authority;
- unsupported cache schema fails closed and is rebuilt or migrated under a separate contract;
- deleting the projection cannot remove canonical memory, lifecycle state, tombstones, receipts, or usage history.

Where immediate refresh is unavailable, the operations ledger records a projection-pending or rebuild-required state. Ordinary retrieval excludes affected stale projection entries until reconciliation completes.

## Idempotency

An idempotency key is scoped to the owning character/workspace and operation authority.

- The same key with the same immutable intent returns or reconstructs the same finalized result.
- The same key with different memory, revision, digest, authority, or operation parameters is a conflict.
- A recovered post-image is rolled forward under the original key; it is not published again as a new mutation.
- Retry does not increment revision twice, duplicate relations, duplicate tombstones, or duplicate durable usage events.
- Expiry of an execution lease does not expire the idempotency result.

## Recovery state machine

Recovery runs before normal mutation or ordinary retrieval may rely on an affected page.

For each unresolved intent, compare the current canonical page digest:

### Current digest equals the pre-image

The canonical replacement did not become durable.

Permitted outcomes:

- retry the exact prepared post-image after revalidating authority and acquiring the writer boundary;
- cancel/abort if policy permits and no canonical mutation occurred;
- mark failed when the original authority or schema is no longer applicable.

Recovery must not advance a receipt for a post-image that is absent.

### Current digest equals the post-image

The canonical replacement became durable but finalization is incomplete.

Recovery rolls forward deterministically:

- verify the expected memory/revision lineage in the post-image;
- finalize or reconstruct the matching receipt;
- finalize the original idempotency result;
- apply or clear the required tombstone;
- mark projection stale or refresh/rebuild it;
- finalize the original job/attempt.

Recovery uses the prepared artifact and original authority references. It does not re-render different semantic content.

### Current digest equals neither image

This indicates a foreign writer, manual edit, corruption, wrong page, unsupported normalization, or stale intent.

Required behavior:

- fail closed;
- do not overwrite the foreign image automatically;
- preserve the unresolved intent and diagnostic lineage;
- invalidate or rebuild affected projections;
- require deterministic reconciliation or governed operator action.

Timestamps, file modification time, cache rows, or newest-write-wins policy cannot override the digest mismatch.

### Receipt exists but post-image is unverifiable

This is not a successful commit. Mark affected state recovery-required or corrupt, block ordinary mutation/retrieval for the inconsistent revision, and enter governed reconciliation.

## Lifecycle operations

### Forget

Forget publishes a new canonical hidden successor under the Subjective MEM lifecycle contract.

The finalized operation also creates or supersedes an anti-reformation tombstone that references the logical memory and lifecycle transition. Normal retrieval excludes the hidden canonical revision through canonical lifecycle projection; the tombstone additionally prevents automatic re-formation.

Forget does not remove the canonical memory body and is not Purge.

### Restore

Restore publishes a new canonical active successor. The same receipt-finalization transaction clears or supersedes the applicable anti-reformation tombstone.

A tombstone must not remain effective against a finalized restored successor. Conversely, deleting a tombstone alone does not restore a canonically hidden memory.

### Correct

Correct publishes an authorized canonical successor while preserving immutable prior revisions and lineage. Operational state cannot rewrite an earlier canonical revision in place.

### Consolidate

Consolidate publishes only the lifecycle/formation-stage transition permitted by the Subjective MEM contract. Storage mechanics cannot use consolidation to change memory kind, scope, grounded content, subjective meaning, or strength outside the authorizing transition.

### Pin and Unpin

Pin/Unpin publish canonical lifecycle successors. Cache-only flags are insufficient.

### Purge

Purge is not an ordinary reversible lifecycle transition. Its evidence, Subjective MEM, operations, backup, and irreversible-erasure semantics require a separate accepted authority.

## Anti-reformation tombstones

A tombstone is a non-rebuildable operational enforcement record.

It contains only bounded references and enforcement metadata such as:

- tombstone ID;
- character/workspace scope;
- logical memory ID;
- lifecycle-transition reference;
- protected semantic identity or digest needed to prevent automatic re-formation;
- reason class;
- effective and supersession state;
- receipt lineage.

It must not contain or become a second editable memory body.

Tombstone rules:

- a finalized Forget creates/supersedes the applicable tombstone;
- a finalized Restore clears/supersedes it;
- a failed or recovery-pending operation cannot expose half-applied enforcement as final;
- a tombstone cannot independently change canonical active/hidden state;
- cache rebuild preserves enforcement because tombstones are not cache-only;
- Purge tombstones, if any, require the separate purge authority.

## Durable usage events

Usage-dependent behavior is based on durable content-free events, not cache-only counters.

A usage event may contain:

- stable memory/revision identifier;
- event kind;
- occurrence time;
- request/selection correlation ID;
- non-reversible query-plan or candidate-set digest;
- bounded retrieval-policy revision.

It must not contain raw query text, prompt content, memory prose, private context, or an unrestricted diagnostics payload by default.

Counts, last-used time, and bounded ranking features are derived projection. Usage:

- never increases evidence confidence;
- never proves truth;
- never grants merge/reinforcement authority;
- never changes disclosure permission;
- never overrides lifecycle or scope;
- has only contract-bounded ranking influence.

## Manual editing boundary

Human-readable authority permits governed manual editing, but an arbitrary filesystem edit is not automatically a valid committed Subjective MEM mutation.

A supported manual-edit workflow must:

- parse and validate the complete affected canonical page;
- preserve stable IDs and immutable lineage;
- identify additions, corrections, moves, and deletions deterministically;
- reject unauthorized lifecycle or provenance rewrites;
- create an authorizing operation/management record;
- finalize a receipt and projection reconciliation;
- fail closed on ambiguous identity or revision changes.

Pure page movement or formatting change may preserve semantic revisions only when canonical normalization proves semantic equivalence. Exact normalization remains deferred.

## Backup and restore boundary

An authoritative backup set includes:

- canonical Markdown documents;
- durable operations database;
- schema/version manifests and required authority metadata;
- integrity digests and consistency markers defined by the future backup contract.

Rebuildable caches, FTS, vectors, and graph indexes may be omitted.

Restore is not complete until:

- canonical documents validate;
- operations receipts/intents/tombstones validate against the restored documents;
- unresolved intents are recovered;
- projections are rebuilt;
- ordinary retrieval and writers remain blocked until consistency succeeds.

Exact snapshot ordering, encryption, retention, remote media, and rollback procedure remain deferred.

## Migration and hard cutover

Migration must converge to this authority model through a bounded hard cutover.

Required direction:

1. inventory old canonical and operational state;
2. freeze or fence old writers;
3. transform into candidate canonical documents and operations records;
4. validate identity, revision, lifecycle, provenance, tombstones, and receipts;
5. rehearse recovery and rollback before authority transfer;
6. switch one canonical authority;
7. rebuild projections;
8. verify characterization and platform tests;
9. retire old readers/writers and remove temporary bridges.

Permanent dual-read, dual-write, precedence fallback, or conflict resolution between two live canonical stores is prohibited.

## Platform and concurrency gates

PR #578 supports feasibility only for a bounded single-host Linux experiment.

Production adoption requires separately governed evidence for:

- Windows and WSL atomic replacement, durability, locking, WAL, and recovery behavior;
- supported filesystem placement, including whether host-mounted paths are permitted;
- writer fairness, bounded retry, lease expiry, and backpressure;
- hot-page contention and page partitioning;
- bulk import batching and durability cost;
- backup/restore under crash and corruption;
- multi-process and, if supported, multi-host writer coordination;
- unsupported newer schema refusal and migration rehearsal.

No platform is implied supported by this target contract alone.

## Validation and observability

A future implementation must provide deterministic tests covering at least:

- create, Correct, Forget, Restore, Consolidate, Pin, and Unpin;
- duplicate idempotency retry;
- stale pre-image rejection;
- crash before replacement;
- crash after replacement before receipt;
- crash after receipt before projection refresh;
- cache deletion and full rebuild equivalence;
- cache corruption and unsupported schema refusal;
- foreign-image recovery failure;
- tombstone/canonical lifecycle agreement;
- usage-event persistence across cache rebuild;
- backup/restore with unresolved intent;
- platform-specific atomicity and durability drills.

Observability is content-free by default and reports bounded state classes, counts, digests, durations, retry classes, and recovery outcomes without exposing memory prose or user queries.

## Non-authorization

Acceptance of this contract does not authorize:

- merging or importing the PR #578 experiment package;
- production Markdown syntax;
- production SQLite schemas;
- runtime integration;
- migration of current user data;
- deletion of the old store;
- enabling persistent writes;
- claiming Windows, WSL, multi-process, or multi-host support;
- treating the rebuildable projection as canonical.
