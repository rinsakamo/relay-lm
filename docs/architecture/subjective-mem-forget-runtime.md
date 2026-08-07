---
relaylm_doc_type: subsystem_architecture
relaylm_authority: subjective_mem_forget_runtime_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - Subjective MEM Forget input, transition, persistence, tombstone, or recovery changes
  - Restore changes Forget tombstone supersession or release semantics
  - ordinary Retrieval changes lifecycle-eligibility consumption
relaylm_not_authoritative_for:
  - ordinary Subjective MEM Retrieval, ranking, cache, or request-path selection
  - API, UI, model-generated Forget decisions, or background recovery
  - Primary MEM migration, retirement, or precedence
  - Restore, Pin/Unpin, Consolidate, or Purge behavior
relaylm_related_authority:
  - ../contracts/shared-assessment-subjective-mem.md
  - ../contracts/subjective-mem-storage-authority-and-commit-protocol.md
  - lc1a_subjective_mem_correct.md
  - subjective-mem-lifecycle-publication-engine.md
  - subjective-mem-restore-runtime.md
  - project_execution_plan.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Subjective MEM runtime implementers
  - lifecycle reviewers
  - retrieval and anti-reformation reviewers
relaylm_authority_level: subsystem
---
# Subjective MEM Forget Runtime

Last reviewed: 2026-08-07 JST

## Scope

Forget owns one caller-invoked, default-off, exact `active -> hidden`
Subjective MEM lifecycle transition on the canonical Markdown and operations
boundaries shared by the lifecycle system.

```text
active revision N / mutation none / retrieval eligible
  -> exact prepared intent / retrieval fail-closed
  -> hidden revision N+1 / mutation none / retrieval ineligible
  -> content-free anti-reformation tombstone effective
```

Forget preserves the full semantic payload, character, scope, memory kind,
formation stage, formation snapshot, and multidimensional strength. It changes
only immutable revision metadata, lifecycle visibility, and lifecycle authority.
The predecessor remains byte-reconstructable and auditable.

Current implementation completion and feature posture remain owned by
`docs/PROJECT_STATUS.md`. Exact schemas and transition requirements remain owned
by the Subjective MEM contracts.

## Shared mutation fence

Forget uses the shared Subjective MEM lifecycle boundaries:

- one Evidence-space transaction lock;
- one logical `SubjectiveMemCurrentState` selector per character and memory;
- exact current revision, selector, receipt, page, block, and digest binding;
- exact predecessor formation-decision or lifecycle-transition authority;
- one Character Workspace canonical Markdown page;
- one secure POSIX page-domain lock and atomic replacement path;
- one immutable post-image artifact;
- deterministic idempotency and caller-invoked forward recovery.

Forget remains a separate operation implementation because anti-reformation
finalization is additional operation-specific authority. It is not a second
semantic or current-state authority and is not implicitly absorbed by the
operation-neutral lifecycle publication engine.

## Canonical successor

The hidden successor retains exactly:

- grounded assessment reference and grounded content;
- subjective meaning;
- memory kind and formation stage;
- scope binding;
- formation snapshot;
- strength dimensions.

It advances the logical revision by one, references the immediate predecessor,
sets `lifecycle_state: hidden`, sets `retrieval_visible: false`, and binds its
authorization to the exact Forget lifecycle transition.

## One anti-reformation authority

`relaylm/subjective_mem_reformation.py` owns:

- exact semantic-identity derivation;
- public and already-locked candidate entry points;
- the single under-lock decision loop;
- exact tombstone-state validation;
- immutable tombstone self-digest validation;
- committed receipt self-digest validation;
- exact lifecycle-transition validation;
- duplicate detection and fail-closed classification.

The public entry point differs from the locked entry point only by acquiring the
Evidence-space transaction. Subjective MEM formation calls the locked entry
point inside its existing transaction after exact replay and current-Assessment
validation, but before a new create identity is reserved.

The exact anti-reformation identity is derived from:

```text
evidence space
character
exact grounded-content digest
exact subjective-meaning digest
memory kind
exact scope-binding digest
```

No embedding, lexical, model-confidence, or similarity comparison grants
authority. Exact identity is blocked; a merely similar candidate is not blocked.

## Exact tombstone lineage

Receipt finalization creates one immutable content-free tombstone containing
only bounded IDs, digests, lifecycle lineage, authorization, reason category,
formation stage, policy revision, and receipt lineage. It never stores grounded
content, subjective meaning, prompts, raw user reasons, paths, or unrestricted
diagnostics.

A tombstone-state entry can block re-formation only when the canonical evaluator
resolves it under the same lock to all of the following:

- one exact state object with no missing or unknown fields;
- one self-authenticating immutable tombstone;
- one exact self-authenticating committed lifecycle receipt;
- one exact `active -> hidden` transition with no missing or unknown fields;
- matching evidence space, character, memory, source and hidden revisions;
- matching formation stage, semantic identity, authorization, reason, and policy;
- matching tombstone and transition digests;
- one exact commit/effective/update time across transition, tombstone, receipt,
  and state.

Duplicate IDs, malformed state, dangling records, unknown fields, digest
mismatch, and cross-linked lineage fail closed identically through public and
locked entry points.

## Commit and recovery

Before page replacement, Forget records a content-free claim and prepared intent
and replaces the singleton selector with `mutation_state: prepared` and
`retrieval_eligible: false`.

The same canonical lineage inspector runs:

1. before the prepared claim and selector reservation;
2. immediately before canonical page replacement while the original intent and
   selector are revalidated;
3. inside receipt/tombstone finalization before the tombstone-state log changes;
4. during exact replay of a finalized result.

A valid pre-existing blocked identity may receive another exact Forget
tombstone. A malformed or dangling pre-existing identity can never be carried
forward by a successful Forget.

After exact hidden post-image verification, one operations transaction inserts:

- lifecycle transition;
- Forget tombstone;
- lifecycle receipt;
- idempotency result;
- intent finalization;
- final hidden singleton selector;
- rebuild-required projection state;
- exact tombstone-state projection used by anti-reformation checks.

Recovery is caller-invoked only:

1. exact pre-image: publish the original immutable post-image after revalidation;
2. exact post-image: roll the original receipt, selector, and tombstone forward;
3. neither image: fail closed and mark recovery required;
4. receipt or tombstone without an exact page: never return success.

A durable hidden successor is never replaced with the active predecessor because
receipt delivery or finalization failed.

## Retrieval and Primary MEM boundary

The final selector and canonical revision are retrieval-ineligible, and the
projection is marked `rebuild_required`. Forget does not own ordinary Retrieval.
The Retrieval cutover remains the owner of projection consumption, candidate
selection, request-path authority, usage events, and old-reader retirement.

Primary MEM Forget remains characterization or historical boundary evidence
only. This Subjective MEM Forget architecture does not grant Primary MEM code,
API routes, UI surfaces, fixtures, or storage any current Forget authority.

## Non-goals

Forget does not own or authorize:

- Restore, Pin/Unpin, Consolidate, or Purge;
- API or SOUL Lab UI;
- ordinary Retrieval or prior-reader retirement;
- heuristic resurrection or tombstone matching;
- background scanner, worker, scheduler, polling, or automatic repair;
- multi-host or non-POSIX canonical publication;
- user-data migration or irreversible erasure.

## Validation

Focused evidence covers dry-run no-write behavior, exact hidden-successor
publication, semantic payload preservation, content-free tombstone shape,
selector and receipt binding, deterministic replay, changed-input conflict,
stale and non-active rejection, pre-page and post-page crash recovery, exact
public/locked equivalence, duplicate-state rejection, dangling lineage
fail-closed, malformed pre-existing state rejection before publication, exact
public re-formation rejection, and similar-but-not-exact allowance.

The maintained runtime validation surface also exercises the surrounding
Subjective MEM formation, commit, Correct, and Forget boundaries together with
the canonical Forget publication/tombstone process smoke. Test and smoke names
may retain historical slice identifiers; those names are validation anchors, not
semantic or architectural authority.
